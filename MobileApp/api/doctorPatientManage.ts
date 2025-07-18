import apiClient from './client';

export const doctorPatientManageApi = {
  // Patient: authorize a doctor
  authorizeDoctor: async (doctor_id: number) => {
    const response = await apiClient.post('/api/v1/patient/authorize-doctor', { doctor_id });
    return response.data;
  },

  // Patient: get authorized doctors
  getAuthorizedDoctors: async () => {
    const response = await apiClient.get('/api/v1/patient/authorized-doctors');
    return response.data;
  },

  // Patient: revoke doctor access
  revokeDoctorAccess: async (doctor_id: number) => {
    const response = await apiClient.delete(`/api/v1/patient/authorized-doctors/${doctor_id}`);
    return response.data;
  },

  // Patient: view access requests
  viewAccessRequests: async () => {
    const response = await apiClient.get('/api/v1/patient/access-requests');
    return response.data;
  },

  // Patient: approve access request
  approveRequest: async (request_id: number, hospital?: string) => {
    // Always send { hospital: null } if hospital is not provided
    const response = await apiClient.post(
      `/api/v1/patient/access-requests/${request_id}/approve`);
    return response.data;
  },

  // Patient: reject access request
  rejectRequest: async (request_id: number) => {
    const response = await apiClient.post(`/api/v1/patient/access-requests/${request_id}/reject`);
    return response.data;
  },

  // Doctor: request access to patient
  requestPatientAccess: async (patient_id: number) => {
    const response = await apiClient.post('/api/v1/doctor/request-access', { patient_id });
    return response.data;
  },

  // Doctor: view their access requests
  doctorViewAccessRequests: async () => {
    const response = await apiClient.get('/api/v1/doctor/access-requests');
    return response.data;
  },

  // Doctor: get their patients
  getDoctorPatients: async (params?: { page?: number; per_page?: number }) => {
    const response = await apiClient.get('/api/v1/doctor/patients', { params });
    return response.data;
  },

  // Doctor: get a patient's BP records
  getPatientBPRecords: async (patient_id: number, params?: { page?: number; per_page?: number; start_date?: string; end_date?: string }) => {
    const response = await apiClient.get(`/api/v1/doctor/patients/${patient_id}/bp-records`, { params });
    return response.data;
  },

  // Doctor: delete a pending access request
  deleteAccessRequest: async (request_id: number) => {
    const response = await apiClient.delete(`/api/v1/doctor/access-requests/${request_id}`);
    return response.data;
  },

  // Doctor/Patient: search users
  searchUsers: async (params: { q: string; role?: string; page?: number; per_page?: number }) => {
    const response = await apiClient.get('/api/v1/users/search', { params });
    return response.data;
  },
};