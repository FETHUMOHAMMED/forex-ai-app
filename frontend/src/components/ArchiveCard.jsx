export default function ArchiveCard({ data }) {
  if (!data) return null;
  
  return (
    <div className="card bg-gray-800/50 p-4 rounded-lg border border-gray-700 opacity-75">
      <h2 className="text-gray-400 text-lg font-bold mb-2">ARCHIVE: PRE_V3</h2>
      <div className="grid grid-cols-3 gap-2 text-sm">
        <div><span className="text-gray-500">Trades</span><div className="text-gray-300">{data.trades || 0}</div></div>
        <div><span className="text-gray-500">Win Rate</span><div className="text-gray-300">{data.win_rate || 0}%</div></div>
        <div><span className="text-gray-500">PF</span><div className="text-gray-300">{data.profit_factor || 0}</div></div>
      </div>
      <div className="text-red-400 text-sm mt-1">PnL: ${data.pnl || 0}</div>
      <div className="text-yellow-500 text-xs mt-2 bg-yellow-900/20 p-1 rounded">FROZEN — {data.status || 'ARCHIVED'}</div>
    </div>
  );
}
