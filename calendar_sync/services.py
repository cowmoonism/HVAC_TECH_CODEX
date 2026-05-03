import logging
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path

from django.conf import settings
from django.utils.dateparse import parse_date, parse_datetime
from django.utils import timezone
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from audit.services import log_audit_event
from calendar_sync.models import CalendarEvent, CalendarEventStatus, CalendarEventType
from notifications.services import NotificationService, get_technician_group_chat
from technicians.models import Technician


logger = logging.getLogger(__name__)


def build_technician_schedule_message(technician_id, target_date):
    technician = Technician.objects.get(id=technician_id)
    target_date = _coerce_to_date(target_date)
    events = list(_get_active_job_events_for_schedule(technician, target_date))
    date_label = target_date.strftime("%A, %B %d")
    lines = [
        f"Hi {technician}, here is your schedule for {date_label}:",
    ]

    if not events:
        lines.extend(["", "No jobs scheduled."])
        return "\n".join(lines)

    for event in events:
        start_at = timezone.localtime(event.start_at)
        end_at = timezone.localtime(event.end_at)
        lines.extend(
            [
                "",
                f"{_format_schedule_time(start_at)}-{_format_schedule_time(end_at)}",
                event.location or "No location provided",
                event.clean_title_for_technician(),
            ]
        )
    return "\n".join(lines)


def send_technician_schedule(technician_id, target_date):
    summary = {
        "technician_id": technician_id,
        "target_date": str(_coerce_to_date(target_date)),
        "sent": False,
        "events_count": 0,
        "error": "",
    }
    try:
        technician = Technician.objects.get(id=technician_id)
    except Technician.DoesNotExist:
        summary["error"] = f"Technician {technician_id} does not exist."
        logger.error(summary["error"])
        return summary

    target_date = _coerce_to_date(target_date)
    events = list(_get_active_job_events_for_schedule(technician, target_date))
    summary["events_count"] = len(events)
    try:
        chat_id = get_technician_group_chat(technician)
    except Exception as exc:
        summary["error"] = str(exc)
        logger.error("Technician schedule delivery failed for technician %s: %s", technician.id, exc)
        return summary

    message = build_technician_schedule_message(technician.id, target_date)
    sent = NotificationService().send_text_to_telegram(chat_id=chat_id, text=message)
    summary["sent"] = sent
    if not sent:
        summary["error"] = "Telegram message was not sent. Check Telegram bot token and chat configuration."
        logger.error("Technician schedule for technician %s on %s was not sent.", technician.id, target_date)
    else:
        logger.info("Technician schedule for technician %s on %s sent to chat %s.", technician.id, target_date, chat_id)
    return summary


def get_google_calendar_service():
    credentials_path = Path(settings.GOOGLE_SERVICE_ACCOUNT_JSON_PATH)
    if not credentials_path.exists():
        logger.warning(
            "Google Calendar credentials file is missing at %s; calendar operation skipped.",
            credentials_path,
        )
        return None

    try:
        credentials = service_account.Credentials.from_service_account_file(
            str(credentials_path),
            scopes=settings.GOOGLE_CALENDAR_SCOPES,
        )
        return build("calendar", "v3", credentials=credentials, cache_discovery=False)
    except Exception as exc:
        logger.error("Failed to create Google Calendar service: %s", exc, exc_info=True)
        return None


