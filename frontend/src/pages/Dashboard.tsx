import { useTickerStore } from '../lib/stores/tickerStore';
import { useLatestSignals, usePriceData, useFlowStatistics } from '../lib/api/queries';
import { formatCurrency, formatNumber } from '../lib/utils/formatters';
import { SIGNAL_TYPES } from '../lib/utils/constants';
import { Link } from 'react-router-dom';

export default function Dashboard() {
  const { selectedTicker } = useTickerStore();
  const { data: signals, isLoading: signalsLoading } = useLatestSignals();
  const { data: prices } = usePriceData(selectedTicker, 30);
  const { data: flowStats } = useFlowStatistics(selectedTicker, '4w');

  const currentSignal = signals?.find(s => s.ticker === selectedTicker);
  const currentPrice = prices?.[0];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Dashboard</h2>
        <p className="text-gray-600 mt-1">Overview of {selectedTicker} ETF</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">Current Price</h3>
          <p className="text-2xl font-bold text-gray-900 mt-2">
            {currentPrice ? formatCurrency(currentPrice.close) : '—'}
          </p>
          {currentPrice && prices && prices.length > 1 && (
            <p className={`text-sm mt-1 ${
              currentPrice.close > prices[1].close ? 'text-green-600' : 'text-red-600'
            }`}>
              {((currentPrice.close - prices[1].close) / prices[1].close * 100).toFixed(2)}%
            </p>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">4-Week Flow Z-Score</h3>
          <p className="text-2xl font-bold text-gray-900 mt-2">
            {flowStats?.z_score !== null && flowStats?.z_score !== undefined
              ? formatNumber(flowStats.z_score, 2)
              : '—'}
          </p>
          {flowStats?.z_score !== null && flowStats?.z_score !== undefined && (
            <p className={`text-sm mt-1 ${
              Math.abs(flowStats.z_score) > 2 ? 'text-red-600' :
              Math.abs(flowStats.z_score) > 1 ? 'text-yellow-600' : 'text-green-600'
            }`}>
              {Math.abs(flowStats.z_score) > 2 ? 'Extreme' :
               Math.abs(flowStats.z_score) > 1 ? 'Elevated' : 'Normal'}
            </p>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">Active Signals</h3>
          <p className="text-2xl font-bold text-gray-900 mt-2">
            {signals?.length || 0}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            {signals?.filter(s => s.direction === 'BUY').length || 0} Buy, {' '}
            {signals?.filter(s => s.direction === 'SELL').length || 0} Sell
          </p>
        </div>
      </div>

      {/* Latest Signal */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Latest Signal for {selectedTicker}
        </h3>
        {signalsLoading ? (
          <p className="text-gray-500">Loading...</p>
        ) : currentSignal ? (
          <div
            className="border-l-4 p-4 rounded"
            style={{
              borderColor: currentSignal.direction === 'BUY' ? '#22c55e' : '#ef4444',
              backgroundColor: currentSignal.direction === 'BUY' ? '#f0fdf4' : '#fef2f2'
            }}
          >
            <div className="flex justify-between items-start">
              <div>
                <h4 className="font-bold text-lg">
                  {SIGNAL_TYPES[currentSignal.signal_type as keyof typeof SIGNAL_TYPES]}
                </h4>
                <p className="text-gray-600 mt-1">{currentSignal.notes}</p>
              </div>
              <span
                className={`px-3 py-1 rounded-full text-sm font-semibold ${
                  currentSignal.direction === 'BUY'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'
                }`}
              >
                {currentSignal.direction}
              </span>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Strength:</span>
                <span className="ml-2 font-semibold">
                  {(currentSignal.strength * 100).toFixed(0)}%
                </span>
              </div>
              <div>
                <span className="text-gray-500">Generated:</span>
                <span className="ml-2 font-semibold">
                  {new Date(currentSignal.generated_at).toLocaleDateString()}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Status:</span>
                <span className="ml-2 font-semibold">{currentSignal.status}</span>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-gray-500">No active signals for {selectedTicker}</p>
        )}
        <Link
          to="/signals"
          className="inline-block mt-4 text-blue-600 hover:text-blue-800 font-medium"
        >
          View all signals →
        </Link>
      </div>

      {/* Quick Navigation */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Link
          to="/prices"
          className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
        >
          <h3 className="font-semibold text-gray-900">Price Tracking</h3>
          <p className="text-sm text-gray-600 mt-1">
            View historical price charts
          </p>
        </Link>
        <Link
          to="/flows"
          className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
        >
          <h3 className="font-semibold text-gray-900">Flow Analysis</h3>
          <p className="text-sm text-gray-600 mt-1">
            Weekly flows with z-scores
          </p>
        </Link>
        <Link
          to="/signals"
          className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
        >
          <h3 className="font-semibold text-gray-900">Trading Signals</h3>
          <p className="text-sm text-gray-600 mt-1">
            7 signal types for trading
          </p>
        </Link>
        <Link
          to="/attribution"
          className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
        >
          <h3 className="font-semibold text-gray-900">Investor Attribution</h3>
          <p className="text-sm text-gray-600 mt-1">
            Retail vs institutional flows
          </p>
        </Link>
      </div>
    </div>
  );
}
