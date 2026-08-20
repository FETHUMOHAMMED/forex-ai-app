export default function V3Performance({ data }) {
  if (!data) return <div className="card">Loading V3 data...</div>;
  
  return (
    <div className="card bg-gray-800 p-4 rounded-lg">
      <h2 className="text-white text-lg font-bold mb-3">PERFORMANCE — V3_REGIME</h2>
      <div className="grid grid-cols-4 gap-3 text-sm">
        <div><span className="text-gray-400">Trades</span><div className="text-white font-bold">{data.trades || 0}</div></div>
        <div><span className="text-gray-400">Win Rate</span><div className="text-white font-bold">{data.win_rate || 'N/A'}</div></div>
        <div><span className="text-gray-400">Profit Factor</span><div className="text-white font-bold">{data.profit_factor || 'N/A'}</div></div>
        <div><span className="text-gray-400">Expectancy</span><div className="text-white font-bold">{data.expectancy || 'N/A'}</div></div>
        <div><span className="text-gray-400">Avg Win</span><div className="text-green-400">{data.avg_win || 'N/A'}</div></div>
        <div><span className="text-gray-400">Avg Loss</span><div className="text-red-400">{data.avg_loss || 'N/A'}</div></div>
        <div><span className="text-gray-400">Avg R</span><div className="text-white">{data.avg_r || 'N/A'}</div></div>
        <div><span className="text-gray-400">Avg Confidence</span><div className="text-white">{data.avg_confidence ? data.avg_confidence + '%' : 'N/A'}</div></div>
      </div>
      <div className="grid grid-cols-3 gap-3 text-sm mt-3 pt-3 border-t border-gray-700">
        <div><span className="text-gray-400">Best Trade</span><div className="text-green-400">${data.best_trade || 0}</div></div>
        <div><span className="text-gray-400">Worst Trade</span><div className="text-red-400">${data.worst_trade || 0}</div></div>
        <div><span className="text-gray-400">Net P&L</span><div className={`font-bold ${(data.pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>${data.pnl || 0}</div></div>
      </div>
      {!data.is_meaningful && (
        <div className="mt-3 text-yellow-400 text-xs bg-yellow-900/30 p-2 rounded">
          Collecting statistical data — {data.trades || 0}/100 trades. Win rate hidden until 10+ trades.
        </div>
      )}
    </div>
  );
}
