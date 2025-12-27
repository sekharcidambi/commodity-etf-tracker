import { useTickerStore } from '../lib/stores/tickerStore';
import { usePriceData } from '../lib/api/queries';
import { formatCurrency, formatNumber } from '../lib/utils/formatters';
import { ComposedChart, Line, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts';

export default function PriceTracking() {
  const { selectedTicker } = useTickerStore();
  const { data: prices, isLoading } = usePriceData(selectedTicker, 365);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading price data...</p>
      </div>
    );
  }

  if (!prices || prices.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">No price data available for {selectedTicker}</p>
      </div>
    );
  }

  // Reverse to show chronological order
  const chartData = [...prices].reverse().map(p => ({
    date: new Date(p.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    price: p.close,
    volume: p.volume,
  }));

  const currentPrice = prices[0];
  const high52w = Math.max(...prices.map(p => p.high));
  const low52w = Math.min(...prices.map(p => p.low));
  const avgVolume = prices.reduce((sum, p) => sum + p.volume, 0) / prices.length;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Price Tracking</h2>
        <p className="text-gray-600 mt-1">{selectedTicker} - Historical Price Data</p>
      </div>

      {/* Price Statistics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-500">Current Price</h3>
          <p className="text-xl font-bold text-gray-900 mt-1">
            {formatCurrency(currentPrice.close)}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-500">52-Week High</h3>
          <p className="text-xl font-bold text-gray-900 mt-1">
            {formatCurrency(high52w)}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-500">52-Week Low</h3>
          <p className="text-xl font-bold text-gray-900 mt-1">
            {formatCurrency(low52w)}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-500">Avg Volume</h3>
          <p className="text-xl font-bold text-gray-900 mt-1">
            {formatNumber(avgVolume, 0)}
          </p>
        </div>
      </div>

      {/* Price Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Price History (1 Year)</h3>
        <ResponsiveContainer width="100%" height={500}>
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12 }}
              interval={Math.floor(chartData.length / 10)}
            />
            <YAxis
              yAxisId="price"
              tick={{ fontSize: 12 }}
              domain={['auto', 'auto']}
              tickFormatter={(value) => `$${value.toFixed(2)}`}
            />
            <YAxis
              yAxisId="volume"
              orientation="right"
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => formatNumber(value, 0)}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #e5e7eb',
                borderRadius: '0.5rem',
              }}
              formatter={(value: any, name: string) => {
                if (name === 'Price') return [formatCurrency(value), 'Price'];
                if (name === 'Volume') return [formatNumber(value, 0), 'Volume'];
                return [value, name];
              }}
            />
            <Legend />
            <Bar
              yAxisId="volume"
              dataKey="volume"
              fill="#93c5fd"
              opacity={0.6}
              name="Volume"
            />
            <Line
              yAxisId="price"
              type="monotone"
              dataKey="price"
              stroke="#2563eb"
              strokeWidth={2}
              dot={false}
              name="Price"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Recent Prices Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Recent Prices</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Open</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">High</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Low</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Close</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Volume</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {prices.slice(0, 20).map((price, idx) => (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {new Date(price.timestamp).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatCurrency(price.open)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatCurrency(price.high)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatCurrency(price.low)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {formatCurrency(price.close)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatNumber(price.volume, 0)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
