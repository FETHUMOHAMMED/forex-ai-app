"""CANONICAL EVIDENCE LOADER - Single source of truth for research counts."""
import json
from pathlib import Path
from datetime import datetime

class CanonicalEvidence:
    """
    THE authoritative evidence loader.
    All research reports must use this.
    
    Unique key: (symbol, timeframe, candle_close_time)
    """
    
    def __init__(self):
        self.evidence_path = Path(
            "research/paper/V4_CANONICAL_1.0/evidence/evaluations.jsonl"
        )
    
    def load(self):
        """Load and deduplicate by canonical key."""
        if not self.evidence_path.exists():
            return []
        
        rows = [
            json.loads(x) for x in 
            self.evidence_path.read_text().splitlines() 
            if x.strip()
        ]
        
        # Deduplicate by (symbol, timeframe, candle_close_time)
        unique = {}
        for r in rows:
            key = (
                r.get('symbol', 'UNKNOWN'),
                r.get('timeframe', 'UNKNOWN'),
                r.get('candle_close_time') or r.get('timestamp_utc', '')
            )
            if key not in unique:
                unique[key] = r
        
        # Sort by timestamp
        return sorted(unique.values(), key=lambda x: x.get('candle_close_time', ''))
    
    def count(self):
        """Return unique candle count (THE denominator)."""
        return len(self.load())
    
    def stats(self):
        """Return summary statistics."""
        candles = self.load()
        total = len(candles)
        
        if total == 0:
            return {"total": 0}
        
        # Component analysis
        london = sum(1 for c in candles if c.get('session') == 'LONDON')
        bullish = sum(1 for c in candles if c.get('bias') == 'BULLISH')
        fvg = sum(1 for c in candles if c.get('fvg_detected'))
        london_bullish = sum(1 for c in candles 
                            if c.get('session') == 'LONDON' and c.get('bias') == 'BULLISH')
        london_fvg = sum(1 for c in candles 
                        if c.get('session') == 'LONDON' and c.get('fvg_detected'))
        all_three = sum(1 for c in candles 
                       if c.get('session') == 'LONDON' 
                       and c.get('bias') == 'BULLISH' 
                       and c.get('fvg_detected'))
        
        return {
            "total": total,
            "london": london,
            "bullish": bullish,
            "fvg": fvg,
            "london_bullish": london_bullish,
            "london_fvg": london_fvg,
            "all_three": all_three,
        }
    
    def date_range(self):
        """Return first and last observation timestamps."""
        candles = self.load()
        if not candles:
            return None, None
        return (
            candles[0].get('candle_close_time') or candles[0].get('timestamp_utc'),
            candles[-1].get('candle_close_time') or candles[-1].get('timestamp_utc')
        )

if __name__ == "__main__":
    ev = CanonicalEvidence()
    stats = ev.stats()
    first, last = ev.date_range()
    
    print("="*70)
    print("  CANONICAL EVIDENCE")
    print("="*70)
    print(f"\n  Unique H4 candles: {stats['total']}")
    print(f"  Date range: {first[:19] if first else 'N/A'} to {last[:19] if last else 'N/A'}")
    print(f"\n  Component Coverage:")
    print(f"    London:              {stats['london']} ({stats['london']/stats['total']*100:.1f}%)")
    print(f"    Bullish bias:        {stats['bullish']} ({stats['bullish']/stats['total']*100:.1f}%)")
    print(f"    FVG:                 {stats['fvg']} ({stats['fvg']/stats['total']*100:.1f}%)")
    print(f"    London + Bullish:    {stats['london_bullish']} ({stats['london_bullish']/stats['total']*100:.1f}%)")
    print(f"    London + FVG:        {stats['london_fvg']} ({stats['london_fvg']/stats['total']*100:.1f}%)")
    print(f"    All three:           {stats['all_three']} ({stats['all_three']/stats['total']*100:.1f}%)")
    print("="*70)
