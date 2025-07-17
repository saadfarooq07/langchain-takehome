import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Unauthorized - redirect to login
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// API service functions
export const authService = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  
  register: (email: string, password: string, fullName?: string) =>
    api.post('/auth/register', { email, password, full_name: fullName }),
  
  logout: () => api.post('/auth/logout'),
};

export const analysisService = {
  analyze: (data: {
    log_content: string;
    application_name?: string;
    application_version?: string;
    environment_type?: string;
    environment_details?: any;
    enable_memory?: boolean;
  }) => api.post('/analyze', data),
  
  getHistory: (page: number = 1, pageSize: number = 10, applicationName?: string) =>
    api.get('/history', {
      params: { page, page_size: pageSize, application_name: applicationName },
    }),
  
  searchMemory: (query: string, applicationName?: string, limit: number = 10) =>
    api.post('/memory/search', {
      query,
      application_name: applicationName,
      context_type: 'analysis_history',
      limit,
    }),
};

export const applicationService = {
  getApplications: () => api.get('/applications'),
  
  getApplicationContext: (applicationName: string) =>
    api.get(`/applications/${applicationName}/context`),
  
  updateApplicationContext: (applicationName: string, context: any) =>
    api.post(`/applications/${applicationName}/context`, context),
};

export const userService = {
  getPreferences: () => api.get('/user/preferences'),
  
  updatePreferences: (preferences: any) =>
    api.post('/user/preferences', preferences),
};