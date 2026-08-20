export default function ResearchProgress({ data }) {
  if (!data) return null;
  const milestones = data.milestones || [
    { label: "Execution Verified", target: 10 },
    { label: "Risk Verified", target: 25 },
    { label: "Initial Review", target: 50 },
    { label: "Statistical Validation", target: 100 },
    { label: "Production Ready", target: 300 },
  ];
  const trades = data.trades || 0;
  const target = data.target || 100;
  const pct = Math.min((trades / target) * 100, 100);
  
  return (
    <div className="card bg-gray-800 p-4 rounded-lg">
      <h2 className="text-white text-lg font-bold mb-3">RESEARCH PROGRESS</h2>
      <div className="text-3xl font-bold text-blue-400">{trades}/{target}</div>
      <div className="w-full bg-gray-700 rounded-full h-3 mt-2">
        <div className="bg-blue-500 h-3 rounded-full" style={{ width: `${pct}%` }}></div>
      </div>
      <div className="text-xs text-gray-400 mt-1">Stage: {trades < 10 ? 'Micro Validation' : trades < 50 ? 'Execution Phase' : 'Statistical Phase'} | Confidence: {trades < 50 ? 'LOW' : 'MEDIUM'}</div>
      <div className="mt-3 space-y-1">
        {milestones.map((m, i) => (
          <div key={i} className="flex items-center text-sm">
            <span className={`mr-2 ${trades >= m.target ? 'text-green-400' : 'text-gray-600'}`}>{trades >= m.target ? '?' : '?'}</span>
            <span className={trades >= m.target ? 'text-green-400' : 'text-gray-400'}>{m.target} trades: {m.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
