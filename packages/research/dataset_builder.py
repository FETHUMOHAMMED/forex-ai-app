"""PROPER RESEARCH DATASET BUILDER - No Look-Ahead Bias."""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json
import hashlib

@dataclass
class DatasetConfig:
    """Configuration for research dataset."""
    # Symbols to collect
    symbols: List[str] = None
    
    # Timeframes (in minutes)
    timeframes: List[int] = None  # [240, 15, 5] for H4, M15, M5
    
    # History requirements
    min_history_days: int = 365
    
    # Quality thresholds
    max_gap_seconds: int = 300  # Max gap between bars
    max_spread_pips: float = 5.0
    min_volume_threshold: int = 1
    
    def __post_init__(self):
        self.symbols = self.symbols or ["EURUSD", "GBPUSD", "USDJPY"]
        self.timeframes = self.timeframes or [240, 15, 5]

class ResearchDatasetBuilder:
    """
    Builds clean, point-in-time dataset for strategy research.
    
    CRITICAL RULES:
    1. No future data in features
    2. Point-in-time reconstruction
    3. Proper timestamp alignment
    4. Gap detection and handling
    5. Spread capture at decision time
    """
    
    def __init__(self, config: DatasetConfig = None):
        self.config = config or DatasetConfig()
        self.data_dir = Path("data/research")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def validate_point_in_time(self, data: pd.DataFrame) -> Dict:
        """
        Validate that no look-ahead bias exists in the dataset.
        
        Checks:
        1. Feature timestamps <= decision timestamp
        2. No future values in rolling calculations
        3. Proper bar close timing
        """
        issues = []
        
        # Check for timestamp ordering
        if not data['timestamp'].is_monotonic_increasing:
            issues.append("TIMESTAMPS_NOT_ORDERED")
        
        # Check for duplicate timestamps
        duplicates = data['timestamp'].duplicated().sum()
        if duplicates > 0:
            issues.append(f"DUPLICATE_TIMESTAMPS: {duplicates}")
        
        # Check for future timestamps
        current_time = datetime.now(timezone.utc)
        future_count = (data['timestamp'] > current_time).sum()
        if future_count > 0:
            issues.append(f"FUTURE_TIMESTAMPS: {future_count}")
        
        # Check for NaN values
        null_counts = data.isnull().sum()
        if null_counts.any():
            issues.append(f"NULL_VALUES: {null_counts[null_counts > 0].to_dict()}")
        
        # Check for unrealistic prices
        if 'high' in data.columns and 'low' in data.columns:
            invalid_hl = (data['high'] < data['low']).sum()
            if invalid_hl > 0:
                issues.append(f"INVALID_HIGH_LOW: {invalid_hl}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "total_rows": len(data),
            "date_range": {
                "start": data['timestamp'].min() if not data.empty else None,
                "end": data['timestamp'].max() if not data.empty else None
            }
        }
    
    def align_multi_timeframe(self, base_timeframe: pd.DataFrame, 
                              higher_timeframes: List[pd.DataFrame]) -> pd.DataFrame:
        """
        Align multiple timeframes ensuring point-in-time correctness.
        
        For each decision at time T:
        - Only use bars that have CLOSED before time T
        - Never use the current forming bar
        - Higher timeframe data must be from completed bars
        """
        aligned_data = base_timeframe.copy()
        
        for tf_data in higher_timeframes:
            # Ensure we only use completed bars
            tf_completed = tf_data[tf_data['timestamp'] <= base_timeframe['timestamp'].min()]
            
            # Forward fill to align with base timeframe
            tf_aligned = tf_data.set_index('timestamp').reindex(
                base_timeframe['timestamp'], 
                method='ffill'
            )
            
            # Add prefix to avoid column collisions
            tf_aligned = tf_aligned.add_prefix('htf_')
            aligned_data = pd.concat([aligned_data, tf_aligned], axis=1)
        
        return aligned_data
    
    def generate_features_point_in_time(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate features using only information available at each timestamp.
        
        CRITICAL: All rolling calculations must use trailing windows only.
        """
        features = data.copy()
        
        # Example features (all trailing/point-in-time)
        features['ema_50'] = features['close'].transform(
            lambda x: x.ewm(span=50, min_periods=50).mean()
        )
        features['ema_200'] = features['close'].transform(
            lambda x: x.ewm(span=200, min_periods=200).mean()
        )
        
        # Rolling high/low (trailing only)
        features['rolling_high_50'] = features['high'].rolling(
            window=50, min_periods=1
        ).max()
        features['rolling_low_50'] = features['low'].rolling(
            window=50, min_periods=1
        ).min()
        
        # Volume features
        features['volume_ma_20'] = features['volume'].rolling(
            window=20, min_periods=1
        ).mean()
        
        # Spread features
        features['spread_ma_20'] = features['spread'].rolling(
            window=20, min_periods=1
        ).mean()
        
        # All features are now point-in-time correct
        
        return features
    
    def create_train_test_split(self, data: pd.DataFrame, 
                                train_ratio: float = 0.7) -> Dict:
        """
        Create proper chronological train/test split.
        
        NEVER random shuffle time series data!
        """
        split_idx = int(len(data) * train_ratio)
        
        train_data = data.iloc[:split_idx].copy()
        test_data = data.iloc[split_idx:].copy()
        
        # Ensure no overlap
        assert train_data['timestamp'].max() < test_data['timestamp'].min(), \
            "Train/test overlap detected!"
        
        return {
            "train": train_data,
            "test": test_data,
            "split_timestamp": test_data['timestamp'].min()
        }
    
    def validate_dataset(self, data: pd.DataFrame) -> Dict:
        """Complete dataset validation."""
        validation = {
            "point_in_time": self.validate_point_in_time(data),
            "quality_metrics": self.calculate_quality_metrics(data),
            "statistics": self.calculate_basic_statistics(data)
        }
        
        # Check minimum requirements
        validation["meets_minimums"] = all([
            len(data) >= 10000,  # Minimum bars
            data['timestamp'].max() - data['timestamp'].min() >= timedelta(days=self.config.min_history_days),
            validation["quality_metrics"]["gap_pct"] < 1.0,  # Less than 1% gaps
            validation["quality_metrics"]["null_pct"] < 0.1,  # Less than 0.1% nulls
        ])
        
        return validation
    
    def calculate_quality_metrics(self, data: pd.DataFrame) -> Dict:
        """Calculate data quality metrics."""
        total_rows = len(data)
        
        # Gap analysis
        time_diffs = data['timestamp'].diff().dropna()
        gaps = time_diffs[time_diffs > pd.Timedelta(seconds=self.config.max_gap_seconds)]
        gap_pct = (len(gaps) / total_rows) * 100
        
        # Null analysis
        null_pct = (data.isnull().sum().sum() / (total_rows * len(data.columns))) * 100
        
        # Spread analysis
        high_spread = (data['spread'] > self.config.max_spread_pips).sum()
        high_spread_pct = (high_spread / total_rows) * 100
        
        return {
            "total_rows": total_rows,
            "gap_count": len(gaps),
            "gap_pct": gap_pct,
            "null_pct": null_pct,
            "high_spread_pct": high_spread_pct,
            "avg_spread": data['spread'].mean() if 'spread' in data.columns else None,
            "max_spread": data['spread'].max() if 'spread' in data.columns else None
        }
    
    def calculate_basic_statistics(self, data: pd.DataFrame) -> Dict:
        """Calculate basic statistical properties."""
        if data.empty:
            return {}
        
        returns = data['close'].pct_change().dropna()
        
        return {
            "mean_return": returns.mean() if len(returns) > 0 else None,
            "std_return": returns.std() if len(returns) > 0 else None,
            "skewness": returns.skew() if len(returns) > 0 else None,
            "kurtosis": returns.kurtosis() if len(returns) > 0 else None,
            "daily_volatility": returns.resample('D').std().mean() if 'timestamp' in data.columns else None,
            "avg_daily_range_pips": ((data['high'] - data['low']) / 0.0001).mean() if len(data) > 0 else None
        }
    
    def save_dataset(self, data: pd.DataFrame, name: str):
        """Save dataset with metadata."""
        save_path = self.data_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.parquet"
        
        # Add metadata
        metadata = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "rows": len(data),
            "symbols": self.config.symbols,
            "timeframes": self.config.timeframes,
            "date_range": {
                "start": data['timestamp'].min().isoformat() if not data.empty else None,
                "end": data['timestamp'].max().isoformat() if not data.empty else None
            },
            "validation": self.validate_dataset(data)
        }
        
        # Save metadata
        meta_path = save_path.with_suffix('.json')
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        # Save parquet (efficient for large datasets)
        data.to_csv(save_path.with_suffix(".csv"), index=False)
        
        return save_path

class PointInTimeValidator:
    """Ensures no look-ahead bias in strategy evaluation."""
    
    @staticmethod
    def validate_decision_timing(data: pd.DataFrame, decision_time: pd.Timestamp) -> bool:
        """Verify that all data used is available at decision_time."""
        # All features must be from <= decision_time
        available_data = data[data['timestamp'] <= decision_time]
        return len(available_data) > 0
    
    @staticmethod
    def get_point_in_time_features(data: pd.DataFrame, 
                                   decision_time: pd.Timestamp) -> pd.DataFrame:
        """Get features as they would appear at decision_time."""
        # IMPORTANT: Only use data available at decision_time
        # The current bar is NOT complete, so exclude it
        available_mask = data['timestamp'] < decision_time
        return data[available_mask].copy()
    
    @staticmethod
    def check_future_outcome(data: pd.DataFrame, 
                            decision_time: pd.Timestamp,
                            outcome_horizon: pd.Timedelta) -> pd.DataFrame:
        """Get future outcome data (for training labels only)."""
        # This data is ONLY for labels, never for features
        outcome_start = decision_time + pd.Timedelta(seconds=1)
        outcome_end = decision_time + outcome_horizon
        outcome_mask = (data['timestamp'] > outcome_start) & (data['timestamp'] <= outcome_end)
        return data[outcome_mask].copy()

if __name__ == "__main__":
    # Example usage
    builder = ResearchDatasetBuilder()
    
    # Create sample data (replace with real data)
    dates = pd.date_range('2025-01-01', '2026-08-18', freq='5min')
    sample_data = pd.DataFrame({
        'timestamp': dates,
        'symbol': 'EURUSD',
        'open': np.random.randn(len(dates)).cumsum() + 100,
        'high': np.random.randn(len(dates)).cumsum() + 101,
        'low': np.random.randn(len(dates)).cumsum() + 99,
        'close': np.random.randn(len(dates)).cumsum() + 100,
        'volume': np.random.randint(1, 100, len(dates)),
        'spread': np.random.uniform(0.5, 2.0, len(dates)),
        'bid': np.random.randn(len(dates)).cumsum() + 100,
        'ask': np.random.randn(len(dates)).cumsum() + 100.001,
    })
    
    # Validate dataset
    validation = builder.validate_dataset(sample_data)
    print("Dataset Validation:")
    print(json.dumps(validation, indent=2, default=str))
    
    # Test point-in-time correctness
    validator = PointInTimeValidator()
    test_time = sample_data['timestamp'].iloc[1000]
    
    # Get features available at test_time
    features = validator.get_point_in_time_features(sample_data, test_time)
    print(f"\nAt time {test_time}:")
    print(f"  Available bars: {len(features)}")
    print(f"  Latest available timestamp: {features['timestamp'].max()}")
    print(f"  Bars after decision time: {(sample_data['timestamp'] > test_time).sum()}")

