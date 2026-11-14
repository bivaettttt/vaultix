import type { ReactNode } from "react";
import { ApiError } from "./api";

export function ErrorNotice({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <p className="error" role="alert">
      {error instanceof Error ? error.message : "Ошибка запроса."}
      {error instanceof ApiError && error.requestId && (
        <small>Запрос {error.requestId}</small>
      )}
    </p>
  );
}

export function Page({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children?: ReactNode;
}) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}
