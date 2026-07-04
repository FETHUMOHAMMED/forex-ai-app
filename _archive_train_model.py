"""
Train and save XGBoost model
"""
from ai_service import ForexAITrader
import joblib

def main():
    print("Training Forex AI Model...")
    trader = ForexAITrader()
    
    # Train on multiple pairs
    pairs = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X']
    
    for pair in pairs:
        print(f"\n--- Training on {pair} ---")
        success = trader.train_model(pair, days=120)
        if success:
            # Save model
            filename = f"models/{pair.replace('=X', '')}_model.joblib"
            joblib.dump(trader.model, filename)
            print(f"✅ Model saved to {filename}")

if __name__ == "__main__":
    main()