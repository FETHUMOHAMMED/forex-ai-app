"""
Phase 11: Auto-Optimizer
Automatically applies high-confidence learning insights to config.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from learning_engine import AdaptiveLearningEngine
from datetime import datetime

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'config.json')

def auto_optimize():
    """Apply high-confidence insights automatically"""
    engine = AdaptiveLearningEngine()
    insights = engine.analyze()
    
    # Only apply HIGH impact insights with >75% confidence
    high_confidence = [i for i in insights 
                      if i.expected_impact == 'HIGH' and i.confidence >= 0.75]
    
    if not high_confidence:
        print("No high-confidence insights to apply.")
        return
    
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    changes_made = []
    
    for insight in high_confidence:
        if insight.category == 'pair' and 'remove' in insight.recommendation.lower():
            pair_to_remove = insight.finding.split(':')[0].strip().split()[-1]
            
            # Remove from Demo2 pairs
            for acc in config.get('accounts', []):
                if acc.get('name') == 'Demo2':
                    if pair_to_remove in acc.get('pairs', []):
                        acc['pairs'].remove(pair_to_remove)
                        changes_made.append(f"Removed {pair_to_remove} from Demo2 pairs")
        
        elif insight.category == 'confidence':
            # Extract recommended confidence
            rec = insight.recommendation
            if '0.' in rec:
                new_conf = float(rec.split('0.')[1][:2]) / 100 + 0.5
                for acc in config.get('accounts', []):
                    if acc.get('name') == 'Demo2':
                        old_conf = acc.get('min_confidence', 0.55)
                        acc['min_confidence'] = round(new_conf, 2)
                        changes_made.append(f"Changed Demo2 min_confidence from {old_conf} to {new_conf}")
    
    if changes_made:
        # Backup old config
        backup_path = CONFIG_PATH.replace('.json', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(backup_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Save new config
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        
        print("=" * 50)
        print("  AUTO-OPTIMIZER APPLIED")
        print("=" * 50)
        for change in changes_made:
            print(f"  ✅ {change}")
        print(f"  Backup saved to: {backup_path}")
    else:
        print("No changes needed.")


if __name__ == '__main__':
    auto_optimize()