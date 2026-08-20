import React from 'react';

/**
 * SafetyDominantCard - Safety is ALWAYS visually dominant over strategy.
 * Shows: AI Decision -> Control Decision -> Execution State
 * Makes it impossible to confuse "AI said BUY" with "trade happened".
 */
export default function SafetyDominantCard({ signal, control, execution }) {
  const getSafetyColor = (status) => {
    switch (status) {
      case 'BLOCKED': return 'bg-red-600';
      case 'REJECTED': return 'bg-red-600';
      case 'NOT_SENT': return 'bg-gray-600';
      case 'PASSED': return 'bg-green-600';
      case 'SENT': return 'bg-green-600';
      default: return 'bg-gray-600';
    }
  };

  return (
    <div className="card bg-gray-900 p-6 rounded-lg border-2 border-gray-700">
      <h2 className="text-white text-xl font-bold mb-4">
        ? EXECUTION CONTROL
      </h2>
      
      {/* STRATEGY DECISION */}
      <div className="mb-4 p-4 bg-gray-800 rounded-lg">
        <div className="text-sm text-gray-400 uppercase tracking-wider">Strategy Decision</div>
        <div className="flex items-center justify-between mt-2">
          <span className="text-2xl font-bold text-blue-400">{signal?.direction || 'N/A'}</span>
          <span className="text-xl text-gray-300">{signal?.confidence ? `${signal.confidence}%` : 'N/A'}</span>
        </div>
        <div className="text-xs text-gray-500 mt-1">
          AI Model Output — NOT an execution result
        </div>
      </div>

      {/* CONTROL DECISION - DOMINANT */}
      <div className={`mb-4 p-4 rounded-lg ${control?.status === 'BLOCKED' ? 'bg-red-900/50 border-2 border-red-600' : 'bg-green-900/50 border-2 border-green-600'}`}>
        <div className="text-sm text-gray-400 uppercase tracking-wider">Control Decision</div>
        <div className="text-3xl font-bold mt-2" style={{ color: control?.status === 'BLOCKED' ? '#ef4444' : '#22c55e' }}>
          {control?.status || 'PENDING'}
        </div>
        {control?.reasons && control.reasons.length > 0 && (
          <div className="mt-2 space-y-1">
            {control.reasons.map((reason, idx) => (
              <div key={idx} className="text-sm text-red-300 font-semibold">
                ? {reason}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* EXECUTION STATE */}
      <div className="p-4 bg-gray-800 rounded-lg">
        <div className="text-sm text-gray-400 uppercase tracking-wider">Execution</div>
        <div className="text-2xl font-bold mt-2 text-gray-300">
          {execution?.status || 'NOT SENT'}
        </div>
      </div>

      {/* SAFETY NOTE */}
      <div className="mt-4 p-3 bg-yellow-900/30 border border-yellow-600 rounded text-yellow-400 text-sm">
        ?? Strategy decisions do NOT automatically execute.<br/>
        Every trade must pass the 11-gate execution contract.
      </div>
    </div>
  );
}
