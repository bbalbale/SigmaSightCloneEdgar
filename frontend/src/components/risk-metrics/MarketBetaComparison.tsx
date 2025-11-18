import { useMarketBetas } from '@/hooks/useMarketBetas';

export function MarketBetaComparison() {
  const { data, loading, error, metadata } = useMarketBetas();

  if (loading) {
    return (
      <div className="rounded-lg border p-8 transition-colors duration-300 themed-card">
        <h2 className="text-2xl font-bold mb-4 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
          Long Term vs. Short Term Beta
        </h2>
        <div className="flex items-center justify-center py-12">
          <div className="text-center text-secondary">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-current mx-auto mb-4"></div>
            <p>Loading beta comparison data...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border p-8 transition-colors duration-300 themed-card">
        <h2 className="text-2xl font-bold mb-4 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
          Long Term vs. Short Term Beta
        </h2>
        <div className="rounded-lg border p-6 text-center bg-red-900/20 border-red-800 text-red-300">
          <p>Error loading beta comparison: {error}</p>
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="rounded-lg border p-8 transition-colors duration-300 themed-card">
        <h2 className="text-2xl font-bold mb-4 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
          Long Term vs. Short Term Beta
        </h2>
        <div className="rounded-lg border p-6 text-center transition-colors duration-300" style={{
          backgroundColor: 'var(--bg-secondary)',
          borderColor: 'var(--border-primary)',
          color: 'var(--text-primary)'
        }}>
          <p>No beta data available</p>
        </div>
      </div>
    );
  }

  const formatBeta = (value: number | null) => {
    if (value === null) return '-';
    return value.toFixed(4);
  };

  const formatDifference = (diff: number | null) => {
    if (diff === null) return '-';
    const formatted = Math.abs(diff).toFixed(4);
    const color = diff > 0 ? 'text-green-600' : diff < 0 ? 'text-red-600' : 'text-secondary';
    const sign = diff > 0 ? '+' : '';
    return <span className={color}>{sign}{diff.toFixed(4)}</span>;
  };

  const formatRSquared = (value: number | null) => {
    if (value === null) return '-';
    return `${(value * 100).toFixed(2)}%`;
  };

  return (
    <div className="rounded-lg border p-8 transition-colors duration-300 themed-card">
      <h2 className="text-2xl font-bold mb-4 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
        Long Term vs. Short Term Beta
      </h2>
      <p className="text-sm mb-6 transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>
        Comparing market betas from data providers with our calculated betas
      </p>

      {metadata && (
        <div className="text-sm mb-6 transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>
          {metadata.total_positions && (
            <span className="mr-4">Total: {metadata.total_positions}</span>
          )}
          {metadata.positions_with_market_beta !== undefined && (
            <span className="mr-4">Market Beta: {metadata.positions_with_market_beta}</span>
          )}
          {metadata.positions_with_calculated_beta !== undefined && (
            <span>Calculated Beta: {metadata.positions_with_calculated_beta}</span>
          )}
        </div>
      )}

      <div className="relative overflow-x-auto">
        <table className="w-full text-sm text-left">
          <caption className="p-5 text-sm transition-colors duration-300" style={{
            color: 'var(--text-secondary)',
            backgroundColor: 'var(--bg-primary)'
          }}>
            Beta values measure systematic risk relative to the market (SPY).
            Differences highlight discrepancies between provider data and our calculations.
          </caption>
          <thead className="text-xs uppercase transition-colors duration-300" style={{
            backgroundColor: 'var(--bg-secondary)',
            color: 'var(--text-primary)'
          }}>
            <tr>
              <th scope="col" className="px-6 py-3 w-[100px]">Symbol</th>
              <th scope="col" className="px-6 py-3 text-right">1 Year Beta</th>
              <th scope="col" className="px-6 py-3 text-right">90 Day Beta</th>
              <th scope="col" className="px-6 py-3 text-right">Difference</th>
              <th scope="col" className="px-6 py-3 text-right">R²</th>
              <th scope="col" className="px-6 py-3 text-right">Observations</th>
            </tr>
          </thead>
          <tbody>
            {data.map((position) => (
              <tr
                key={position.position_id}
                className="border-b transition-colors duration-300"
                style={{
                  backgroundColor: 'var(--bg-primary)',
                  borderColor: 'var(--border-primary)'
                }}
              >
                <td className="px-6 py-4 font-medium whitespace-nowrap transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
                  {position.symbol}
                </td>
                <td className="px-6 py-4 text-right transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
                  {formatBeta(position.market_beta)}
                </td>
                <td className="px-6 py-4 text-right transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
                  {formatBeta(position.calculated_beta)}
                </td>
                <td className="px-6 py-4 text-right">
                  {formatDifference(position.beta_difference)}
                </td>
                <td className="px-6 py-4 text-right transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
                  {formatRSquared(position.beta_r_squared)}
                </td>
                <td className="px-6 py-4 text-right transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
                  {position.observations || '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
