import { describe, it, expect, beforeEach, vi } from 'vitest';
import { analyticsApi } from '@/services/analyticsApi';

declare const global: any;

describe('analyticsApi', () => {
  beforeEach(() => {
    // @ts-ignore
    global.fetch = vi.fn(async (input: RequestInfo, init?: RequestInit) => {
      // Basic JSON stub
      const body = JSON.stringify({ ok: true });
      return new Response(body, {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    });
    // localStorage mock
    const store: Record<string, string> = { access_token: 'test-token' };
    // @ts-ignore
    global.localStorage = {
      getItem: (k: string) => store[k] ?? null,
      setItem: (k: string, v: string) => { store[k] = v; },
      removeItem: (k: string) => { delete store[k]; },
      clear: () => { Object.keys(store).forEach((k) => delete store[k]); },
    };
  });

  it('calls overview with Authorization header and returns url', async () => {
    const { data, url } = await analyticsApi.getOverview('pid-123');
    expect(data).toBeDefined();
    expect(typeof url).toBe('string');
    // Verify fetch called with the full URL and Authorization header
    const call = (global.fetch as any).mock.calls[0];
    expect(String(call[0])).toContain('/api/v1/analytics/portfolio/pid-123/overview');
    expect(call[1].headers.Authorization).toBe('Bearer test-token');
  });
});

