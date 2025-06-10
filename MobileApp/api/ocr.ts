import apiClient from './client';

export const ocrApi = {
  processImage: async (imageFile: FormData) => {
    const response = await apiClient.post('/ocr/process-image', imageFile, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  processAndSave: async (imageFile: FormData, options?: { 
    auto_save?: boolean;
    notes?: string;
  }) => {
    const response = await apiClient.post('/ocr/process-and-save', imageFile, {
      params: options,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};