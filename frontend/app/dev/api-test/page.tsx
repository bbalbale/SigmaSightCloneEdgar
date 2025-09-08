"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "@/services/apiClient";
import { analyticsApi } from "@/services/analyticsApi";

type Json = any;

type Result = {
  ok: boolean;
  status: number;
  data: Json;
  tookMs: number;
  url: string;
};

const pretty = (obj: unknown) => JSON.stringify(obj, null, 2);

// Helper to fetch /auth/me via apiClient (direct, JWT)
const fetchMe = async (token: string): Promise<Result> => {
  const endpoint = "/api/v1/auth/me";
  const url = apiClient.buildUrl(endpoint);
  const started = performance.now();
  try {
    const data = await apiClient.get<any>(endpoint, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const tookMs = Math.round(performance.now() - started);
    return { ok: true, status: 200, data, tookMs, url };
  } catch (e: any) {
    const tookMs = Math.round(performance.now() - started);
    const status = typeof e?.status === 'number' ? e.status : 0;
    return { ok: false, status, data: { error: String(e?.message || e) }, tookMs, url };
  }
};

export default function ApiTestPage() {
  const [portfolioId, setPortfolioId] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState<string[]>([]);
  const [results, setResults] = useState<Record<string, Result | null>>({});

  // Analytics params
  const [lookbackDays, setLookbackDays] = useState<number>(90);
  const [minOverlap, setMinOverlap] = useState<number>(30);
  const [posLimit, setPosLimit] = useState<number>(10);
  const [posOffset, setPosOffset] = useState<number>(0);
  const [scenarios, setScenarios] = useState<string>(""); // CSV optional

  const token = useMemo(() => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
  }, []);

  const appendLog = useCallback((line: string) => {
    setLog((l) => [
      `${new Date().toLocaleTimeString()}: ${line}`,
      ...l,
    ].slice(0, 200));
  }, []);

  const fetchPortfolioId = useCallback(async () => {
    if (!token) {
      appendLog("No token in localStorage. Please login at /login.");
      return;
    }
    setBusy(true);
    try {
      const res = await fetchMe(token);
      setResults((r) => ({ ...r, auth_me: res }));
      if (res.ok && res.data?.portfolio_id) {
        setPortfolioId(res.data.portfolio_id);
        appendLog(`Detected portfolio_id=${res.data.portfolio_id}`);
      } else {
        appendLog("/auth/me did not return portfolio_id.");
      }
    } finally {
      setBusy(false);
    }
  }, [token, appendLog]);

  const runAnalytics = useCallback(async () => {
    if (!token) {
      appendLog("No token in localStorage. Please login at /login.");
      return;
    }
    const pid = portfolioId.trim() || "<SET_ID>";
    setBusy(true);
    // Wrap service calls to include timing and a synthetic 200 status on success
    const measure = async <T,>(key: string, fn: () => Promise<{ data: T; url: string }>): Promise<[string, Result]> => {
      const started = performance.now();
      try {
        const { data, url } = await fn();
        return [key, { ok: true, status: 200, data, tookMs: Math.round(performance.now() - started), url }];
      } catch (e: any) {
        const status = typeof e?.status === 'number' ? e.status : 0;
        const url = '';
        return [key, { ok: false, status, data: { error: String(e?.message || e) }, tookMs: Math.round(performance.now() - started), url }];
      }
    };

    const entries = await Promise.all([
      measure('overview', () => analyticsApi.getOverview(pid)),
      measure('correlation_matrix', () => analyticsApi.getCorrelationMatrix(pid, { lookback_days: lookbackDays, min_overlap: minOverlap })),
      measure('factor_exposures', () => analyticsApi.getPortfolioFactorExposures(pid)),
      measure('positions_factor_exposures', () => analyticsApi.getPositionFactorExposures(pid, { limit: posLimit, offset: posOffset })),
      measure('stress_test', () => analyticsApi.getStressTest(pid, { scenarios: scenarios.trim() || undefined })),
    ]);
    setResults((r) => ({ ...r, ...Object.fromEntries(entries) }));
    appendLog("Finished analytics API calls.");
    setBusy(false);
  }, [token, portfolioId, lookbackDays, minOverlap, posLimit, posOffset, scenarios, appendLog]);

  useEffect(() => {
    // Auto-try to fetch portfolio id on load if token exists
    if (token && !portfolioId) {
      fetchPortfolioId();
    }
  }, [token, portfolioId, fetchPortfolioId]);

  return (
    <div className="max-w-screen-xl mx-auto p-6 space-y-8">
      <h1 className="text-2xl font-semibold">Analytics API Test Page</h1>
      <p className="text-sm text-gray-600">
        Calls analytics endpoints via proxy using <code>Authorization: Bearer &lt;token&gt;</code>. Login at <code>/login</code> first.
      </p>

      {/* Token/Portfolio */}
      <section className="border rounded-lg p-4 space-y-3">
        <h2 className="text-lg font-medium">Context</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
          <div className="text-xs text-gray-600 col-span-2">
            access_token: {token ? "present" : "missing"}
          </div>
          <label className="block md:col-span-2">
            <span className="text-sm">Portfolio ID</span>
            <input
              className="mt-1 w-full border rounded px-3 py-2"
              value={portfolioId}
              onChange={(e) => setPortfolioId(e.target.value)}
              placeholder="Detect or paste UUID"
            />
          </label>
          <div className="flex gap-2 md:col-span-4">
            <button onClick={fetchPortfolioId} disabled={busy} className="px-3 py-2 rounded border">
              Detect from /auth/me
            </button>
          </div>
        </div>
      </section>

      {/* Params */}
      <section className="border rounded-lg p-4 space-y-3">
        <h2 className="text-lg font-medium">Parameters</h2>
        <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
          <label className="block">
            <span className="text-sm">lookback_days</span>
            <input type="number" className="mt-1 w-full border rounded px-3 py-2" value={lookbackDays} onChange={(e) => setLookbackDays(parseInt(e.target.value || "0", 10))} />
          </label>
          <label className="block">
            <span className="text-sm">min_overlap</span>
            <input type="number" className="mt-1 w-full border rounded px-3 py-2" value={minOverlap} onChange={(e) => setMinOverlap(parseInt(e.target.value || "0", 10))} />
          </label>
          <label className="block">
            <span className="text-sm">positions limit</span>
            <input type="number" className="mt-1 w-full border rounded px-3 py-2" value={posLimit} onChange={(e) => setPosLimit(parseInt(e.target.value || "0", 10))} />
          </label>
          <label className="block">
            <span className="text-sm">positions offset</span>
            <input type="number" className="mt-1 w-full border rounded px-3 py-2" value={posOffset} onChange={(e) => setPosOffset(parseInt(e.target.value || "0", 10))} />
          </label>
          <label className="block md:col-span-2">
            <span className="text-sm">stress scenarios (CSV)</span>
            <input className="mt-1 w-full border rounded px-3 py-2" value={scenarios} onChange={(e) => setScenarios(e.target.value)} placeholder="market_down_10,rate_up_50bp" />
          </label>
        </div>
        <div className="flex gap-2">
          <button onClick={runAnalytics} disabled={busy} className="px-3 py-2 rounded bg-indigo-600 text-white disabled:opacity-50">
            Run All Analytics
          </button>
        </div>
      </section>

      {/* Results */}
      <section className="border rounded-lg p-4 space-y-3">
        <h2 className="text-lg font-medium">Results</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.entries(results).map(([key, value]) => (
            <div key={key} className="border rounded p-3">
              <div className="text-sm font-medium mb-1">{key}</div>
              {value ? (
                <>
                  <div className="text-xs text-gray-500 mb-1">
                    {value.ok ? "OK" : "ERR"} · {value.status} · {value.tookMs}ms · {value.url}
                  </div>
                  <pre className="text-xs whitespace-pre-wrap overflow-auto max-h-72">
                    {pretty(value.data)}
                  </pre>
                </>
              ) : (
                <div className="text-xs text-gray-500">No data</div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Log */}
      <section className="border rounded-lg p-4 space-y-2">
        <h2 className="text-lg font-medium">Log</h2>
        <div className="text-xs grid gap-1">
          {log.map((l, i) => (
            <div key={i} className="text-gray-600">
              {l}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
