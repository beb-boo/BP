import apiClient from './client';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface UserCreate {
  email: string;
  full_name: string;
  password: string;
  confirm_password: string;
  citizen_id?: string;
  medical_license?: string;
  date_of_birth?: string;
  gender?: string;
  blood_type?: string;
  height?: number;
  weight?: number;
  role?: string;
}

export interface UserLogin {
  email: string;
  password: string;
}

export const authApi = {
  register: async (userData: UserCreate) => {
    const response = await apiClient.post('/auth/register', userData);
    return response.data;
  },

  login: async (credentials: UserLogin) => {
    const response = await apiClient.post('/auth/login', credentials);
    if (response.data.access_token) {
      await AsyncStorage.setItem('token', response.data.access_token);
    }
    return response.data;
  },

  logout: async () => {
    await AsyncStorage.removeItem('token');
  },

  getCurrentUser: async () => {
    const response = await apiClient.get('/users/me');
    return response.data;
  },
};