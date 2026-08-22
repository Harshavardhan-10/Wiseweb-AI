import type { ApiError, ApiErrorDetail } from "./types";

export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

export function errMessage(err: unknown): string {
  if (err && typeof err === "object" && "status" in err && "detail" in err) {
    const api = err as ApiError;
    if (typeof api.detail === "string") return api.detail;
    if (Array.isArray(api.detail)) {
      const first = api.detail[0] as ApiErrorDetail | undefined;
      if (first?.msg) return first.msg;
    }
    return `Request failed (${api.status})`;
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}
