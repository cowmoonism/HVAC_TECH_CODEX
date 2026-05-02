import type { ReactNode } from "react";

type AsyncStateProps = {
  loading: boolean;
  error: string;
  children: ReactNode;
};

export function AsyncState({ loading, error, children }: AsyncStateProps) {
  if (loading) {
    return <div className="panel muted-panel">Loading...</div>;
  }

  if (error) {
    return <div className="panel error-panel">{error}</div>;
  }

  return <>{children}</>;
}
