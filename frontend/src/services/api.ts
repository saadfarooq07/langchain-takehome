import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v2';
const AUTH_API_URL = process.env.REACT_APP_AUTH_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('allogator_access_token');
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
      localStorage.removeItem('allogator_access_token');
      localStorage.removeItem('allogator_refresh_token');
      localStorage.removeItem('allogator_user');
      window.location.href = '/onboarding';
    }
    return Promise.reject(error);
  }
);

export default api;

// Types
export interface User {
  id: string;
  email: string;
  full_name: string | null;
}

export interface Tenant {
  id: string;
  slug: string;
  name: string;
  role: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginResponse {
  user: User;
  tenant: Tenant;
  tokens: AuthTokens;
  available_tenants: Tenant[];
}

export interface TenantCreateRequest {
  name: string;
  slug: string;
  owner_email: string;
  owner_password: string;
  owner_name?: string;
  description?: string;
}

export interface TenantCreateResponse {
  message: string;
  tenant_id: string;
  tenant_slug: string;
  verification_required: boolean;
}

// Auth API client
const authApi = axios.create({
  baseURL: AUTH_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to auth API requests
authApi.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('allogator_access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// API service functions
export const authService = {
  createTenant: async (data: TenantCreateRequest): Promise<TenantCreateResponse> => {
    const response = await authApi.post('/api/v2/auth/tenants', data);
    return response.data;
  },

  login: async (email: string, password: string, tenant_slug?: string): Promise<LoginResponse> => {
    const response = await authApi.post('/api/v2/auth/login', { email, password, tenant_slug });
    const data = response.data;
    
    // Store tokens and user data
    localStorage.setItem('allogator_access_token', data.tokens.access_token);
    localStorage.setItem('allogator_refresh_token', data.tokens.refresh_token);
    localStorage.setItem('allogator_user', JSON.stringify({
      ...data.user,
      tenant: data.tenant,
      onboardingCompleted: true,
    }));
    
    // Dispatch custom event for auth state change
    window.dispatchEvent(new Event('auth-state-changed'));
    
    return data;
  },
  
  logout: async () => {
    try {
      await authApi.post('/api/v2/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear local storage regardless
      localStorage.removeItem('allogator_access_token');
      localStorage.removeItem('allogator_refresh_token');
      localStorage.removeItem('allogator_user');
      localStorage.removeItem('allogator_api_keys');
      
      // Dispatch custom event for auth state change
      window.dispatchEvent(new Event('auth-state-changed'));
      
      window.location.href = '/';
    }
  },

  googleAuth: async (credential: string): Promise<LoginResponse> => {
    const response = await authApi.post('/api/v2/auth/google', { credential });
    const data = response.data;
    
    // Store tokens and user data
    localStorage.setItem('allogator_access_token', data.tokens.access_token);
    localStorage.setItem('allogator_refresh_token', data.tokens.refresh_token);
    localStorage.setItem('allogator_user', JSON.stringify({
      ...data.user,
      tenant: data.tenant,
      onboardingCompleted: true,
    }));
    
    // Dispatch custom event for auth state change
    window.dispatchEvent(new Event('auth-state-changed'));
    
    return data;
  },

  getCurrentUser: async (): Promise<User | null> => {
    try {
      const response = await authApi.get('/api/v2/auth/me');
      return response.data;
    } catch (error) {
      console.error('Get current user error:', error);
      return null;
    }
  },
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
    
  getThreads: (page: number = 1, pageSize: number = 20) =>
    api.get('/threads', {
      params: { page, page_size: pageSize },
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

// API key storage (encrypted in production)
export const storeApiKeys = async (keys: { gemini: string; groq: string; tavily: string }): Promise<void> => {
  // In production, these would be encrypted and stored server-side
  // For now, we'll store them in localStorage
  localStorage.setItem('allogator_api_keys', JSON.stringify(keys));
  
  // TODO: Send to backend for secure storage
  // await authApi.post('/auth/api-keys', keys);
};

export const getStoredApiKeys = (): { gemini: string; groq: string; tavily: string } | null => {
  const keys = localStorage.getItem('allogator_api_keys');
  return keys ? JSON.parse(keys) : null;
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
  } catch (error: any) {
    console.error('Error analyzing log:', error);
    
    // If API is not available, return a mock response for demo purposes
    if (error.code === 'ERR_NETWORK' || error.message.includes('Network Error')) {
      return {
        executive_summary: {
          overview: "Mock analysis completed. The API server appears to be offline.",
          critical_issues: ["API server not reachable at http://localhost:8000"]
        },
        issues: [
          {
            severity: "high",
            type: "connection",
            description: "Cannot connect to the analysis API server",
            root_cause: "The backend server is not running or not accessible"
          }
        ],
        suggestions: [
          {
            issue: "API Connection Error",
            suggestions: [
              "Start the backend server with: python main.py",
              "Check that the server is running on port 8000",
              "Verify your network connection"
            ]
          }
        ],
        diagnostic_commands: [
          {
            command: "python main.py",
            description: "Start the backend API server"
          },
          {
            command: "curl http://localhost:8000/health",
            description: "Check if the API is responding"
          }
        ]
      };
    }
    
    throw error;
  }
};

// Streaming analysis function (works for both guest and authenticated users)
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
  const token = localStorage.getItem('allogator_access_token');
  const isGuest = !token;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Accept': 'text/event-stream',
  };
  
  // Add guest header if no token
  if (isGuest) {
    headers['X-Guest-Mode'] = 'true';
  } else {
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