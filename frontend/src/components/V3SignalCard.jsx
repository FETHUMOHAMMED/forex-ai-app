export default function V3SignalCard({ signals }) {
  if (!signals || signals.length === 0) return <div className="card">No active signals</div>;
  
  return (
    <div className="card bg-gray-800 p-4 rounded-lg">
      <h2 className="text-white text-lg font-bold mb-3">CURRENT AI SIGNALS</h2>
      {signals.map((sig, i) => (
        <div key={i} className={`${i > 0 ? 'mt-3 pt-3 border-t border-gray-700' : ''}`}>
          <div className="flex justify-between items-center">
            <span className="text-white font-bold text-lg">{sig.pair}</span>
            <span className={`px-2 py-0.5 rounded text-xs font-bold ${sig.direction === 'SELL' ? 'bg-red-600' : 'bg-green-600'}`}>{sig.direction}</span>
          </div>
          <div className="text-2xl font-bold text-blue-400 mt-1">{sig.confidence}%</div>
          <div className="text-xs text-gray-400 mt-1">Grade: {sig.confidence >= 85 ? 'A+' : sig.confidence >= 75 ? 'A' : 'B'}</div>
          <div className="grid grid-cols-2 gap-2 text-xs mt-2">
            <div><span className="text-gray-500">Regime:</span> <span className="text-white">{sig.regime || 'N/A'}</span></div>
            <div><span className="text-gray-500">Dealer:</span> <span className="text-white">{sig.dealer_pressure || 'N/A'}</span></div>
            <div><span className="text-gray-500">Liquidity:</span> <span className="text-white">{sig.liquidity_state || 'N/A'}</span></div>
            <div><span className="text-gray-500">RR:</span> <span className="text-white">2.0</span></div>
          </div>
          <div className="grid grid-cols-3 gap-2 text-xs mt-2 pt-2 border-t border-gray-700">
            <div><span className="text-gray-500">Entry</span><div className="text-white">{sig.entry}</div></div>
            <div><span className="text-gray-500">SL</span><div className="text-red-400">{sig.sl}</div></div>
            <div><span className="text-gray-500">TP</span><div className="text-green-400">{sig.tp}</div></div>
          </div>
        </div>
      ))}
    </div>
  );
}
