import apiClient from './client';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface UserCreate {
  email: any;
  phone_number: string;
  password: string;
  full_name: string;
  role: string;
  citizen_id?: string; 
  date_of_birth?: string;
  gender?: string;
  blood_type?: string;
  height?: number;
  weight?: number;
  medical_license?: any;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface OTPRequest {
  email: any;
  phone_number:string;
  purpose: string;
}

export interface OTPVerification{
  email: any;
  phone_number:string;
  otp_code: string;
  purpose: string;
}

export const authApi = {
  register: async (userData: UserCreate) => {
    const response = await apiClient.post('/api/v1/auth/register', userData);
    return response.data;
  },

  login: async (credentials: UserLogin) => {
    const response = await apiClient.post('/api/v1/auth/login', credentials);
    return response.data;
  },

  logout: async () => {
    const response = await apiClient.post('/api/v1/auth/logout');
    return response.data;
  },

  getCurrentUser: async () => {
    const response = await apiClient.get('/api/v1/users/me');
    return response.data;
  },
  requestOTP: async (otp_request: OTPRequest) => {
    const response = await apiClient.post('/api/v1/auth/request-otp', otp_request);
    return response.data;
  },
  verifyOTP: async (otp_vertify: OTPVerification) => {
    const response = await apiClient.post('/api/v1/auth/verify-otp', otp_vertify);
    return response.data;
  },
  verifyContact: async (data: { email?: string; phone_number?: string; otp_code: string; purpose: string }) => {
    const response = await apiClient.post('/api/v1/auth/verify-contact', data);
    return response.data;
  },
  changePassword: async (data: { current_password: string; new_password: string; confirm_new_password: string }) => {
    const response = await apiClient.post('/api/v1/auth/change-password', data);
    return response.data;
  },
  resetPassword: async (data: { email?: string; phone_number?: string; otp_code: string; new_password: string; confirm_new_password: string }) => {
    const response = await apiClient.post('/api/v1/auth/reset-password', data);
    return response.data;
  },
  updateProfile: async (data: any) => {
    const response = await apiClient.put('/api/v1/users/me', data);
    return response.data;
  },
  searchUsers: async (params: { q: string; role?: string; page?: number; per_page?: number }) => {
    const response = await apiClient.get('/api/v1/users/search', { params });
    return response.data;
  },
};