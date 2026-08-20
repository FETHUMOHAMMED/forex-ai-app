"""P0: Exact MT5 Reconciliation - Position-level, never symbol-wide.
Replaces the old pattern: "query all EURUSD deals" -> "exact position lineage"
"""
import MetaTrader5 as mt5
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional, List, Dict

@dataclass
class MT5PositionLineage:
    """Exact MT5 position lineage - ONE position, its deals, its PnL"""
    position_ticket: int
    symbol: str
    entry_deal: Optional[Dict] = None
    exit_deal: Optional[Dict] = None
    partial_deals: List[Dict] = None
    
    @property
    def entry_price(self) -> Optional[float]:
        return self.entry_deal['price'] if self.entry_deal else None
    
    @property
    def exit_price(self) -> Optional[float]:
        return self.exit_deal['price'] if self.exit_deal else None
    
    @property
    def volume(self) -> Optional[float]:
        return self.entry_deal['volume'] if self.entry_deal else None
    
    @property
    def net_pnl(self) -> float:
        pnl = 0.0
        if self.entry_deal: pnl += self.entry_deal.get('profit', 0)
        if self.exit_deal: pnl += self.exit_deal.get('profit', 0)
        if self.entry_deal: pnl += self.entry_deal.get('commission', 0)
        if self.exit_deal: pnl += self.exit_deal.get('commission', 0)
        if self.exit_deal: pnl += self.exit_deal.get('swap', 0)
        return round(pnl, 2)
    
    @property
    def is_complete(self) -> bool:
        return self.entry_deal is not None and self.exit_deal is not None


def resolve_trade_identity(position_ticket: int, 
                           from_date: datetime = None,
                           to_date: datetime = None) -> MT5PositionLineage:
    """
    P0: Resolve EXACT position lineage from MT5.
    NEVER queries by symbol. NEVER returns unrelated deals.
    
    Args:
        position_ticket: The MT5 position ticket (from positions_get or order_send)
        from_date: Start of history window
        to_date: End of history window
    
    Returns:
        MT5PositionLineage with entry deal, exit deal, and net PnL
    """
    if from_date is None:
        from_date = datetime(2026, 8, 1, tzinfo=timezone.utc)
    if to_date is None:
        to_date = datetime.now(timezone.utc)
    
    mt5.initialize()
    
    # QUERY BY POSITION - not symbol, not approximate
    deals = mt5.history_deals_get(from_date, to_date, position=position_ticket)
    
    lineage = MT5PositionLineage(
        position_ticket=position_ticket,
        symbol="",
        partial_deals=[]
    )
    
    if deals:
        for deal in deals:
            # ONLY deals belonging to THIS position
            if deal.position_id != position_ticket:
                continue
            
            deal_info = {
                'ticket': deal.ticket,
                'position_id': deal.position_id,
                'price': deal.price,
                'volume': deal.volume,
                'profit': deal.profit,
                'commission': deal.commission,
                'swap': deal.swap,
                'entry': deal.entry,  # 0=IN, 1=OUT
                'time': datetime.fromtimestamp(deal.time, tz=timezone.utc),
                'reason': deal.reason,
            }
            
            lineage.symbol = deal.symbol
            
            if deal.entry == 0:  # Position opened
                lineage.entry_deal = deal_info
            elif deal.entry == 1:  # Position closed
                lineage.exit_deal = deal_info
                lineage.partial_deals.append(deal_info)
    
    mt5.shutdown()
    return lineage


def reconcile_db_with_mt5(db_entry: float, db_exit: float, db_pnl: float,
                          db_volume: float, position_ticket: int) -> Dict:
    """
    P0: Full reconciliation of a DB trade against exact MT5 position.
    Returns PASS/FAIL for each field.
    """
    lineage = resolve_trade_identity(position_ticket)
    
    result = {
        'position_ticket': position_ticket,
        'mt5_found': lineage.is_complete,
        'checks': {}
    }
    
    if lineage.entry_price:
        match = abs(db_entry - lineage.entry_price) < 0.0001
        result['checks']['entry_price'] = {
            'db': db_entry, 'mt5': lineage.entry_price, 'match': match
        }
    
    if lineage.exit_price and db_exit:
        match = abs(db_exit - lineage.exit_price) < 0.0001
        result['checks']['exit_price'] = {
            'db': db_exit, 'mt5': lineage.exit_price, 'match': match
        }
    
    if lineage.volume and db_volume:
        match = abs(db_volume - lineage.volume) < 0.001
        result['checks']['volume'] = {
            'db': db_volume, 'mt5': lineage.volume, 'match': match
        }
    
    if lineage.is_complete and db_pnl is not None:
        match = abs(db_pnl - lineage.net_pnl) < 0.01
        result['checks']['pnl'] = {
            'db': db_pnl, 'mt5': lineage.net_pnl, 'match': match
        }
    
    result['all_pass'] = all(c['match'] for c in result['checks'].values())
    return result
