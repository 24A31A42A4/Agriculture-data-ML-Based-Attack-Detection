import axios from 'axios';

// Configure standard axios instance
const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Since the backend uses OAuth2 with Bearer tokens, we'll need a mechanism to 
// automatically inject the token. For this simple demo frontend, we can either
// skip auth (if we temporarily disabled it) or hardcode a login step.
// For now, we will add an interceptor that attaches a token if it exists.

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const getHealthSummary = () => api.get('/devices/health/summary');
export const getActiveModels = () => api.get('/ml/models');

// Device Endpoints
export const getDevices = () => api.get('/devices');
export const resetDeviceTrust = (deviceId) => api.post(`/devices/${deviceId}/reset-trust`);
export const triggerTamperingSimulation = (deviceId) => api.post(`/attack-sim/data-tampering/${deviceId}`);
export const triggerReplaySimulation = (deviceId) => api.post(`/attack-sim/replay/${deviceId}`);
export const triggerMLAnomalySimulation = (deviceId) => api.post(`/attack-sim/ml-anomaly/${deviceId}`);
export const compareMLPredictions = (features) => api.post('/ml/compare', features);
export const checkFeatureDrift = () => api.post('/drift/check');

// New Endpoints for Dashboard
export const getAuditLogs = () => api.get('/audit/logs');
export const getBlockchainBlocks = () => api.get('/blockchain/blocks');

export const login = (username, password) => {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);
  return axios.post('/api/v1/auth/login/access-token', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  });
};
export const register = (data) => api.post('/auth/register', data);

export default api;
