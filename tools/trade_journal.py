"""Manual trade journal for observations."""
import json
from datetime import datetime, timezone
from pathlib import Path

class TradeJournal:
    """Record observations and lessons during forward testing."""
    
    def __init__(self):
        self.journal_dir = Path("research/forward_test/journal")
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self.journal_file = self.journal_dir / "observations.jsonl"
    
    def add_entry(self, entry_type, notes):
        """Add a journal entry."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": entry_type,  # SETUP, TRADE, OBSERVATION, LESSON, ERROR
            "notes": notes
        }
        
        with open(self.journal_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        print(f"Journal entry added: {entry_type}")
    
    def add_setup_observation(self, direction, entry, sl, tp, notes=""):
        """Record a setup observation."""
        self.add_entry("SETUP", {
            "direction": direction,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "notes": notes
        })
    
    def add_missed_trade(self, reason, notes=""):
        """Record a missed trade (important for learning)."""
        self.add_entry("MISSED", {
            "reason": reason,
            "notes": notes
        })
    
    def view_journal(self):
        """View recent journal entries."""
        if not self.journal_file.exists():
            print("No journal entries yet")
            return
        
        print("\nRecent journal entries:")
        with open(self.journal_file, 'r') as f:
            lines = f.readlines()
        
        for line in lines[-10:]:  # Last 10 entries
            entry = json.loads(line)
            print(f"\n{entry['timestamp']}")
            print(f"  Type: {entry['type']}")
            print(f"  Notes: {entry['notes']}")

if __name__ == "__main__":
    journal = TradeJournal()
    
    # Interactive mode
    print("="*60)
    print("  TRADE JOURNAL")
    print("="*60)
    print("1. Add setup observation")
    print("2. Add missed trade")
    print("3. Add general observation")
    print("4. View recent entries")
    print("5. Exit")
    
    while True:
        choice = input("\nChoice (1-5): ").strip()
        
        if choice == "1":
            direction = input("Direction (BUY/SELL): ").upper()
            entry = float(input("Entry price: "))
            sl = float(input("Stop loss: "))
            tp = float(input("Take profit: "))
            notes = input("Notes: ")
            journal.add_setup_observation(direction, entry, sl, tp, notes)
        
        elif choice == "2":
            reason = input("Reason missed: ")
            notes = input("Notes: ")
            journal.add_missed_trade(reason, notes)
        
        elif choice == "3":
            notes = input("Observation: ")
            journal.add_entry("OBSERVATION", notes)
        
        elif choice == "4":
            journal.view_journal()
        
        elif choice == "5":
            break
