import apiClient from './client';

export interface BloodPressureRecord {
  systolic: number;
  diastolic: number;
  pulse: number;
  measurement_date: string;
  measurement_time?: string;
  notes?: string;
}

export const bloodPressureApi = {
  getRecords: async (params?: { 
    skip?: number; 
    limit?: number;
    start_date?: string;
    end_date?: string;
  }) => {
    const response = await apiClient.get('/bp-records', { params });
    return response.data;
  },

  createRecord: async (record: BloodPressureRecord) => {
    const response = await apiClient.post('/bp-records', record);
    return response.data;
  },

  getRecord: async (recordId: number) => {
    const response = await apiClient.get(`/bp-records/${recordId}`);
    return response.data;
  },

  updateRecord: async (recordId: number, record: Partial<BloodPressureRecord>) => {
    const response = await apiClient.put(`/bp-records/${recordId}`, record);
    return response.data;
  },

  deleteRecord: async (recordId: number) => {
    const response = await apiClient.delete(`/bp-records/${recordId}`);
    return response.data;
  },
};