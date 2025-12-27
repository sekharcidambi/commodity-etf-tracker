import { useTickerStore } from '../../lib/stores/tickerStore';
import { TICKERS } from '../../lib/utils/constants';

export default function TickerSelector() {
  const { selectedTicker, setTicker } = useTickerStore();

  return (
    <div className="flex gap-2">
      {TICKERS.map((ticker) => (
        <button
          key={ticker}
          onClick={() => setTicker(ticker)}
          className={`px-4 py-2 rounded-lg font-semibold transition-colors ${
            selectedTicker === ticker
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          {ticker}
        </button>
      ))}
    </div>
  );
}
