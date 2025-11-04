/**
 * Comprehensive API Client with fetch wrapper
 * Provides axios-like functionality without dependencies
 */

// Custom Error Types
export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data?: any,
    public url?: string
  ) {
    super(`API Error: ${status} ${statusText}`);
    this.name = 'ApiError';
  }
}

export class NetworkError extends Error {
  constructor(message: string, public originalError: Error) {
    super(`Network Error: ${message}`);
    this.name = 'NetworkError';
  }
}

export class TimeoutError extends Error {
  constructor(timeout: number) {
    super(`Request timeout after ${timeout}ms`);
    this.name = 'TimeoutError';
  }
}

// Request/Response Types
export interface ApiRequestConfig {
  timeout?: number;
  retries?: number;
  retryDelay?: number;
  cache?: boolean;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

export interface ApiResponse<T = any> {
  data: T;
  status: number;
  statusText: string;
  headers: Headers;
  url: string;
}

// Request/Response Interceptor Types
export type RequestInterceptor = (url: string, config: RequestInit) => Promise<{ url: string; config: RequestInit }> | { url: string; config: RequestInit };
export type ResponseInterceptor = <T>(response: ApiResponse<T>) => Promise<ApiResponse<T>> | ApiResponse<T>;
export type ErrorInterceptor = (error: Error) => Promise<Error> | Error | never;

// Main API Client Class
export class ApiClient {
  private baseURL: string;
  private defaultTimeout: number;
  private defaultRetries: number;
  private defaultRetryDelay: number;
  private requestInterceptors: RequestInterceptor[] = [];
  private responseInterceptors: ResponseInterceptor[] = [];
  private errorInterceptors: ErrorInterceptor[] = [];

  constructor(
    baseURL: string = process.env.NEXT_PUBLIC_API_BASE_URL || (typeof window !== 'undefined' ? '/api/proxy' : 'http://localhost:8000'),
    options: {
      timeout?: number;
      retries?: number;
      retryDelay?: number;
    } = {}
  ) {
    this.baseURL = baseURL.replace(/\/$/, ''); // Remove trailing slash
    this.defaultTimeout = options.timeout || 30000;
    this.defaultRetries = options.retries || 2;
    this.defaultRetryDelay = options.retryDelay || 1000;
  }

  // Interceptor Management
  addRequestInterceptor(interceptor: RequestInterceptor): void {
    this.requestInterceptors.push(interceptor);
  }

  addResponseInterceptor(interceptor: ResponseInterceptor): void {
    this.responseInterceptors.push(interceptor);
  }

  addErrorInterceptor(interceptor: ErrorInterceptor): void {
    this.errorInterceptors.push(interceptor);
  }

  // Main HTTP Methods
  async get<T = any>(endpoint: string, config?: ApiRequestConfig): Promise<T> {
    return this.request<T>('GET', endpoint, undefined, config);
  }

  async post<T = any>(endpoint: string, data?: any, config?: ApiRequestConfig): Promise<T> {
    return this.request<T>('POST', endpoint, data, config);
  }

  async put<T = any>(endpoint: string, data?: any, config?: ApiRequestConfig): Promise<T> {
    return this.request<T>('PUT', endpoint, data, config);
  }

  async patch<T = any>(endpoint: string, data?: any, config?: ApiRequestConfig): Promise<T> {
    return this.request<T>('PATCH', endpoint, data, config);
  }

  async delete<T = any>(endpoint: string, data?: any, config?: ApiRequestConfig): Promise<T> {
    return this.request<T>('DELETE', endpoint, data, config);
  }

  // Core Request Method
  private async request<T>(
    method: string,
    endpoint: string,
    data?: any,
    config?: ApiRequestConfig
  ): Promise<T> {
    const url = endpoint.startsWith('http') ? endpoint : `${this.baseURL}${endpoint}`;
    const timeout = config?.timeout || this.defaultTimeout;
    const retries = config?.retries !== undefined ? config.retries : this.defaultRetries;

    let lastError: Error = new Error('Request failed');
    
    // Retry logic with exponential backoff
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        // Don't pass the original signal to executeRequest for retries
        // Only pass it on the first attempt
        const requestConfig = attempt === 0 ? config : { ...config, signal: undefined };
        const response = await this.executeRequest<T>(method, url, data, requestConfig, timeout);
        return response.data;
      } catch (error) {
        lastError = error as Error;
        
        // Don't retry on client errors (4xx) or non-network errors
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          break;
        }
        
        // Don't retry if the user's abort signal was triggered
        if (config?.signal?.aborted) {
          break;
        }
        
        // Don't retry on the last attempt
        if (attempt === retries) {
          break;
        }
        
        // Wait before retrying with exponential backoff
        const delay = (config?.retryDelay || this.defaultRetryDelay) * Math.pow(2, attempt);
        await this.sleep(delay);
        
