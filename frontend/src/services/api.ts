import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v2';

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
    enable_enhanced_analysis?: boolean;
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

// Helper function for the Allogator UI
export const analyzeLog = async (data: {
  log_content: string;
  application_name?: string;
  enable_memory?: boolean;
}) => {
  try {
    const response = await analysisService.analyze({
      ...data,
      enable_enhanced_analysis: true, // Always use enhanced analysis for better output
    });
    return response.data;
  } catch (error) {
    console.error('Error analyzing log:', error);
    throw error;
  }
};

// Streaming analysis function
export const analyzeLogStream = async (
  data: {
    log_content: string;
    application_name?: string;
    enable_memory?: boolean;
    enable_enhanced_analysis?: boolean;
  },
  onProgress?: (event: any) => void,
  onResult?: (result: any) => void,
  onError?: (error: any) => void,
  onComplete?: () => void
) => {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Accept': 'text/event-stream',
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Use fetch for POST request with streaming response
  const response = await fetch(`${API_BASE_URL}/analyze/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      ...data,
      enable_enhanced_analysis: data.enable_enhanced_analysis !== false,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) {
    throw new Error('No response body');
  }

  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      
      // Keep the last incomplete line in the buffer
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6));
            
            switch (event.type) {
              case 'start':
                console.log('Analysis started:', event.data);
                break;
              case 'progress':
                onProgress?.(event.data);
                break;
              case 'result':
                onResult?.(event.data.analysis_result);
                break;
              case 'error':
                onError?.(event.data);
                break;
              case 'complete':
                onComplete?.();
                break;
            }
          } catch (e) {
            console.error('Error parsing SSE event:', e, 'Line:', line);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
};