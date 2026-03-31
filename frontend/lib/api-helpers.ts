import axios from "axios";

export interface ApiValidationIssue {
  msg: string;
}

export interface ApiErrorPayload {
  detail?: string | ApiValidationIssue[];
  message?: string;
  errors?: ApiValidationIssue[];
}

export interface ApiResponse<TData, TMeta = unknown> {
  status: string;
  message?: string;
  data: TData;
  meta?: TMeta;
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const payload = error.response?.data as ApiErrorPayload | undefined;
    const detail = payload?.detail ?? payload?.message ?? payload?.errors;

    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg).join(", ") || fallback;
    }

    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return fallback;
}