        if (process.env.NODE_ENV === 'development') {
          console.warn(`API request failed, retrying in ${delay}ms (attempt ${attempt + 1}/${retries + 1})`);
        }
      }
    }
    
    // Apply error interceptors
    for (const interceptor of this.errorInterceptors) {
      lastError = await Promise.resolve(interceptor(lastError));
    }
    
    throw lastError;
  }

  // Execute single request
  private async executeRequest<T>(
    method: string,
    url: string,
    data?: any,
    config?: ApiRequestConfig,
    timeout?: number
  ): Promise<ApiResponse<T>> {
    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutDuration = timeout ?? this.defaultTimeout;
    let timeoutTriggered = false;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    if (timeoutDuration && timeoutDuration > 0) {
      timeoutId = setTimeout(() => {
        timeoutTriggered = true;
        controller.abort();
      }, timeoutDuration);
    }

    let externalAbortCleanup: (() => void) | null = null;
    if (config?.signal) {
      if (config.signal.aborted) {
        controller.abort(config.signal.reason);
      } else {
        const onExternalAbort = () => {
          controller.abort(config.signal?.reason);
        };
        config.signal.addEventListener('abort', onExternalAbort, { once: true });
        externalAbortCleanup = () => {
          config.signal?.removeEventListener('abort', onExternalAbort);
        };
      }
    }

    try {
      // Build request configuration
      let requestConfig: RequestInit = {
        method,
        headers: {
          ...config?.headers,
        },
        signal: controller.signal,
      };

      // Add body for POST/PUT/PATCH/DELETE requests
      if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH' || method === 'DELETE')) {
        // Check if data is FormData - don't stringify it or set Content-Type
        if (data instanceof FormData) {
          requestConfig.body = data;
          // Don't set Content-Type - browser will set it with boundary
        } else {
          // For JSON data, stringify and set Content-Type
          requestConfig.headers = {
            'Content-Type': 'application/json',
            ...requestConfig.headers,
          };
          requestConfig.body = JSON.stringify(data);
        }
      } else {
        // For GET/DELETE requests, set JSON content type
        requestConfig.headers = {
          'Content-Type': 'application/json',
          ...requestConfig.headers,
        };
      }

      // Apply request interceptors
      let finalUrl = url;
      for (const interceptor of this.requestInterceptors) {
        const result = await Promise.resolve(interceptor(finalUrl, requestConfig));
        finalUrl = result.url;
        requestConfig = result.config;
      }

      if (process.env.NODE_ENV === 'development') {
        console.log(`🚀 API Request: ${method} ${finalUrl}`, {
          headers: requestConfig.headers,
          body: requestConfig.body,
        });
      }

      // Execute fetch request
      const response = await fetch(finalUrl, requestConfig);

      // Check if request was successful
      if (!response.ok) {
        let errorData;
        const contentType = response.headers.get('content-type');
        
        // Read the response body as text first
        const responseText = await response.text();
        
        // Try to parse as JSON if content type indicates JSON
        if (contentType && contentType.includes('application/json')) {
          try {
            errorData = JSON.parse(responseText);
          } catch {
            errorData = responseText;
          }
        } else {
          errorData = responseText;
        }
        
        throw new ApiError(response.status, response.statusText, errorData, finalUrl);
      }

      // Parse response data
      let responseData: T;
      const contentType = response.headers.get('content-type');
      
      if (contentType && contentType.includes('application/json')) {
        responseData = await response.json();
      } else {
        responseData = await response.text() as any;
      }

      const apiResponse: ApiResponse<T> = {
        data: responseData,
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
        url: finalUrl,
      };

      if (process.env.NODE_ENV === 'development') {
        console.log(`✅ API Response: ${method} ${finalUrl}`, {
          status: response.status,
          data: responseData,
        });
      }

      // Apply response interceptors
      let finalResponse = apiResponse;
      for (const interceptor of this.responseInterceptors) {
        finalResponse = await Promise.resolve(interceptor(finalResponse));
      }

      return finalResponse;

    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      
      // Handle different error types
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          if (timeoutTriggered) {
            throw new TimeoutError(timeoutDuration || this.defaultTimeout);
          }
          throw error;
        }
        
        throw new NetworkError(error.message, error);
      }
      
      throw new NetworkError('Unknown network error', error as Error);
    } finally {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      if (externalAbortCleanup) {
        externalAbortCleanup();
      }
    }
  }

  // Utility method for delays
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Request URL builder
  buildUrl(endpoint: string, params?: Record<string, string | number | boolean>): string {
    const url = endpoint.startsWith('http') ? endpoint : `${this.baseURL}${endpoint}`;
    
    if (!params || Object.keys(params).length === 0) {
      return url;
    }
    
    const urlObj = new URL(url);
    Object.entries(params).forEach(([key, value]) => {
      urlObj.searchParams.set(key, String(value));
    });
    
    return urlObj.toString();
  }

  // Configuration getters
  getBaseURL(): string {
    return this.baseURL;
  }

  setBaseURL(baseURL: string): void {
    this.baseURL = baseURL.replace(/\/$/, '');
  }
}

// Default instance - uses Next.js proxy for backend API calls
export const apiClient = new ApiClient('/api/proxy');

// Add default request interceptor for auth
apiClient.addRequestInterceptor(async (url, config) => {
  // Get token from localStorage (where authManager stores it)
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;

  if (token) {
    config.headers = {
      ...config.headers,
      'Authorization': `Bearer ${token}`,
    };
  }

  return { url, config };
});

// Add default response interceptor for logging
apiClient.addResponseInterceptor((response) => {
  if (process.env.NODE_ENV === 'development') {
    // Additional response processing can go here
  }
  return response;
});

// Add default error interceptor
apiClient.addErrorInterceptor((error) => {
  if (process.env.NODE_ENV === 'development') {
    console.error('🚨 API Error:', error);
  }
  
  // You can transform errors here if needed
  return error;
});

export default apiClient;
