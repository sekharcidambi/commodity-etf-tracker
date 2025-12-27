import { useState } from 'react';
import { useTickerStore } from '../lib/stores/tickerStore';
import { useSignals, useSignalPerformance } from '../lib/api/queries';
import { SIGNAL_TYPES } from '../lib/utils/constants';
import { formatDate } from '../lib/utils/formatters';
import type { Signal } from '../lib/api/types';

function SignalCard({ signal }: { signal: Signal }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="border-l-4 p-4 rounded bg-white shadow-sm hover:shadow-md transition-shadow"
      style={{
        borderColor: signal.direction === 'BUY' ? '#22c55e' : signal.direction === 'SELL' ? '#ef4444' : '#6b7280',
      }}
    >
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <h4 className="font-bold text-lg text-gray-900">
            {SIGNAL_TYPES[signal.signal_type as keyof typeof SIGNAL_TYPES]}
          </h4>
          <p className="text-sm text-gray-600 mt-1">{signal.ticker}</p>
          {signal.notes && (
            <p className="text-sm text-gray-700 mt-2">{signal.notes}</p>
          )}
        </div>
        <span
          className={`px-3 py-1 rounded-full text-sm font-semibold ${
            signal.direction === 'BUY'
              ? 'bg-green-100 text-green-800'
              : signal.direction === 'SELL'
              ? 'bg-red-100 text-red-800'
              : 'bg-gray-100 text-gray-800'
          }`}
        >
          {signal.direction}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
        <div>
          <span className="text-gray-500">Strength:</span>
          <span className="ml-2 font-semibold">{(signal.strength * 100).toFixed(0)}%</span>
        </div>
        <div>
          <span className="text-gray-500">Generated:</span>
          <span className="ml-2 font-semibold">{formatDate(signal.generated_at)}</span>
        </div>
        <div>
          <span className="text-gray-500">Status:</span>
          <span className="ml-2 font-semibold">{signal.status}</span>
        </div>
      </div>

      {signal.expires_at && (
        <div className="mt-2 text-sm">
          <span className="text-gray-500">Expires:</span>
          <span className="ml-2 font-semibold">{formatDate(signal.expires_at)}</span>
        </div>
      )}

      {signal.trigger_values && Object.keys(signal.trigger_values).length > 0 && (
        <div className="mt-4">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-blue-600 hover:text-blue-800 text-sm font-medium"
          >
            {expanded ? 'Hide' : 'Show'} trigger details
          </button>
          {expanded && (
            <div className="mt-2 bg-gray-50 rounded p-3 text-sm">
              <pre className="text-xs text-gray-700 overflow-x-auto">
                {JSON.stringify(signal.trigger_values, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function TradingSignals() {
  const { selectedTicker } = useTickerStore();
  const [statusFilter, setStatusFilter] = useState<'ACTIVE' | 'EXPIRED' | 'CLOSED'>('ACTIVE');
  const { data: signals, isLoading } = useSignals(selectedTicker, undefined, statusFilter);
  const { data: performance } = useSignalPerformance(selectedTicker);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading signals...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Trading Signals</h2>
        <p className="text-gray-600 mt-1">{selectedTicker} - 7 Signal Types for Buy/Sell Decisions</p>
      </div>

      {/* Performance Metrics */}
      {performance && performance.total_signals > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-sm font-medium text-gray-500">Total Signals</h3>
            <p className="text-2xl font-bold text-gray-900 mt-1">{performance.total_signals}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-sm font-medium text-gray-500">Win Rate</h3>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {performance.win_rate !== null ? `${(performance.win_rate * 100).toFixed(1)}%` : '—'}
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-sm font-medium text-gray-500">Avg Hold Time</h3>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {performance.avg_hold_time_days !== null ? `${performance.avg_hold_time_days.toFixed(1)} days` : '—'}
            </p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-gray-700">Status:</span>
          <div className="flex gap-2">
            {(['ACTIVE', 'EXPIRED', 'CLOSED'] as const).map((status) => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  statusFilter === status
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {status}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Signals Grid */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          {statusFilter} Signals for {selectedTicker}
        </h3>
        {signals && signals.length > 0 ? (
          <div className="space-y-4">
            {signals.map((signal) => (
              <SignalCard key={signal.id} signal={signal} />
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <p className="text-gray-500">No {statusFilter.toLowerCase()} signals found for {selectedTicker}</p>
          </div>
        )}
      </div>

      {/* Signal Types Reference */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Signal Types</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.entries(SIGNAL_TYPES).map(([key, name]) => (
            <div key={key} className="border rounded-lg p-4">
              <h4 className="font-semibold text-gray-900">{name}</h4>
              <p className="text-sm text-gray-600 mt-1">
                {key === 'EXTREME_FLOW' && 'Flow z-score exceeds ±2.0 (extreme inflows/outflows)'}
                {key === 'FLOW_PRICE_DIVERGENCE' && 'Flow and price move in opposite directions'}
                {key === 'FUTURES_SPOT_BASIS' && 'Abnormal futures/spot price basis'}
                {key === 'MOMENTUM_ALIGNMENT' && 'Flow and price momentum aligned'}
                {key === 'SMART_MONEY_DIVERGENCE' && 'Institutional flows diverge from retail'}
                {key === 'KOREAN_RETAIL_EUPHORIA' && 'Extreme Korean retail activity (contrarian)'}
                {key === 'INSTITUTIONAL_ACCUMULATION' && '2+ quarters of 13F institutional buying'}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
