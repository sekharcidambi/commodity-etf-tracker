import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [health, setHealth] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => {
        setHealth(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to fetch health:', err)
        setLoading(false)
      })
  }, [])

  return (
    <div className="App">
      <header className="App-header">
        <h1>🚀 Commodity ETF Tracker</h1>
        <p>Real-time commodity ETF flow tracking and signal generation</p>

        {loading ? (
          <p>Connecting to API...</p>
        ) : health ? (
          <div className="status-card">
            <h2>✅ System Status</h2>
            <p><strong>Status:</strong> {health.status}</p>
            <p><strong>Service:</strong> {health.service}</p>
            <p><strong>Version:</strong> {health.version}</p>
          </div>
        ) : (
          <div className="status-card error">
            <h2>❌ API Offline</h2>
            <p>Unable to connect to backend API</p>
            <p>Make sure Docker services are running</p>
          </div>
        )}

        <div className="quick-links">
          <h3>Quick Links</h3>
          <ul>
            <li><a href="/api/docs" target="_blank">📚 API Documentation</a></li>
            <li><a href="/api/v1/tickers/" target="_blank">📊 Tickers List</a></li>
            <li><a href="https://github.com/yourusername/commodity-etf-tracker" target="_blank">💻 GitHub Repo</a></li>
          </ul>
        </div>

        <div className="features">
          <h3>Features Coming Soon</h3>
          <div className="feature-grid">
            <div className="feature-card">
              <h4>📈 Price Tracking</h4>
              <p>Real-time prices for AGQ, UGL, and precious metals</p>
            </div>
            <div className="feature-card">
              <h4>💰 Flow Analysis</h4>
              <p>Weekly ETF flows with z-score calculations</p>
            </div>
            <div className="feature-card">
              <h4>🎯 Trading Signals</h4>
              <p>7 signal types for buy/sell decisions</p>
            </div>
            <div className="feature-card">
              <h4>🇰🇷 Investor Attribution</h4>
              <p>Track Korean retail vs institutional flows</p>
            </div>
          </div>
        </div>
      </header>
    </div>
  )
}

export default App
