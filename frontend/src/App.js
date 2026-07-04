import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

function App() {
  const [signals, setSignals] = useState([]);
  const [connected, setConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState('');
  const [stats, setStats] = useState(null);
  const [equityCurve, setEquityCurve] = useState([]);

  useEffect(() => {
    console.log('Connecting to WebSocket...');
    
    let ws = null;
    let timeoutId = null;

    const connectWebSocket = () => {
      const socket = new WebSocket('ws://localhost:8080');
      
      socket.onopen = () => {
        console.log('✅ WebSocket connected!');
        setConnected(true);
      };
      
      socket.onmessage = (event) => {
        console.log('📨 Received message:', event.data);
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'signals') {
            console.log('📊 Got signals:', data.data);
            setSignals(data.data);
            setLastUpdate(data.timestamp);
          } else if (data.type === 'connected') {
            console.log('🔌 Connected to server:', data.message);
          }
        } catch (e) {
          console.error('Parse error:', e);
        }
      };
      
      socket.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
      };
      
      socket.onclose = () => {
        console.log('🔌 WebSocket disconnected');
        setConnected(false);
      };
      
      return socket;
    };

    timeoutId = setTimeout(() => {
      ws = connectWebSocket();
    }, 100);

    // Fetch real stats from backend
    const fetchStats = async () => {
      try {
        const response = await fetch('http://localhost:3001/api/stats');
        const data = await response.json();
        setStats(data);
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      }
    };

    // Fetch equity curve data
    const fetchEquityCurve = async () => {
      try {
        const response = await fetch('http://localhost:3001/api/equity-curve');
        const data = await response.json();
        setEquityCurve(data);
      } catch (error) {
        console.error('Failed to fetch equity curve:', error);
      }
    };

    fetchStats();
    fetchEquityCurve();
    const statsInterval = setInterval(fetchStats, 30000);
    const equityInterval = setInterval(fetchEquityCurve, 60000); // every 60 sec

    return () => {
      if (timeoutId) clearTimeout(timeoutId);
      if (ws) ws.close();
      clearInterval(statsInterval);
      clearInterval(equityInterval);
    };
  }, []);

  const getSignalStyle = (signal, strength) => {
    if (signal === 'BUY') return 'bg-green-500/20 border-green-500';
    if (signal === 'SELL') return 'bg-red-500/20 border-red-500';
    return 'bg-gray-800 border-gray-700';
  };

  const getSignalColor = (signal) => {
    if (signal === 'BUY') return 'text-green-400';
    if (signal === 'SELL') return 'text-red-400';
    return 'text-gray-400';
  };

  const getStrengthBadge = (strength) => {
    switch(strength) {
      case 'STRONG': return 'bg-green-600';
      case 'MEDIUM': return 'bg-yellow-600';
      default: return 'bg-gray-600';
    }
  };

  const formatCurrency = (value) => `$${value.toLocaleString()}`;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800">
      {/* Header */}
      <header className="bg-gray-900/50 backdrop-blur-sm border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-white flex items-center gap-2">
                <span>🤖</span> FOREX AI TRADING
              </h1>
              <p className="text-gray-400 text-sm mt-1">
                ICT + SMC + XGBoost Ensemble | Live Signals
              </p>
            </div>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
              <span className="text-gray-400 text-sm">
                {connected ? 'LIVE CONNECTED' : 'DISCONNECTED'}
              </span>
            </div>
          </div>
          {lastUpdate && (
            <p className="text-xs text-gray-500 mt-2">
              Last update: {new Date(lastUpdate).toLocaleTimeString()}
            </p>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Performance Statistics Dashboard */}
        {stats && (
          <div className="mb-8">
            <h2 className="text-white text-lg font-semibold mb-3">📊 Trading Performance</h2>
            
            {/* Basic Metrics Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-4 border border-gray-700">
                <div className="text-gray-400 text-sm">Win Rate</div>
                <div className="text-2xl font-bold text-green-400">{stats.win_rate?.toFixed(1) || 0}%</div>
                <div className="text-xs text-gray-500 mt-1">{stats.winning_trades}W / {stats.losing_trades}L</div>
              </div>
              <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-4 border border-gray-700">
                <div className="text-gray-400 text-sm">Total P&L</div>
                <div className={`text-2xl font-bold ${stats.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  ${stats.total_pnl?.toFixed(2) || '0.00'}
                </div>
                <div className="text-xs text-gray-500 mt-1">Today: ${stats.today_pnl?.toFixed(2) || '0.00'}</div>
              </div>
              <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-4 border border-gray-700">
                <div className="text-gray-400 text-sm">Profit Factor</div>
                <div className="text-2xl font-bold text-blue-400">
                  {stats.profit_factor === Infinity ? '∞' : stats.profit_factor?.toFixed(2) || '0.00'}
                </div>
                <div className="text-xs text-gray-500 mt-1">Gross Profit / Gross Loss</div>
              </div>
              <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-4 border border-gray-700">
                <div className="text-gray-400 text-sm">Max Drawdown</div>
                <div className="text-2xl font-bold text-red-400">{stats.max_drawdown?.toFixed(2) || '0.00'}%</div>
                <div className="text-xs text-gray-500 mt-1">From peak balance</div>
              </div>
            </div>

            {/* Advanced Metrics Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-4 border border-gray-700">
                <div className="text-gray-400 text-sm">Sharpe Ratio</div>
                <div className="text-2xl font-bold text-yellow-400">{stats.sharpe_ratio?.toFixed(2) || '0.00'}</div>
                <div className="text-xs text-gray-500 mt-1">Annualized (est.)</div>
              </div>
              <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-4 border border-gray-700">
                <div className="text-gray-400 text-sm">Rolling Win Rate</div>
                <div className="text-2xl font-bold text-green-400">{stats.rolling_win_rate?.toFixed(1) || 0}%</div>
                <div className="text-xs text-gray-500 mt-1">Last 20 trades</div>
              </div>
              <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-4 border border-gray-700">
                <div className="text-gray-400 text-sm">Active Signals</div>
                <div className="text-2xl font-bold text-white">{signals.length}</div>
                <div className="text-xs text-gray-500 mt-1">Open Positions: {stats.open_positions}</div>
              </div>
              <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-4 border border-gray-700">
                <div className="text-gray-400 text-sm">Best / Worst Trade</div>
                <div className="text-lg font-bold">
                  <span className="text-green-400">${stats.best_trade?.toFixed(2)}</span>
                  <span className="text-gray-500 mx-1">/</span>
                  <span className="text-red-400">${stats.worst_trade?.toFixed(2)}</span>
                </div>
                <div className="text-xs text-gray-500 mt-1">Single trade P&L extremes</div>
              </div>
            </div>

            {/* Equity Curve Chart */}
            {equityCurve.length > 0 && (
              <div className="mt-6 bg-gray-800/50 backdrop-blur-sm rounded-lg p-4 border border-gray-700">
                <h3 className="text-white text-base font-semibold mb-3">📈 Equity Curve (Cumulative Balance)</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={equityCurve} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
                    <defs>
                      <linearGradient id="colorBalance" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#00ff88" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="#00ff88" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                    <XAxis dataKey="date" stroke="#ccc" fontSize={12} />
                    <YAxis stroke="#ccc" fontSize={12} tickFormatter={formatCurrency} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#2d2d2d', border: '1px solid #555', borderRadius: '4px' }}
                      formatter={(value) => [`$${Number(value).toFixed(2)}`, 'Balance']}
                      labelStyle={{ color: '#ccc' }}
                    />
                    <Area type="monotone" dataKey="balance" stroke="#00ff88" fill="url(#colorBalance)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Signal Quality Breakdown */}
            <div className="mt-4 grid grid-cols-3 gap-4">
              <div className="bg-gray-800/30 rounded-lg p-3 text-center">
                <div className="text-xs text-gray-400">STRONG</div>
                <div className="text-lg font-bold text-green-400">{signals.filter(s => s.strength === 'STRONG').length}</div>
              </div>
              <div className="bg-gray-800/30 rounded-lg p-3 text-center">
                <div className="text-xs text-gray-400">MEDIUM</div>
                <div className="text-lg font-bold text-yellow-400">{signals.filter(s => s.strength === 'MEDIUM').length}</div>
              </div>
              <div className="bg-gray-800/30 rounded-lg p-3 text-center">
                <div className="text-xs text-gray-400">WEAK</div>
                <div className="text-lg font-bold text-gray-400">{signals.filter(s => s.strength === 'WEAK').length}</div>
              </div>
            </div>
          </div>
        )}

        {/* Signals Grid */}
        {signals.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">📡</div>
            <p className="text-gray-400 text-lg">Waiting for AI signals...</p>
            <p className="text-gray-500 text-sm mt-2">
              {connected ? 'Analyzing markets...' : 'Connecting to server...'}
            </p>
            {connected && (
              <p className="text-blue-400 text-xs mt-4">
                Connected to WebSocket. Signals arriving every 30 seconds.
              </p>
            )}
          </div>
        ) : (
          <>
            <div className="mb-4 flex justify-between items-center">
              <span className="text-green-400 text-sm">
                ✅ {signals.length} active signals
              </span>
            </div>
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {signals.map((signal, idx) => (
                <div key={idx} className={`rounded-xl border p-6 backdrop-blur-sm transition-all hover:scale-[1.02] ${getSignalStyle(signal.signal, signal.strength)}`}>
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-2xl font-bold text-white">{signal.pair}</h3>
                      <span className={`inline-block px-2 py-1 text-xs rounded-lg mt-2 text-white ${getStrengthBadge(signal.strength)}`}>
                        {signal.strength}
                      </span>
                    </div>
                    <div className={`text-3xl font-bold ${getSignalColor(signal.signal)}`}>
                      {signal.signal}
                    </div>
                  </div>

                  {/* Confidence Bar */}
                  <div className="mb-4">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-400">Confidence</span>
                      <span className="text-white">{(signal.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all ${signal.signal === 'BUY' ? 'bg-green-500' : 'bg-red-500'}`}
                        style={{ width: `${signal.confidence * 100}%` }}
                      />
                    </div>
                    {signal.confidence >= 0.70 && (
                      <div className="text-xs text-green-400 mt-1">✓ Meets confidence threshold</div>
                    )}
                  </div>

                  {/* Trade Details */}
                  <div className="space-y-2 mb-4 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Entry:</span>
                      <span className="font-mono font-medium text-white">{signal.entry}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Stop Loss:</span>
                      <span className="font-mono text-red-400">{signal.stop_loss}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Take Profit:</span>
                      <span className="font-mono text-green-400">{signal.take_profit}</span>
                    </div>
                    <div className="flex justify-between pt-2 border-t border-gray-700">
                      <span className="text-gray-400">Risk:Reward:</span>
                      <span className="font-bold text-blue-400">1:{signal.risk_reward}</span>
                    </div>
                  </div>

                  {/* Risk Warning */}
                  {signal.risk_reward < 1.5 && (
                    <div className="mb-3 text-xs text-yellow-400 bg-yellow-400/10 p-2 rounded">
                      ⚠️ Low risk:reward ratio
                    </div>
                  )}

                  {/* Copy Button */}
                  <button
                    onClick={() => {
                      const text = `${signal.signal} ${signal.pair}\nEntry: ${signal.entry}\nSL: ${signal.stop_loss}\nTP: ${signal.take_profit}\nR:R 1:${signal.risk_reward}\nConfidence: ${(signal.confidence * 100).toFixed(0)}%`;
                      navigator.clipboard.writeText(text);
                      alert('✅ Trade details copied to clipboard!');
                    }}
                    className="w-full bg-white/10 hover:bg-white/20 py-2 rounded-lg transition font-medium text-sm"
                  >
                    📋 Copy Trade Details
                  </button>
                </div>
              ))}
            </div>
          </>
        )}
      </main>
    
      <footer className="border-t border-gray-800 mt-12 py-6 text-center text-gray-500 text-sm">
        <p>⚠️ For educational purposes only. Trade at your own risk.</p>
        <p className="mt-1">ICT + SMC Strategy | XGBoost ML | Real-time WebSocket</p>
        <p className="mt-1 text-xs">
          Status: {connected ? '🟢 Connected to signal server' : '🔴 Disconnected'}
        </p>
      </footer>
    </div>
  );
}

export default App;