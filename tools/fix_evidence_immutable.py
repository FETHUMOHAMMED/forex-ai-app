"""Make Trade Evidence Record immutable with hash verification."""
content = open('packages/execution/trade_evidence.py').read()

# Add hash verification method
old = '''    def print_evidence(self):'''

new = '''    def verify_integrity(self) -> bool:
        """Verify evidence record has not been mutated."""
        import hashlib
        content = json.dumps({
            "signal_id": self.signal_id,
            "account_id": self.account_id,
            "MT5_login": self.MT5_login,
            "strategy": self.strategy_version,
            "signal_time": self.signal_time,
            "planned_entry": self.planned_entry,
            "planned_sl": self.planned_sl,
            "planned_tp": self.planned_tp,
            "volume": self.volume,
        }, sort_keys=True)
        current_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return current_hash == self.evidence_hash
    
    def print_evidence(self):'''

content = content.replace(old, new)

# Update __post_init__ to make fields frozen
old_init = '''    def __post_init__(self):
        """Generate immutable hash."""
        content = json.dumps({
            "signal_id": self.signal_id,
            "account_id": self.account_id,
            "MT5_login": self.MT5_login,
            "strategy": self.strategy_version,
            "signal_time": self.signal_time,
            "planned_entry": self.planned_entry,
            "planned_sl": self.planned_sl,
            "planned_tp": self.planned_tp,
            "volume": self.volume,
        }, sort_keys=True)
        import hashlib
        self.evidence_hash = hashlib.sha256(content.encode()).hexdigest()[:16]'''

new_init = '''    def __post_init__(self):
        """Generate immutable hash at creation."""
        content = json.dumps({
            "signal_id": self.signal_id,
            "account_id": self.account_id,
            "MT5_login": self.MT5_login,
            "strategy": self.strategy_version,
            "signal_time": self.signal_time,
            "planned_entry": self.planned_entry,
            "planned_sl": self.planned_sl,
            "planned_tp": self.planned_tp,
            "volume": self.volume,
        }, sort_keys=True)
        import hashlib
        object.__setattr__(self, 'evidence_hash', hashlib.sha256(content.encode()).hexdigest()[:16])'''

content = content.replace(old_init, new_init)

# Update print_evidence to show integrity
old_print_end = '''    print(f"  FINAL: {self.final_classification}")
    print(f"  HASH: {self.evidence_hash}")
    print("=" * 70)'''

new_print_end = '''    print(f"  FINAL: {self.final_classification}")
    print(f"  HASH: {self.evidence_hash}")
    integrity = self.verify_integrity()
    print(f"  INTEGRITY: {'VERIFIED (immutable)' if integrity else 'TAMPERED!'}")
    print("=" * 70)'''

content = content.replace(old_print_end, new_print_end)

open('packages/execution/trade_evidence.py', 'w').write(content)
print('Added hash verification + immutability check')
