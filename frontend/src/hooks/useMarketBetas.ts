import { useState, useEffect } from 'react';
import { usePortfolioStore } from '@/stores/portfolioStore';
import { apiClient } from '@/services/apiClient';

interface PositionBetaComparison {
  symbol: string;
  position_id: string;
  market_beta: number | null;
  calculated_beta: number | null;
  beta_r_squared: number | null;
  calculation_date: string | null;
  observations: number | null;
  beta_difference: number | null;
}

interface MarketBetaResponse {
  available: boolean;
  portfolio_id: string;
  positions?: PositionBetaComparison[];
  metadata?: {
    total_positions?: number;
    positions_with_market_beta?: number;
    positions_with_calculated_beta?: number;
    error?: string;
  };
}

export function useMarketBetas() {
  const { portfolioId } = usePortfolioStore();
  const [data, setData] = useState<PositionBetaComparison[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<MarketBetaResponse['metadata']>(undefined);

  useEffect(() => {
    const fetchBetaComparison = async () => {
      if (!portfolioId) {
        setError('No portfolio selected');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        const response = await apiClient.get<MarketBetaResponse>(
          `/api/v1/analytics/portfolio/${portfolioId}/beta-comparison`
        );

        if (!response.available) {
          setError(response.metadata?.error || 'Beta comparison data not available');
          setData(null);
          setMetadata(response.metadata);
        } else {
          setData(response.positions || []);
          setMetadata(response.metadata);
        }
      } catch (err) {
        console.error('Failed to fetch beta comparison:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch beta comparison data');
        setData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchBetaComparison();
  }, [portfolioId]);

  return { data, loading, error, metadata };
}
