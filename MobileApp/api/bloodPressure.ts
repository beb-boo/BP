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
    page?: number;
    per_page?: number;
    start_date?: string;
    end_date?: string;
  }) => {
    const response = await apiClient.get('/api/v1/bp-records', { params });
    return response.data;
  },

  createRecord: async (record: BloodPressureRecord) => {
    const response = await apiClient.post('/api/v1/bp-records', record);
    return response.data;
  },

  getRecord: async (recordId: number) => {
    const response = await apiClient.get(`/api/v1/bp-records/${recordId}`);
    return response.data;
  },

  updateRecord: async (recordId: number, record: Partial<BloodPressureRecord>) => {
    const response = await apiClient.put(`/api/v1/bp-records/${recordId}`, record);
    return response.data;
  },

  deleteRecord: async (recordId: number) => {
    const response = await apiClient.delete(`/api/v1/bp-records/${recordId}`);
    return response.data;
  },

  processImage: async (file: any) => {
    const formData = new FormData();
    formData.append('file', file);
    console.log('api ',formData);
    const response = await apiClient.post('/api/v1/ocr/process-image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    console.log('processImg', response)
    return response.data;
  },

  saveFromOcr: async (record: BloodPressureRecord) => {
    const response = await apiClient.post('/api/v1/bp-records/save-from-ocr', record);
    return response.data;
  },
};