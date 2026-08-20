"""
Trade Quality Score - 0-100 based on all filters.
Only trades scoring 60+ should execute.
"""
def score_trade_quality(signal_dict):
    score = 0
    reasons = []
    
    # Institutional (0-30)
    inst = signal_dict.get('institutional_score', 0)
    if inst >= 70: score += 30
    elif inst >= 55: score += 20
    else: reasons.append("Low institutional score")
    
    # Dealer pressure (0-20)
    dealer = signal_dict.get('dealer_pressure', 'NEUTRAL')
    if dealer in ('BUYING_PRESSURE','SELLING_PRESSURE'): score += 20
    elif dealer in ('ACCUMULATING','DISTRIBUTING'): score += 15
    else: reasons.append("Neutral dealer")
    
    # Liquidity (0-15)
    liq = signal_dict.get('liquidity_state', 'NO_EVENT')
    if 'SWEEP' in str(liq) or 'IMBALANCE' in str(liq): score += 15
    elif liq == 'NO_EVENT': reasons.append("No liquidity event")
    else: score += 10
    
    # Confidence (0-20)
    conf = signal_dict.get('confidence', 0)
    if conf >= 0.60: score += 20
    elif conf >= 0.55: score += 15
    elif conf >= 0.50: score += 10
    else: reasons.append("Low confidence")
    
    # Session (0-15)
    from datetime import datetime, timezone
    hour = datetime.now(timezone.utc).hour
    if 10 <= hour < 13: score += 15  # London Mid
    elif 7 <= hour < 17: score += 10  # London
    else: reasons.append("Outside optimal session")
    
    grade = 'A' if score >= 85 else 'B' if score >= 70 else 'C' if score >= 60 else 'D' if score >= 50 else 'F'
    
    return {'score': score, 'grade': grade, 'reasons': reasons}
