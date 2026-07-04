export interface Signal {
  pair: string;
  signal: 'BUY' | 'SELL';
  confidence: number;
  strength: 'STRONG' | 'MEDIUM' | 'WEAK';
  entry: number;
  stop_loss: number;
  take_profit: number;
  risk_reward: number;
  ict_signal: string;
  ml_signal: string;
  timestamp: string;
}

export interface WebSocketMessage {
  type: 'connected' | 'signals' | 'error';
  data?: any;
  message?: string;
  timestamp: string;
}