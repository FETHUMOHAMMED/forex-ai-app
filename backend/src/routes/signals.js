import { Router } from 'express';

const router = Router();

// Shared signals storage (would normally be in a service)
let globalSignals: any[] = [];

export function setSignals(signals: any[]) {
  globalSignals = signals;
}

router.get('/', (req, res) => {
  res.json(globalSignals);
});

router.get('/:pair', (req, res) => {
  const signal = globalSignals.find(s => s.pair === req.params.pair);
  res.json(signal || null);
});

export default router;