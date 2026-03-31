
import axios from "axios";

// ── Telegram WebApp Types ──

export interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  is_premium?: boolean;
}

export interface TelegramThemeParams {
  bg_color?: string;
  text_color?: string;
  hint_color?: string;
  link_color?: string;
  button_color?: string;
  button_text_color?: string;
  secondary_bg_color?: string;
}

export interface TelegramMainButton {
  text: string;
  color: string;
  textColor: string;
  isVisible: boolean;
  isActive: boolean;
  show(): void;
  hide(): void;
  onClick(callback: () => void): void;
  offClick(callback: () => void): void;
  showProgress(leaveActive?: boolean): void;
  hideProgress(): void;
}

export interface TelegramWebApp {
  ready(): void;
  expand(): void;
  close(): void;
  showAlert(message: string, callback?: () => void): void;
  showConfirm(
    message: string,
    callback?: (confirmed: boolean) => void
  ): void;
  initData: string;
  initDataUnsafe: {
    query_id?: string;
    user?: TelegramUser;
    auth_date: number;
    hash: string;
  };
  themeParams: TelegramThemeParams;
  MainButton: TelegramMainButton;
  BackButton: {
    isVisible: boolean;
    show(): void;
    hide(): void;
    onClick(callback: () => void): void;
    offClick(callback: () => void): void;
  };
  colorScheme: "light" | "dark";
  viewportHeight: number;
  viewportStableHeight: number;
}

declare global {
  interface Window {
    Telegram?: {
      WebApp: TelegramWebApp;
    };
  }
}

// ── Helpers ──

export function getTelegramWebApp(): TelegramWebApp | null {
  if (typeof window !== "undefined" && window.Telegram?.WebApp) {
    return window.Telegram.WebApp;
  }
  return null;
}

export function isTelegramWebView(): boolean {
  return getTelegramWebApp() !== null;
}

// ── Telegram-specific Axios instance ──
// Uses JWT from mini-app-auth (set via setTelegramToken)
// Also sends API key for existing endpoint compatibility

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "bp-web-app-key";

let _telegramToken: string | null = null;

export const telegramApi = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
});

telegramApi.interceptors.request.use((config) => {
  if (_telegramToken) {
    config.headers.Authorization = `Bearer ${_telegramToken}`;
  }
  config.headers["X-API-Key"] = API_KEY;
  return config;
});

// Don't redirect on 401 — just reject (Mini App handles errors in-page)
telegramApi.interceptors.response.use(
  (r) => r,
  (err) => Promise.reject(err)
);

export function setTelegramToken(token: string) {
  _telegramToken = token;
}
