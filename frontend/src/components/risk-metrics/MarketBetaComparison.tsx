import { useMarketBetas } from '@/hooks/useMarketBetas';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export function MarketBetaComparison() {
  const { data, loading, error, metadata } = useMarketBetas();

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Market Beta Comparison</CardTitle>
          <CardDescription>
            Comparing market betas from data providers with our calculated betas
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <p className="text-muted-foreground">Loading beta comparison data...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Market Beta Comparison</CardTitle>
          <CardDescription>
            Comparing market betas from data providers with our calculated betas
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <p className="text-red-500">{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Market Beta Comparison</CardTitle>
          <CardDescription>
            Comparing market betas from data providers with our calculated betas
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <p className="text-muted-foreground">No beta data available</p>
          </div>
        </CardContent>
      </Card>
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
    <Card>
      <CardHeader>
        <CardTitle>Market Beta Comparison</CardTitle>
        <CardDescription>
          Comparing market betas from data providers with our calculated betas
        </CardDescription>
        {metadata && (
          <div className="text-sm text-muted-foreground mt-2">
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
      </CardHeader>
      <CardContent>
        <div className="relative overflow-x-auto">
          <table className="w-full text-sm text-left">
            <caption className="p-5 text-sm text-tertiary bg-white dark:bg-gray-800">
              Beta values measure systematic risk relative to the market (SPY).
              Differences highlight discrepancies between provider data and our calculations.
            </caption>
            <thead className="text-xs uppercase bg-primary dark:bg-gray-700">
              <tr>
                <th scope="col" className="px-6 py-3 w-[100px]">Symbol</th>
                <th scope="col" className="px-6 py-3 text-right">Market Beta</th>
                <th scope="col" className="px-6 py-3 text-right">Calculated Beta</th>
                <th scope="col" className="px-6 py-3 text-right">Difference</th>
                <th scope="col" className="px-6 py-3 text-right">R²</th>
                <th scope="col" className="px-6 py-3 text-right">Observations</th>
              </tr>
            </thead>
            <tbody>
              {data.map((position) => (
                <tr key={position.position_id} className="bg-white border-b dark:bg-gray-800 dark:border-gray-700">
                  <td className="px-6 py-4 font-medium whitespace-nowrap">{position.symbol}</td>
                  <td className="px-6 py-4 text-right">{formatBeta(position.market_beta)}</td>
                  <td className="px-6 py-4 text-right">{formatBeta(position.calculated_beta)}</td>
                  <td className="px-6 py-4 text-right">{formatDifference(position.beta_difference)}</td>
                  <td className="px-6 py-4 text-right">{formatRSquared(position.beta_r_squared)}</td>
                  <td className="px-6 py-4 text-right">{position.observations || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
