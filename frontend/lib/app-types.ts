export interface AppUser {
  id?: number;
  full_name: string;
  role: string;
  verification_status?: "pending" | "verified" | "rejected";
  language?: string;
  email?: string | null;
  phone_number?: string | null;
  citizen_id?: string | null;
  medical_license?: string | null;
  date_of_birth?: string | null;
  gender?: string | null;
  blood_type?: string | null;
  height?: number | null;
  weight?: number | null;
  timezone?: string | null;
  is_email_verified?: boolean;
  telegram_id?: number | null;
  // Subscription fields (present on login, /users/me, /payment/* responses)
  subscription_tier?: "free" | "premium";
  is_premium_active?: boolean;
  subscription_expires_at?: string | null;
  days_remaining?: number;
}

export interface PaginationMeta {
  current_page: number;
  total_pages: number;
  total?: number;
  per_page?: number;
}

export interface BPRecord {
  id: number;
  systolic: number;
  diastolic: number;
  pulse: number;
  measurement_date: string;
  measurement_time?: string;
  notes?: string | null;
}

export interface Classification {
  level: string;
  label_en: string;
  label_th: string;
}

export interface Trend {
  systolic_slope: number;
  diastolic_slope: number;
  systolic_r_squared?: number;
  diastolic_r_squared?: number;
  direction: string;
  confidence?: string;
}

export interface BPStats {
  systolic: { avg: number; min: number; max: number; sd?: number; cv?: number };
  diastolic: { avg: number; min: number; max: number; sd?: number };
  pulse: { avg: number; min: number; max: number };
  classification?: Classification;
  pulse_pressure?: { avg: number };
  map?: { avg: number };
  trend?: Trend;
  total_records_period: number;
  total_records_all_time: number;
}

export interface OCRResultPayload {
  systolic?: number | null;
  diastolic?: number | null;
  pulse?: number | null;
  measurement_date?: string | null;
  measurement_time?: string | null;
  error?: string | null;
}

export interface AuthorizedDoctor {
  doctor_id: number;
  full_name: string;
  hospital?: string | null;
}

export interface DoctorSearchResult {
  doctor_id: number;
  full_name: string;
  license_year?: number | null;
}

export interface AccessRequestItem {
  request_id: number;
  doctor_name?: string;
  patient_name?: string;
  status: string;
  created_at: string;
}

export interface PatientSummary {
  patient_id: number;
  full_name: string;
  gender?: string | null;
  age?: number | null;
}

export interface PaymentAccount {
  bank: string;
  account_number: string;
  account_name: string;
}

export interface Plan {
  plan_type: string;
  name: string;
  name_en: string;
  price: number;
  duration_days: number;
  features: string[];
}

// Subscription state returned from login, /users/me, and /payment/* endpoints
export interface SubscriptionInfo {
  subscription_tier: "free" | "premium";
  is_premium_active: boolean;
  subscription_expires_at: string | null;
  days_remaining: number;
}

// Admin types
export interface AdminUserItem {
  id: number;
  role: string;
  verification_status?: string;
  is_active: boolean;
  full_name_masked: string;
  email_masked?: string | null;
  phone_masked?: string | null;
  medical_license_masked?: string | null;
  subscription_tier: string;
  subscription_expires_at?: string | null;
  created_at: string;
  last_login?: string | null;
  verification_logs?: string | null;
}

export interface AdminAuditEntry {
  id: number;
  admin_user_id: number;
  action: string;
  target_user_id?: number | null;
  details?: string | null;
  created_at: string;
}