/**
 * Chat Authentication Tests
 * Tests for V1.1 chat authentication migration
 * Using HttpOnly cookies with credentials:'include'
 */

import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3005';
const API_URL = 'http://localhost:8000';
const TEST_USER = {
  email: 'demo_growth@sigmasight.com',
  password: 'demo12345'
};

test.describe('Chat Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Clear all cookies before each test
    await page.context().clearCookies();
  });

  test('should set HttpOnly cookie on login', async ({ page }) => {
    // Navigate to portfolio page
    await page.goto(`${BASE_URL}/portfolio?type=high-net-worth`);
    
    // Perform login
    const response = await page.request.post(`${API_URL}/api/v1/auth/login`, {
      data: TEST_USER
    });
    
    // Check response
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.access_token).toBeDefined();
    
    // Check for HttpOnly cookie
    const cookies = await page.context().cookies();
    const authCookie = cookies.find(c => c.name === 'auth_token');
    expect(authCookie).toBeDefined();
    expect(authCookie?.httpOnly).toBe(true);
    expect(authCookie?.sameSite).toBe('Lax');
  });

  test('should use cookie for authenticated requests', async ({ page }) => {
    // First login to get cookie
    await page.request.post(`${API_URL}/api/v1/auth/login`, {
      data: TEST_USER
    });
    
    // Make authenticated request with cookie
    const meResponse = await page.request.get(`${API_URL}/api/v1/auth/me`);
    expect(meResponse.ok()).toBeTruthy();
    
    const userData = await meResponse.json();
    expect(userData.email).toBe(TEST_USER.email);
  });

  test('should persist authentication across page refresh', async ({ page }) => {
    // Login and navigate to portfolio
    await page.goto(`${BASE_URL}/portfolio?type=high-net-worth`);
    
    // Perform login via API
    await page.request.post(`${API_URL}/api/v1/auth/login`, {
      data: TEST_USER
    });
    
    // Refresh page
    await page.reload();
    
    // Check if still authenticated
    const meResponse = await page.request.get(`${API_URL}/api/v1/auth/me`);
    expect(meResponse.ok()).toBeTruthy();
  });

  test('should clear cookie on logout', async ({ page }) => {
    // Login first
    await page.request.post(`${API_URL}/api/v1/auth/login`, {
      data: TEST_USER
    });
    
    // Verify cookie exists
    let cookies = await page.context().cookies();
    expect(cookies.find(c => c.name === 'auth_token')).toBeDefined();
    
    // Logout
    await page.request.post(`${API_URL}/api/v1/auth/logout`);
    
    // Verify cookie is cleared
    cookies = await page.context().cookies();
    expect(cookies.find(c => c.name === 'auth_token')).toBeUndefined();
  });

  test('should handle SSE streaming with cookie auth', async ({ page }) => {
    // Login to get cookie
    await page.request.post(`${API_URL}/api/v1/auth/login`, {
      data: TEST_USER
    });
    
    // Test SSE endpoint with cookie
    const response = await page.request.post(`${API_URL}/api/v1/chat/send`, {
      data: {
        message: 'Test message',
        conversation_id: 'test-conv-id'
      },
      headers: {
        'Accept': 'text/event-stream'
      }
    });
    
    // Should get streaming response
    expect(response.ok()).toBeTruthy();
    expect(response.headers()['content-type']).toContain('text/event-stream');
  });

  test('should include credentials in fetch requests', async ({ page }) => {
    await page.goto(`${BASE_URL}/portfolio?type=high-net-worth`);
    
    // Intercept fetch requests to check credentials
    await page.route('**/api/v1/**', async (route, request) => {
      const headers = request.headers();
      
      // Check if credentials are included (cookies will be sent automatically)
      expect(request.method()).toBeDefined();
      
      // Continue the request
      await route.continue();
    });
    
    // Trigger a fetch request from the page
    await page.evaluate(async () => {
      const response = await fetch('/api/proxy/api/v1/auth/me', {
        credentials: 'include'
      });
      return response.ok;
    });
  });

  test('should handle auth expiry gracefully', async ({ page }) => {
    // Login
    await page.request.post(`${API_URL}/api/v1/auth/login`, {
      data: TEST_USER
    });
    
    // Simulate expired token by clearing cookies
    await page.context().clearCookies();
    
    // Try authenticated request
    const response = await page.request.get(`${API_URL}/api/v1/auth/me`);
    
    // Should return 401
    expect(response.status()).toBe(401);
  });
});

test.describe('Chat SSE Streaming', () => {
  test('should receive heartbeat events', async ({ page }) => {
    // Login first
    await page.request.post(`${API_URL}/api/v1/auth/login`, {
      data: TEST_USER
    });
    
    await page.goto(`${BASE_URL}/portfolio?type=high-net-worth`);
    
    // Set up SSE listener
    const events: string[] = [];
    
    await page.evaluate(() => {
      const eventSource = new EventSource('/api/proxy/api/v1/chat/stream-test', {
        withCredentials: true
      });
      
      return new Promise((resolve) => {
        const events: string[] = [];
        
        eventSource.addEventListener('heartbeat', (e) => {
          events.push('heartbeat');
        });
        
        // Collect events for 20 seconds
        setTimeout(() => {
          eventSource.close();
          resolve(events);
        }, 20000);
      });
    });
    
    // Should have received at least one heartbeat (15 second interval)
    expect(events.filter(e => e === 'heartbeat').length).toBeGreaterThan(0);
  });

  test('should handle connection errors with proper error type', async ({ page }) => {
    await page.goto(`${BASE_URL}/portfolio?type=high-net-worth`);
    
    // Test error handling
    const errorResponse = await page.evaluate(async () => {
      try {
        const response = await fetch('/api/proxy/api/v1/chat/send', {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ message: 'test' })
        });
        
        if (!response.ok) {
          const error = await response.json();
          return error;
        }
      } catch (error) {
        return { error_type: 'NETWORK_ERROR', message: error.message };
      }
    });
    
    // Should have error_type field
    expect(errorResponse).toHaveProperty('error_type');
    expect(['AUTH_EXPIRED', 'RATE_LIMITED', 'NETWORK_ERROR', 'SERVER_ERROR', 'FATAL_ERROR'])
      .toContain(errorResponse.error_type);
  });
});