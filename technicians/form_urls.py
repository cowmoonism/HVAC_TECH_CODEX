from django.urls import path

from technicians.form_views import contract_form, expense_form, report_form


urlpatterns = [
    path("report/", report_form, name="technician-form-report"),
    path("expense/", expense_form, name="technician-form-expense"),
    path("contract/", contract_form, name="technician-form-contract"),
]
