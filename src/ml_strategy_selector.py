"""
ML-based Packing Strategy Selector for TetraboX

This module implements an intelligent strategy selector that uses machine learning
to choose the optimal packing algorithm based on order characteristics and 
container constraints.

Features:
- XGBoost-based classification with fallback to RandomForest
- 19 engineered features including container-aware metrics
- Rule-based fallback when ML model is not available
- Feature importance analysis and model interpretability
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from sklearn.ensemble import RandomForestClassifier
import joblib
import os
from .models import Product, Container, OrderItem


class StrategyPredictor:
    """ML-based packing strategy selector using XGBoost/RandomForest"""
    
    def __init__(self, model_path: str = "models/strategy_selector.pkl"):
        self.model_path = model_path
        self.model = None
        self.feature_names = [
            # Order characteristics
            'total_items',
            'unique_skus',
            'total_volume_cm3',
            'total_weight_g',
            'avg_item_volume',
            'volume_std',
            'size_diversity',
            
            # Container relationship features (enhanced)
            'utilization_potential',
            'weight_ratio',
            'fragility_ratio',
            'hazmat_flag',
            
            # Price features (refined)
            'cheapest_container_price',
            'avg_viable_container_price',
            'price_spread',
            
            # Advanced features
            'aspect_ratio_variance',
            'stackability_score',
            'container_fit_count',
            'min_containers_needed',
            'weight_to_volume_ratio',
        ]
        
        # Strategy labels mapping to packer.py functions
        self.strategies = ['greedy', 'best_fit', 'large_first', 'aggressive']
        
        # Load model if exists
        if os.path.exists(model_path):
            self.load_model()
    
    def extract_features(self, 
                         products: List[Product], 
                         containers: List[Container]) -> Dict[str, float]:
        """Extract comprehensive features from order and available containers"""
        
        # Basic order statistics
        total_items = len(products)
        unique_skus = len(set(p.sku for p in products))
        
        # Volume and weight calculations
        volumes = [p.width_mm * p.length_mm * p.height_mm / 1000.0 for p in products]  # cm³
        weights = [p.weight_g for p in products]
        
        total_volume_cm3 = sum(volumes)
        total_weight_g = sum(weights)
        avg_item_volume = np.mean(volumes) if volumes else 0
        volume_std = np.std(volumes) if len(volumes) > 1 else 0
        
        # Size diversity analysis
        max_volume = max(volumes) if volumes else 1
        min_volume = min(volumes) if volumes else 1
        size_diversity = max_volume / min_volume if min_volume > 0 else 1
        
        # Container characteristics analysis
        viable_containers = [c for c in containers if c.is_3d_box]
        max_container_volume = max(
            (c.inner_w_mm * c.inner_l_mm * c.inner_h_mm / 1000.0 for c in viable_containers),
            default=1
        )
        max_container_weight = max((c.max_weight_g for c in viable_containers), default=1)
        
        # ENHANCED FEATURES - Container relationship
        utilization_potential = total_volume_cm3 / max_container_volume if max_container_volume > 0 else 0
        weight_ratio = total_weight_g / max_container_weight if max_container_weight > 0 else 0
        
        # Fragility and hazmat analysis
        fragile_count = sum(1 for p in products if p.fragile)
        fragility_ratio = fragile_count / total_items if total_items > 0 else 0
        
        hazmat_count = sum(1 for p in products if p.hazmat_class)
        hazmat_flag = 1.0 if hazmat_count > 0 else 0.0
        
        # Price analysis (refined approach)
        container_prices = [c.price_try for c in viable_containers if c.price_try]
        cheapest_container_price = min(container_prices) if container_prices else 0
        avg_viable_container_price = np.mean(container_prices) if container_prices else 0
        price_spread = (max(container_prices) - min(container_prices)) / avg_viable_container_price \
                       if container_prices and avg_viable_container_price > 0 else 0
        
        # Advanced geometric features
        aspect_ratios = []
        stackable_count = 0
        for p in products:
            # Aspect ratio variance calculation
            w, l, h = p.width_mm, p.length_mm, p.height_mm
            if h > 0:
                aspect_ratios.extend([w/h, l/h, w/l if l > 0 else 1])
            
            # Stackability analysis (items with relatively flat base)
            if h > 0 and (w * l) / h > 100:  # Large base relative to height
                stackable_count += 1
        
        aspect_ratio_variance = np.var(aspect_ratios) if aspect_ratios else 0
        stackability_score = stackable_count / total_items if total_items > 0 else 0
        
        # Container compatibility analysis
        container_fit_count = 0
        for container in viable_containers:
            # Check if order could theoretically fit (with packing efficiency factor)
            container_vol = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm / 1000.0
            if total_volume_cm3 <= container_vol * 0.7 and total_weight_g <= container.max_weight_g:
                container_fit_count += 1
        
        min_containers_needed = max(1, int(np.ceil(utilization_potential)))
        weight_to_volume_ratio = total_weight_g / total_volume_cm3 if total_volume_cm3 > 0 else 0
        
        # Ensure all values are JSON-serializable Python types
        return {
            'total_items': float(total_items),
            'unique_skus': float(unique_skus),
            'total_volume_cm3': float(total_volume_cm3),
            'total_weight_g': float(total_weight_g),
            'avg_item_volume': float(avg_item_volume),
            'volume_std': float(volume_std),
            'size_diversity': float(size_diversity),
            'utilization_potential': float(utilization_potential),
            'weight_ratio': float(weight_ratio),
            'fragility_ratio': float(fragility_ratio),
            'hazmat_flag': float(hazmat_flag),
            'cheapest_container_price': float(cheapest_container_price),
            'avg_viable_container_price': float(avg_viable_container_price),
            'price_spread': float(price_spread),
            'aspect_ratio_variance': float(aspect_ratio_variance),
            'stackability_score': float(stackability_score),
            'container_fit_count': float(container_fit_count),
            'min_containers_needed': float(min_containers_needed),
            'weight_to_volume_ratio': float(weight_to_volume_ratio),
        }
    
    def predict_strategy(self, 
                         products: List[Product], 
                         containers: List[Container]) -> Tuple[str, float, Dict[str, float]]:
        """
        Predict best strategy and return confidence score with feature analysis
        
        Returns:
            Tuple of (strategy_name, confidence_score, feature_dict)
        """
        
        features = self.extract_features(products, containers)
        
        if self.model is None:
            # Fallback to rule-based if model not trained
            strategy, confidence = self._rule_based_fallback(features)
            return strategy, confidence, features
        
        feature_vector = np.array([[features[f] for f in self.feature_names]])
        
        # Get prediction and probability
        strategy_idx = self.model.predict(feature_vector)[0]
        probabilities = self.model.predict_proba(feature_vector)[0]
        
        predicted_strategy = self.strategies[strategy_idx]
        confidence = float(probabilities[strategy_idx])  # Convert numpy.float32 to Python float
        
        return predicted_strategy, confidence, features
    
    def _rule_based_fallback(self, features: Dict[str, float]) -> Tuple[str, float]:
        """Enhanced rule-based strategy selection as fallback"""
        
        # Multi-container scenarios
        if features['utilization_potential'] > 1.2:
            return 'aggressive', 0.85
        
        # High fragility or price sensitivity
        if features['fragility_ratio'] > 0.3 or features['price_spread'] > 0.5:
            return 'best_fit', 0.80
        
        # Complex size distribution
        if features['size_diversity'] > 10 or features['aspect_ratio_variance'] > 5:
            return 'large_first', 0.75
        
        # Weight-constrained orders
        if features['weight_ratio'] > 0.8:
            return 'best_fit', 0.78
        
        # High utilization potential but single container viable
        if features['utilization_potential'] > 0.85:
            return 'greedy', 0.82
        
        # Default case
        return 'greedy', 0.70
    
    def train_model(self, training_data: pd.DataFrame) -> bool:
        """Train the XGBoost model on historical data"""
        try:
            # Try XGBoost first
            import xgboost as xgb
            
            X = training_data[self.feature_names]
            y = training_data['best_strategy'].map({s: i for i, s in enumerate(self.strategies)})
            
            self.model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                eval_metric='mlogloss'
            )
            self.model.fit(X, y)
            
            # Save model
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(self.model, self.model_path)
            
            print("✅ XGBoost model trained and saved successfully")
            return True
            
        except ImportError:
            # Fallback to RandomForest if XGBoost not installed
            print("⚠️ XGBoost not available, using RandomForest")
            
            X = training_data[self.feature_names]
            y = training_data['best_strategy'].map({s: i for i, s in enumerate(self.strategies)})
            
            self.model = RandomForestClassifier(
                n_estimators=100, 
                max_depth=10, 
                random_state=42,
                class_weight='balanced'
            )
            self.model.fit(X, y)
            
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(self.model, self.model_path)
            
            print("✅ RandomForest model trained and saved successfully")
            return True
        
        except Exception as e:
            print(f"❌ Model training failed: {e}")
            return False
    
    def load_model(self):
        """Load trained model from disk"""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                print(f"✅ Model loaded from {self.model_path}")
        except Exception as e:
            print(f"⚠️ Failed to load model: {e}")
            self.model = None
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores for model interpretability"""
        if self.model is None:
            return {}
        
        if hasattr(self.model, 'feature_importances_'):
            importance = dict(zip(self.feature_names, self.model.feature_importances_))
            return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
        return {}
    
    def generate_training_data(self, 
                               products_list: List[List[Product]], 
                               containers: List[Container],
                               strategies_to_test: List[str] = None) -> pd.DataFrame:
        """
        Generate training data by running all strategies on sample orders
        
        Args:
            products_list: List of product lists (different orders)
            containers: Available containers
            strategies_to_test: Strategies to evaluate (default: all)
        
        Returns:
            DataFrame with features and best_strategy labels
        """
        if strategies_to_test is None:
            strategies_to_test = self.strategies
        
        training_records = []
        
        for i, products in enumerate(products_list):
            print(f"Processing order {i+1}/{len(products_list)}")
            
            # Extract features for this order
            features = self.extract_features(products, containers)
            
            # Test all strategies and find the best one
            strategy_results = {}
            
            for strategy in strategies_to_test:
                try:
                    # This would need to be implemented to actually run the strategies
                    # For now, we'll simulate results
                    if strategy == 'greedy':
                        score = self._simulate_greedy_score(features)
                    elif strategy == 'best_fit':
                        score = self._simulate_best_fit_score(features)
                    elif strategy == 'large_first':
                        score = self._simulate_large_first_score(features)
                    elif strategy == 'aggressive':
                        score = self._simulate_aggressive_score(features)
                    else:
                        score = 0.5
                    
                    strategy_results[strategy] = score
                    
                except Exception as e:
                    print(f"Strategy {strategy} failed: {e}")
                    strategy_results[strategy] = 0.0
            
            # Find best strategy
            best_strategy = max(strategy_results.items(), key=lambda x: x[1])[0]
            
            # Add to training data
            record = features.copy()
            record['best_strategy'] = best_strategy
            record['order_id'] = f"train_{i}"
            
            training_records.append(record)
        
        return pd.DataFrame(training_records)
    
    def _simulate_greedy_score(self, features: Dict[str, float]) -> float:
        """Simulate greedy strategy performance"""
        score = 0.7  # Base score
        if features['utilization_potential'] < 0.9:
            score += 0.2
        if features['fragility_ratio'] < 0.2:
            score += 0.1
        return min(1.0, score)
    
    def _simulate_best_fit_score(self, features: Dict[str, float]) -> float:
        """Simulate best_fit strategy performance"""
        score = 0.6  # Base score
        if features['fragility_ratio'] > 0.3:
            score += 0.3
        if features['price_spread'] > 0.4:
            score += 0.2
        return min(1.0, score)
    
    def _simulate_large_first_score(self, features: Dict[str, float]) -> float:
        """Simulate large_first strategy performance"""
        score = 0.65  # Base score
        if features['size_diversity'] > 8:
            score += 0.25
        if features['aspect_ratio_variance'] > 3:
            score += 0.15
        return min(1.0, score)
    
    def _simulate_aggressive_score(self, features: Dict[str, float]) -> float:
        """Simulate aggressive strategy performance"""
        score = 0.5  # Base score
        if features['utilization_potential'] > 1.1:
            score += 0.4
        if features['min_containers_needed'] > 2:
            score += 0.2
        return min(1.0, score)


# Global instance
strategy_predictor = StrategyPredictor()
