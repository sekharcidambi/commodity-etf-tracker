import { useTickerStore } from '../lib/stores/tickerStore';
import { useFlowData, useFlowStatistics } from '../lib/api/queries';
import { formatNumber } from '../lib/utils/formatters';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from 'recharts';

export default function FlowAnalysis() {
  const { selectedTicker } = useTickerStore();
  const { data: flows, isLoading: flowsLoading } = useFlowData(selectedTicker, 52);
  const { data: stats4w } = useFlowStatistics(selectedTicker, '4w');
  const { data: stats13w } = useFlowStatistics(selectedTicker, '13w');
  const { data: stats26w } = useFlowStatistics(selectedTicker, '26w');
  const { data: stats52w } = useFlowStatistics(selectedTicker, '52w');

  if (flowsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading flow data...</p>
      </div>
    );
  }

  if (!flows || flows.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">No flow data available for {selectedTicker}</p>
      </div>
    );
  }

  // Reverse for chronological order
  const chartData = [...flows].reverse().map(f => ({
    week: new Date(f.week_ending).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    netFlow: f.net_flow,
  }));

  const getZScoreColor = (zScore: number | null | undefined) => {
    if (zScore === null || zScore === undefined) return 'text-gray-500';
    const abs = Math.abs(zScore);
    if (abs > 2) return 'text-red-600';
    if (abs > 1) return 'text-yellow-600';
    return 'text-green-600';
  };

  const getZScoreLabel = (zScore: number | null | undefined) => {
    if (zScore === null || zScore === undefined) return 'N/A';
    const abs = Math.abs(zScore);
    if (abs > 2) return 'Extreme';
    if (abs > 1) return 'Elevated';
    return 'Normal';
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Flow Analysis</h2>
        <p className="text-gray-600 mt-1">{selectedTicker} - Weekly ETF Flows with Z-Score Analysis</p>
      </div>

      {/* Z-Score Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: '4-Week', stats: stats4w },
          { label: '13-Week', stats: stats13w },
          { label: '26-Week', stats: stats26w },
          { label: '52-Week', stats: stats52w },
        ].map(({ label, stats }) => (
          <div key={label} className="bg-white rounded-lg shadow p-4">
            <h3 className="text-sm font-medium text-gray-500">{label} Z-Score</h3>
            <p className={`text-2xl font-bold mt-2 ${getZScoreColor(stats?.z_score)}`}>
              {stats?.z_score !== null && stats?.z_score !== undefined
                ? formatNumber(stats.z_score, 2)
                : '—'}
            </p>
            <p className={`text-sm mt-1 ${getZScoreColor(stats?.z_score)}`}>
              {getZScoreLabel(stats?.z_score)}
            </p>
            {stats?.rolling_sum !== null && stats?.rolling_sum !== undefined && (
              <p className="text-xs text-gray-500 mt-2">
                Rolling Sum: ${formatNumber(stats.rolling_sum, 1)}M
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Flow Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Weekly Net Flows (52 Weeks)</h3>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="week"
              tick={{ fontSize: 12 }}
              interval={Math.floor(chartData.length / 10)}
            />
            <YAxis
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => `$${value}M`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #e5e7eb',
                borderRadius: '0.5rem',
              }}
              formatter={(value: any) => [`$${formatNumber(value, 1)}M`, 'Net Flow']}
            />
            <ReferenceLine y={0} stroke="#000" strokeWidth={1} />
            <Bar
              dataKey="netFlow"
              fill="#3b82f6"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Flow Statistics Details */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Flow Statistics Details</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[
            { label: '4-Week Window', stats: stats4w },
            { label: '13-Week Window', stats: stats13w },
            { label: '26-Week Window', stats: stats26w },
            { label: '52-Week Window', stats: stats52w },
          ].map(({ label, stats }) => (
            <div key={label} className="border rounded-lg p-4">
              <h4 className="font-semibold text-gray-900 mb-3">{label}</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Current Flow:</span>
                  <span className="font-medium">
                    {stats?.current_flow !== null && stats?.current_flow !== undefined
                      ? `$${formatNumber(stats.current_flow, 1)}M`
                      : '—'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Rolling Sum:</span>
                  <span className="font-medium">
                    {stats?.rolling_sum !== null && stats?.rolling_sum !== undefined
                      ? `$${formatNumber(stats.rolling_sum, 1)}M`
                      : '—'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Z-Score:</span>
                  <span className={`font-medium ${getZScoreColor(stats?.z_score)}`}>
                    {stats?.z_score !== null && stats?.z_score !== undefined
                      ? formatNumber(stats.z_score, 2)
                      : '—'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Percentile:</span>
                  <span className="font-medium">
                    {stats?.percentile !== null && stats?.percentile !== undefined
                      ? `${formatNumber(stats.percentile, 1)}%`
                      : '—'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Mean:</span>
                  <span className="font-medium">
                    {stats?.mean !== null && stats?.mean !== undefined
                      ? `$${formatNumber(stats.mean, 1)}M`
                      : '—'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Std Dev:</span>
                  <span className="font-medium">
                    {stats?.std_dev !== null && stats?.std_dev !== undefined
                      ? `$${formatNumber(stats.std_dev, 1)}M`
                      : '—'}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Flows Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Recent Weekly Flows</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Week Ending</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Net Flow</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">AUM</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Shares Outstanding</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {flows.slice(0, 20).map((flow, idx) => (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {new Date(flow.week_ending).toLocaleDateString()}
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${
                    flow.net_flow > 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    ${formatNumber(flow.net_flow, 1)}M
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    ${formatNumber(flow.aum, 1)}M
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatNumber(flow.shares_outstanding, 0)}
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