def sync_google_calendar_for_technician(technician_id, start_date=None, end_date=None):
    summary = {
        "technician_id": technician_id,
        "created": 0,
        "updated": 0,
        "skipped": 0,
    }

    try:
        technician = Technician.objects.get(id=technician_id)
    except Technician.DoesNotExist:
        summary["error"] = f"Technician {technician_id} does not exist."
        logger.error(summary["error"])
        _audit_calendar_sync(technician_id=technician_id, summary=summary)
        return summary

    if not technician.google_calendar_id:
        summary["error"] = f"Technician {technician.id} does not have a Google Calendar id configured."
        logger.error(summary["error"])
        _audit_calendar_sync(technician_id=technician.id, summary=summary)
        return summary

    service = get_google_calendar_service()
    if service is None:
        summary["error"] = "Google Calendar credentials are not available."
        _audit_calendar_sync(technician_id=technician.id, summary=summary)
        return summary

    start_dt, end_dt = _build_sync_window(start_date, end_date)

    try:
        response = service.events().list(
            calendarId=technician.google_calendar_id,
            singleEvents=True,
            orderBy="startTime",
            timeMin=start_dt.isoformat(),
            timeMax=end_dt.isoformat(),
        ).execute()
    except HttpError as exc:
        summary["error"] = f"Google Calendar API failed while listing events: {exc}"
        logger.error(summary["error"], exc_info=True)
        _audit_calendar_sync(technician_id=technician.id, summary=summary)
        return summary
    except Exception as exc:
        summary["error"] = f"Unexpected failure while listing Google Calendar events: {exc}"
        logger.error(summary["error"], exc_info=True)
        _audit_calendar_sync(technician_id=technician.id, summary=summary)
        return summary

    for google_event in response.get("items", []):
        event_id = google_event.get("id")
        start_at, start_timezone = _parse_google_event_datetime(google_event.get("start", {}), default_tz=technician.timezone)
        end_at, end_timezone = _parse_google_event_datetime(google_event.get("end", {}), default_tz=start_timezone)
        if not event_id or not start_at or not end_at:
            summary["skipped"] += 1
            logger.warning("Skipped Google Calendar event with missing id/start/end: %s", google_event)
            continue

        title = google_event.get("summary") or ""
        location = google_event.get("location") or ""
        defaults = {
            "technician": technician,
            "title": title,
            "location": location,
            "description": google_event.get("description") or "",
            "start_at": start_at,
            "end_at": end_at,
            "timezone": start_timezone or end_timezone or technician.timezone,
            "event_type": _infer_event_type(title, location),
            "status": _infer_event_status(title),
            "job_number": _extract_job_number(title),
            "raw_google_payload": google_event,
            "last_synced_at": timezone.now(),
        }
        _, created = CalendarEvent.objects.update_or_create(
            google_calendar_id=technician.google_calendar_id,
            google_event_id=event_id,
            defaults=defaults,
        )
        if created:
            summary["created"] += 1
        else:
            summary["updated"] += 1

    logger.info(
        "Synced Google Calendar %s for technician %s: %s",
        technician.google_calendar_id,
        technician.id,
        summary,
    )
    _audit_calendar_sync(technician_id=technician.id, summary=summary)
    return summary


WORK_REPORT_BLOCK_START = "--- Work Report Submitted ---"


def update_google_event_description(calendar_event_id, appended_text):
    service = get_google_calendar_service()
    if service is None:
        _audit_calendar_update(calendar_event_id=calendar_event_id, success=False, appended_text=appended_text)
        return False

    try:
        calendar_event = CalendarEvent.objects.get(id=calendar_event_id)
    except CalendarEvent.DoesNotExist:
        logger.error("CalendarEvent %s does not exist; Google Calendar update skipped.", calendar_event_id)
        _audit_calendar_update(calendar_event_id=calendar_event_id, success=False, appended_text=appended_text)
        return False

    if not calendar_event.google_calendar_id or not calendar_event.google_event_id:
        logger.error(
            "CalendarEvent %s is missing google_calendar_id or google_event_id; Google Calendar update skipped.",
            calendar_event.id,
        )
        _audit_calendar_update(calendar_event_id=calendar_event.id, success=False, appended_text=appended_text)
        return False

    try:
        google_event = service.events().get(
            calendarId=calendar_event.google_calendar_id,
            eventId=calendar_event.google_event_id,
        ).execute()
        existing_description = google_event.get("description") or ""
        appended_text = appended_text.strip()
        google_event["description"] = _replace_managed_work_report_block(existing_description, appended_text)

        service.events().update(
            calendarId=calendar_event.google_calendar_id,
            eventId=calendar_event.google_event_id,
            body=google_event,
        ).execute()
    except HttpError as exc:
        logger.error(
            "Google Calendar API failed while updating CalendarEvent %s: %s",
            calendar_event.id,
            exc,
            exc_info=True,
        )
        _audit_calendar_update(calendar_event_id=calendar_event.id, success=False, appended_text=appended_text)
        return False
    except Exception as exc:
        logger.error(
            "Unexpected failure while updating Google Calendar event for CalendarEvent %s: %s",
            calendar_event.id,
            exc,
            exc_info=True,
        )
        _audit_calendar_update(calendar_event_id=calendar_event.id, success=False, appended_text=appended_text)
        return False

    calendar_event.description = google_event["description"]
    calendar_event.last_synced_at = timezone.now()
    calendar_event.save(update_fields=["description", "last_synced_at", "updated_at"])
    logger.info(
        "Updated Google Calendar event %s on calendar %s for CalendarEvent %s.",
        calendar_event.google_event_id,
        calendar_event.google_calendar_id,
        calendar_event.id,
    )
    _audit_calendar_update(
        calendar_event_id=calendar_event.id,
        success=True,
        appended_text=appended_text,
        technician_id=calendar_event.technician_id,
        google_event_id=calendar_event.google_event_id,
    )
    return True


