import { useTickerStore } from '../lib/stores/tickerStore';
import { useInvestorSegments, useInstitutionalHoldings } from '../lib/api/queries';
import { formatNumber, formatCurrency } from '../lib/utils/formatters';
import { INVESTOR_SEGMENTS, SEGMENT_COLORS } from '../lib/utils/constants';

export default function InvestorAttribution() {
  const { selectedTicker } = useTickerStore();
  const { data: segments, isLoading: segmentsLoading } = useInvestorSegments(selectedTicker);
  const { data: institutionalHoldings, isLoading: institutionalLoading } = useInstitutionalHoldings(selectedTicker, 20);

  const hasSegmentData = segments && Object.keys(segments).length > 0;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Investor Attribution</h2>
        <p className="text-gray-600 mt-1">{selectedTicker} - Retail vs Institutional Flow Analysis</p>
      </div>

      {/* Segment Overview */}
      {segmentsLoading ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <p className="text-gray-500">Loading segment data...</p>
        </div>
      ) : hasSegmentData ? (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Flow by Investor Segment</h3>
          <div className="space-y-4">
            {Object.entries(segments).map(([segment, flows]: [string, any]) => {
              const segmentName = INVESTOR_SEGMENTS[segment as keyof typeof INVESTOR_SEGMENTS] || segment;
              const segmentColor = SEGMENT_COLORS[segment as keyof typeof SEGMENT_COLORS] || '#6b7280';
              const recentFlows = flows.slice(0, 4);
              const totalFlow = recentFlows.reduce((sum: number, f: any) => sum + (f.estimated_flow || 0), 0);

              return (
                <div key={segment} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div
                        className="w-4 h-4 rounded"
                        style={{ backgroundColor: segmentColor }}
                      />
                      <h4 className="font-semibold text-gray-900">{segmentName}</h4>
                    </div>
                    <span className={`text-lg font-bold ${totalFlow > 0 ? 'text-green-600' : 'text-red-600'}`}>
                      ${formatNumber(totalFlow, 1)}M (4w)
                    </span>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                    {recentFlows.map((flow: any, idx: number) => (
                      <div key={idx} className="bg-gray-50 rounded p-2">
                        <div className="text-gray-500 text-xs">
                          {new Date(flow.week_ending).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        </div>
                        <div className={`font-semibold ${flow.estimated_flow > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          ${formatNumber(flow.estimated_flow, 1)}M
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <p className="text-gray-500">
            No investor segment data available for {selectedTicker}
          </p>
          <p className="text-sm text-gray-400 mt-2">
            Segment attribution data is populated through flow collection
          </p>
        </div>
      )}

      {/* Institutional Holdings */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            Top 20 Institutional Holdings (13F Filings)
          </h3>
        </div>
        {institutionalLoading ? (
          <div className="p-8 text-center">
            <p className="text-gray-500">Loading institutional holdings...</p>
          </div>
        ) : institutionalHoldings && institutionalHoldings.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Institution</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Shares</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Value (USD)</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">% of Portfolio</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Change</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Filing Date</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {institutionalHoldings.map((holding, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                      {holding.institution_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatNumber(holding.shares, 0)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatCurrency(holding.value_usd)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {holding.percent_of_portfolio !== null
                        ? `${(holding.percent_of_portfolio * 100).toFixed(2)}%`
                        : '—'}
                    </td>
                    <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${
                      holding.change_shares !== null && holding.change_shares > 0
                        ? 'text-green-600'
                        : holding.change_shares !== null && holding.change_shares < 0
                        ? 'text-red-600'
                        : 'text-gray-900'
                    }`}>
                      {holding.change_shares !== null
                        ? `${holding.change_shares > 0 ? '+' : ''}${formatNumber(holding.change_shares, 0)}`
                        : '—'}
                      {holding.change_percent !== null && (
                        <span className="ml-1 text-xs">
                          ({holding.change_percent > 0 ? '+' : ''}{holding.change_percent.toFixed(1)}%)
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {new Date(holding.filing_date).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center">
            <p className="text-gray-500">
              No institutional holdings data available for {selectedTicker}
            </p>
            <p className="text-sm text-gray-400 mt-2">
              Use the data collection API to gather 13F filings
            </p>
          </div>
        )}
      </div>

      {/* Smart Money vs Retail Indicator */}
      {hasSegmentData && segments.INSTITUTIONAL && segments.KOREAN_RETAIL && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Smart Money vs Retail Indicator
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="border rounded-lg p-4">
              <h4 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                <div className="w-4 h-4 rounded" style={{ backgroundColor: SEGMENT_COLORS.INSTITUTIONAL }} />
                Institutional (Smart Money)
              </h4>
              <p className="text-2xl font-bold text-gray-900">
                $
                {formatNumber(
                  segments.INSTITUTIONAL.slice(0, 4).reduce((sum: number, f: any) => sum + (f.estimated_flow || 0), 0),
                  1
                )}
                M
              </p>
              <p className="text-sm text-gray-500 mt-1">4-week total</p>
            </div>
            <div className="border rounded-lg p-4">
              <h4 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                <div className="w-4 h-4 rounded" style={{ backgroundColor: SEGMENT_COLORS.KOREAN_RETAIL }} />
                Korean Retail
              </h4>
              <p className="text-2xl font-bold text-gray-900">
                $
                {formatNumber(
                  segments.KOREAN_RETAIL.slice(0, 4).reduce((sum: number, f: any) => sum + (f.estimated_flow || 0), 0),
                  1
                )}
                M
              </p>
              <p className="text-sm text-gray-500 mt-1">4-week total</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
