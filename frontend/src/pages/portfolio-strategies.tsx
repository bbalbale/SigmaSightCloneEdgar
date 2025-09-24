import React, { useEffect, useState } from 'react';
import StrategyList from '@/components/portfolio/StrategyList';
import { portfolioResolver } from '@/services/portfolioResolver';

export default function PortfolioStrategiesPage() {
  const [portfolioId, setPortfolioId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const url = new URL(window.location.href);
        const pid = url.searchParams.get('portfolio_id');
        if (pid) {
          setPortfolioId(pid);
          return;
        }
        const resolved = await portfolioResolver.getUserPortfolioId();
        if (!resolved) {
          setError('No portfolio found or not authenticated. Please log in.');
        } else {
          setPortfolioId(resolved);
        }
      } catch (e: any) {
        setError(e?.message || 'Failed to resolve portfolio');
      }
    })();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-4">Portfolio Strategies</h1>
        {error && <div className="text-red-600 mb-2">{error}</div>}
        {portfolioId ? (
          <>
            <div className="mb-4 text-sm text-gray-600">Portfolio ID: {portfolioId}</div>
            <StrategyList portfolioId={portfolioId} />
          </>
        ) : (
          <div>Resolving portfolio...</div>
        )}
      </div>
    </div>
  );
}