def _replace_managed_work_report_block(existing_description, new_block):
    existing_description = (existing_description or "").rstrip()
    new_block = (new_block or "").strip()
    if not existing_description:
        return new_block

    marker_index = existing_description.find(WORK_REPORT_BLOCK_START)
    if marker_index == -1:
        return f"{existing_description}\n\n{new_block}"

    base_description = existing_description[:marker_index].rstrip()
    if not base_description:
        return new_block
    return f"{base_description}\n\n{new_block}"


def _audit_calendar_sync(*, technician_id, summary):
    log_audit_event(
        "calendar.sync",
        target=f"technician:{technician_id}",
        metadata={
            "created": summary.get("created", 0),
            "updated": summary.get("updated", 0),
            "skipped": summary.get("skipped", 0),
            "has_error": bool(summary.get("error")),
        },
    )


def _audit_calendar_update(*, calendar_event_id, success, appended_text, technician_id=None, google_event_id=""):
    log_audit_event(
        "calendar.update_description",
        target=f"calendar_event:{calendar_event_id}",
        metadata={
            "success": success,
            "technician_id": technician_id,
            "google_event_id": google_event_id,
            "appended_text_length": len(appended_text or ""),
        },
    )


def _build_sync_window(start_date=None, end_date=None):
    today = timezone.localdate()
    start_value = start_date or today - timedelta(days=1)
    end_value = end_date or today + timedelta(days=14)
    start_dt = _coerce_to_aware_datetime(start_value, time.min)
    end_dt = _coerce_to_aware_datetime(end_value, time.max)
    return start_dt, end_dt


def _coerce_to_aware_datetime(value, default_time):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = parse_datetime(value)
        if parsed is None:
            parsed_date = parse_date(value)
            parsed = datetime.combine(parsed_date, default_time) if parsed_date else None
    else:
        parsed = datetime.combine(value, default_time)

    if parsed is None:
        raise ValueError(f"Invalid date/datetime value: {value}")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _parse_google_event_datetime(value, default_tz):
    raw_value = value.get("dateTime")
    event_timezone = value.get("timeZone") or default_tz
    if raw_value:
        parsed = parse_datetime(raw_value)
        if parsed and timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed, event_timezone

    raw_date = value.get("date")
    if raw_date:
        parsed_date = parse_date(raw_date)
        if parsed_date:
            return timezone.make_aware(
                datetime.combine(parsed_date, time.min),
                timezone.get_current_timezone(),
            ), event_timezone
    return None, event_timezone


def _infer_event_status(title):
    normalized = title.lower()
    if any(term in normalized for term in ("cancel", "canceled", "cancelled")):
        return CalendarEventStatus.CANCELED
    if any(term in normalized for term in ("reschedule", "rescheduled")):
        return CalendarEventStatus.RESCHEDULED
    if "fake" in normalized:
        return CalendarEventStatus.FAKE
    return CalendarEventStatus.SCHEDULED


def _infer_event_type(title, location):
    if location:
        return CalendarEventType.JOB
    if _is_job_like_title(title):
        return CalendarEventType.JOB
    return CalendarEventType.OTHER


def _is_job_like_title(title):
    normalized = title.lower()
    if re.match(r"^\s*\d+\.\s+", title):
        return True
    job_terms = ("job", "service", "repair", "install", "cleaning", "maintenance", "duct", "dryer", "chimney", "hvac")
    return any(term in normalized for term in job_terms)


def _extract_job_number(title):
    match = re.match(r"^\s*(\d+)\.\s+", title)
    return match.group(1) if match else None


def _coerce_to_date(value):
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return timezone.localtime(value).date()
    parsed = parse_date(str(value))
    if parsed is None:
        raise ValueError(f"Invalid date value: {value}")
    return parsed


def _get_active_job_events_for_schedule(technician, target_date):
    inactive_statuses = [
        CalendarEventStatus.CANCELED,
        CalendarEventStatus.RESCHEDULED,
        CalendarEventStatus.FAKE,
    ]
    return (
        CalendarEvent.objects.filter(
            technician=technician,
            event_type=CalendarEventType.JOB,
            start_at__date=target_date,
            start_at__time__gte=time(8, 0),
        )
        .exclude(status__in=inactive_statuses)
        .order_by("start_at")
    )


def _format_schedule_time(value):
    local_value = timezone.localtime(value)
    if local_value.minute:
        return local_value.strftime("%I:%M").lstrip("0")
    return local_value.strftime("%I").lstrip("0")
