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
        
        # 🚀 FAST ML: Smart caching for instant predictions
        self.feature_cache = {}
        self.prediction_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        # 🚀 FAST ML: Lightweight ensemble models
        self.ensemble_models = {}
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
            
            # 🚀 NEW HIGH-IMPACT FEATURES (Fast Implementation)
            # Spatial Intelligence
            'container_volume_ratio',
            'packing_efficiency_estimate',
            'dimensional_harmony_score',
            'corner_utilization_potential',
            'void_space_minimization',
            
            # Advanced Geometric
            'aspect_ratio_consistency',
            'size_distribution_entropy',
            'stacking_compatibility_index',
            'rotation_optimization_score',
            'load_balancing_index',
            
            # Container Intelligence
            'container_flexibility_score',
            'price_per_volume_efficiency',
            'container_utilization_variance',
            'optimal_container_count',
            'multi_container_cost_benefit',
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
        
        # 🚀 FAST ML: Add 15 new high-impact features
        advanced_features = self._extract_advanced_features(products, containers, {
            'total_volume_cm3': total_volume_cm3,
            'total_weight_g': total_weight_g,
            'total_items': total_items,
            'viable_containers': viable_containers,
            'aspect_ratios': aspect_ratios,
            'volumes': volumes,
            'weights': weights
        })
        
        # Combine all features
        all_features = {
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
        
        # Add advanced features
        all_features.update(advanced_features)
        
        return all_features
    
    def predict_strategy(self, 
                         products: List[Product], 
                         containers: List[Container]) -> Tuple[str, float, Dict[str, float]]:
        """
        🚀 FAST ML: Predict best strategy with smart caching
        
        Returns:
            Tuple of (strategy_name, confidence_score, feature_dict)
        """
        
        # Create cache key for instant lookup
        cache_key = self._create_cache_key(products, containers)
        
        # Check prediction cache first (instant return)
        if cache_key in self.prediction_cache:
            self.cache_hits += 1
            return self.prediction_cache[cache_key]
        
        self.cache_misses += 1
        
        # Extract features (with feature caching)
        features = self.extract_features(products, containers)
        
        if self.model is None:
            # Fallback to rule-based if model not trained
            strategy, confidence = self._rule_based_fallback(features)
            result = strategy, confidence, features
            self.prediction_cache[cache_key] = result
            return result
        
        # 🚀 FAST ML: Handle feature compatibility with existing models
        try:
            # Try with all 34 features first (for new models)
            feature_vector = np.array([[features[f] for f in self.feature_names]])
            feature_vector_34 = feature_vector
        except KeyError:
            # Fallback to original 19 features for compatibility
            original_features = [
                'total_items', 'unique_skus', 'total_volume_cm3', 'total_weight_g',
                'avg_item_volume', 'volume_std', 'size_diversity', 'utilization_potential',
                'weight_ratio', 'fragility_ratio', 'hazmat_flag', 'cheapest_container_price',
                'avg_viable_container_price', 'price_spread', 'aspect_ratio_variance',
                'stackability_score', 'container_fit_count', 'min_containers_needed',
                'weight_to_volume_ratio'
            ]
            feature_vector = np.array([[features[f] for f in original_features]])
            feature_vector_34 = None
        
        # 🚀 FAST ML: Use ensemble prediction if available
        if hasattr(self, 'ensemble_models') and self.ensemble_models:
            # Use 34-feature vector for ensemble if available
            if feature_vector_34 is not None:
                predicted_strategy, confidence = self._ensemble_predict(feature_vector_34)
            else:
                predicted_strategy, confidence = self._ensemble_predict(feature_vector)
        else:
            # Fallback to single model with feature compatibility
            try:
                strategy_idx = self.model.predict(feature_vector)[0]
                probabilities = self.model.predict_proba(feature_vector)[0]
                predicted_strategy = self.strategies[strategy_idx]
                confidence = float(probabilities[strategy_idx])
            except ValueError as e:
                if "Feature shape mismatch" in str(e):
                    print(f"⚠️ Model trained with different feature count. Using rule-based fallback.")
                    predicted_strategy, confidence = self._rule_based_fallback(features)
                else:
                    raise e
        
        result = predicted_strategy, confidence, features
        
        # Cache result for future instant access
        self.prediction_cache[cache_key] = result
        
        return result
    
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
        """🚀 FAST ML: Train lightweight ensemble model for maximum speed and accuracy"""
        try:
            X = training_data[self.feature_names]
            y = training_data['best_strategy'].map({s: i for i, s in enumerate(self.strategies)})
            
            # Try to create lightweight ensemble
            ensemble_models = {}
            
            # 1. Fast XGBoost (primary model)
            try:
                import xgboost as xgb
                ensemble_models['xgboost'] = xgb.XGBClassifier(
                    n_estimators=50,  # Reduced for speed
                    max_depth=4,      # Reduced for speed
                    learning_rate=0.15,  # Increased for faster convergence
                    random_state=42,
                    eval_metric='mlogloss',
                    n_jobs=-1  # Use all cores
                )
                ensemble_models['xgboost'].fit(X, y)
                print("✅ XGBoost (fast) trained successfully")
            except ImportError:
                print("⚠️ XGBoost not available")
            
            # 2. Fast LightGBM (secondary model)
            try:
                import lightgbm as lgb
                ensemble_models['lightgbm'] = lgb.LGBMClassifier(
                    n_estimators=50,  # Reduced for speed
                    max_depth=4,      # Reduced for speed
                    learning_rate=0.15,
                    random_state=42,
                    verbose=-1,  # Suppress output
                    n_jobs=-1
                )
                ensemble_models['lightgbm'].fit(X, y)
                print("✅ LightGBM (fast) trained successfully")
            except ImportError:
                print("⚠️ LightGBM not available")
            
            # 3. Fast RandomForest (fallback)
            ensemble_models['randomforest'] = RandomForestClassifier(
                n_estimators=50,  # Reduced for speed
                max_depth=6,      # Reduced for speed
                random_state=42,
                class_weight='balanced',
                n_jobs=-1
            )
            ensemble_models['randomforest'].fit(X, y)
            print("✅ RandomForest (fast) trained successfully")
            
            # Store ensemble models
            self.ensemble_models = ensemble_models
            self.model = ensemble_models['xgboost'] if 'xgboost' in ensemble_models else ensemble_models['randomforest']
            
            # Save models
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(self.ensemble_models, self.model_path.replace('.pkl', '_ensemble.pkl'))
            joblib.dump(self.model, self.model_path)  # Save primary model for compatibility
            
            print(f"✅ Fast ensemble model trained with {len(ensemble_models)} models")
            return True
            
        except Exception as e:
            print(f"❌ Fast ensemble training failed: {e}")
            # Fallback to simple RandomForest
            try:
                X = training_data[self.feature_names]
                y = training_data['best_strategy'].map({s: i for i, s in enumerate(self.strategies)})
                
                self.model = RandomForestClassifier(
                    n_estimators=50, 
                    max_depth=6, 
                    random_state=42,
                    class_weight='balanced',
                    n_jobs=-1
                )
                self.model.fit(X, y)
                
                os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
                joblib.dump(self.model, self.model_path)
                
                print("✅ Fallback RandomForest model trained successfully")
                return True
            except Exception as e2:
                print(f"❌ Fallback training also failed: {e2}")
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
    
    def _extract_advanced_features(self, products: List[Product], containers: List[Container], 
                                  context: Dict) -> Dict[str, float]:
        """🚀 FAST ML: Extract 15 new high-impact features"""
        
        total_volume_cm3 = context['total_volume_cm3']
        total_weight_g = context['total_weight_g']
        total_items = context['total_items']
        viable_containers = context['viable_containers']
        aspect_ratios = context['aspect_ratios']
        volumes = context['volumes']
        weights = context['weights']
        
        # Spatial Intelligence Features
        container_volume_ratio = self._calculate_container_volume_ratio(volumes, viable_containers)
        packing_efficiency_estimate = self._estimate_packing_efficiency(products, viable_containers)
        dimensional_harmony_score = self._calculate_dimensional_harmony_score(products)
        corner_utilization_potential = self._calculate_corner_utilization_potential(products)
        void_space_minimization = self._calculate_void_space_minimization(products, viable_containers)
        
        # Advanced Geometric Features
        aspect_ratio_consistency = self._calculate_aspect_ratio_consistency(aspect_ratios)
        size_distribution_entropy = self._calculate_size_distribution_entropy(volumes)
        stacking_compatibility_index = self._calculate_stacking_compatibility_index(products)
        rotation_optimization_score = self._calculate_rotation_optimization_score(products)
        load_balancing_index = self._calculate_load_balancing_index(weights)
        
        # Container Intelligence Features
        container_flexibility_score = self._calculate_container_flexibility_score(viable_containers)
        price_per_volume_efficiency = self._calculate_price_per_volume_efficiency(viable_containers)
        container_utilization_variance = self._calculate_container_utilization_variance(viable_containers)
        optimal_container_count = self._calculate_optimal_container_count(total_volume_cm3, viable_containers)
        multi_container_cost_benefit = self._calculate_multi_container_cost_benefit(products, viable_containers)
        
        return {
            'container_volume_ratio': float(container_volume_ratio),
            'packing_efficiency_estimate': float(packing_efficiency_estimate),
            'dimensional_harmony_score': float(dimensional_harmony_score),
            'corner_utilization_potential': float(corner_utilization_potential),
            'void_space_minimization': float(void_space_minimization),
            'aspect_ratio_consistency': float(aspect_ratio_consistency),
            'size_distribution_entropy': float(size_distribution_entropy),
            'stacking_compatibility_index': float(stacking_compatibility_index),
            'rotation_optimization_score': float(rotation_optimization_score),
            'load_balancing_index': float(load_balancing_index),
            'container_flexibility_score': float(container_flexibility_score),
            'price_per_volume_efficiency': float(price_per_volume_efficiency),
            'container_utilization_variance': float(container_utilization_variance),
            'optimal_container_count': float(optimal_container_count),
            'multi_container_cost_benefit': float(multi_container_cost_benefit),
        }
    
    def _create_cache_key(self, products: List[Product], containers: List[Container]) -> str:
        """Create fast cache key for predictions"""
        # Create signature from order characteristics
        total_vol = sum(p.width_mm * p.length_mm * p.height_mm for p in products)
        total_weight = sum(p.weight_g for p in products)
        item_count = len(products)
        
        # Container signature
        container_sig = tuple(sorted([c.box_id for c in containers]))
        
        return f"{total_vol:.0f}_{total_weight:.0f}_{item_count}_{hash(container_sig)}"
    
    # 🚀 FAST ML: High-impact feature calculation methods
    
    def _calculate_container_volume_ratio(self, volumes: List[float], containers: List[Container]) -> float:
        """Calculate how well item volumes match container volumes"""
        if not volumes or not containers:
            return 0.0
        
        avg_item_volume = np.mean(volumes)
        container_volumes = [c.inner_w_mm * c.inner_l_mm * c.inner_h_mm / 1000.0 for c in containers]
        avg_container_volume = np.mean(container_volumes)
        
        return min(1.0, avg_item_volume / avg_container_volume) if avg_container_volume > 0 else 0.0
    
    def _estimate_packing_efficiency(self, products: List[Product], containers: List[Container]) -> float:
        """Estimate packing efficiency based on size relationships"""
        if not products or not containers:
            return 0.5
        
        # Calculate how well items fit in containers
        total_item_volume = sum(p.width_mm * p.length_mm * p.height_mm for p in products)
        best_container_volume = max(c.inner_w_mm * c.inner_l_mm * c.inner_h_mm for c in containers)
        
        # Estimate 70% packing efficiency for realistic scenarios
        efficiency = min(0.9, (total_item_volume / best_container_volume) * 0.7) if best_container_volume > 0 else 0.5
        return efficiency
    
    def _calculate_dimensional_harmony_score(self, products: List[Product]) -> float:
        """Calculate how harmoniously item dimensions work together"""
        if len(products) < 2:
            return 1.0
        
        # Calculate dimension ratios
        dimensions = [(p.width_mm, p.length_mm, p.height_mm) for p in products]
        ratios = []
        
        for w, l, h in dimensions:
            if h > 0:
                ratios.extend([w/h, l/h, w/l if l > 0 else 1])
        
        # Lower variance = better harmony
        harmony = 1.0 / (1.0 + np.var(ratios)) if ratios else 1.0
        return min(1.0, harmony)
    
    def _calculate_corner_utilization_potential(self, products: List[Product]) -> float:
        """Calculate potential for efficient corner utilization"""
        if not products:
            return 0.0
        
        # Items with square-ish bases are better for corner packing
        square_items = 0
        for p in products:
            w, l = p.width_mm, p.length_mm
            if w > 0 and l > 0:
                ratio = min(w, l) / max(w, l)
                if ratio > 0.7:  # Close to square
                    square_items += 1
        
        return square_items / len(products)
    
    def _calculate_void_space_minimization(self, products: List[Product], containers: List[Container]) -> float:
        """Calculate potential for minimizing void space"""
        if not products or not containers:
            return 0.0
        
        # Calculate size diversity - more diverse sizes create more voids
        volumes = [p.width_mm * p.length_mm * p.height_mm for p in products]
        size_diversity = max(volumes) / min(volumes) if volumes and min(volumes) > 0 else 1
        
        # Lower diversity = better void minimization
        void_minimization = 1.0 / (1.0 + np.log(size_diversity))
        return min(1.0, void_minimization)
    
    def _calculate_aspect_ratio_consistency(self, aspect_ratios: List[float]) -> float:
        """Calculate consistency of aspect ratios across items"""
        if len(aspect_ratios) < 2:
            return 1.0
        
        # Lower variance = more consistent
        consistency = 1.0 / (1.0 + np.std(aspect_ratios))
        return min(1.0, consistency)
    
    def _calculate_size_distribution_entropy(self, volumes: List[float]) -> float:
        """Calculate entropy of size distribution"""
        if len(volumes) < 2:
            return 0.0
        
        # Normalize volumes
        total_vol = sum(volumes)
        if total_vol == 0:
            return 0.0
        
        normalized = [v / total_vol for v in volumes]
        
        # Calculate entropy
        entropy = -sum(p * np.log2(p) if p > 0 else 0 for p in normalized)
        return entropy / np.log2(len(volumes))  # Normalize to 0-1
    
    def _calculate_stacking_compatibility_index(self, products: List[Product]) -> float:
        """Calculate how well items can be stacked"""
        if not products:
            return 0.0
        
        stackable_items = 0
        for p in products:
            w, l, h = p.width_mm, p.length_mm, p.height_mm
            # Items with large base relative to height are more stackable
            if h > 0 and (w * l) / h > 50:
                stackable_items += 1
        
        return stackable_items / len(products)
    
    def _calculate_rotation_optimization_score(self, products: List[Product]) -> float:
        """Calculate potential for optimization through rotation"""
        if not products:
            return 0.0
        
        # Items with significant dimension differences benefit more from rotation
        rotation_benefit = 0
        for p in products:
            w, l, h = p.width_mm, p.length_mm, p.height_mm
            dims = sorted([w, l, h])
            # Higher ratio between largest and smallest dimension = more rotation benefit
            if dims[0] > 0:
                ratio = dims[2] / dims[0]
                rotation_benefit += min(1.0, (ratio - 1) / 2)
        
        return rotation_benefit / len(products)
    
    def _calculate_load_balancing_index(self, weights: List[float]) -> float:
        """Calculate how balanced the load distribution is"""
        if len(weights) < 2:
            return 1.0
        
        # Lower coefficient of variation = better balance
        mean_weight = np.mean(weights)
        if mean_weight == 0:
            return 1.0
        
        cv = np.std(weights) / mean_weight
        balance = 1.0 / (1.0 + cv)
        return min(1.0, balance)
    
    def _calculate_container_flexibility_score(self, containers: List[Container]) -> float:
        """Calculate flexibility of available containers"""
        if not containers:
            return 0.0
        
        # More container options = more flexibility
        flexibility = min(1.0, len(containers) / 10.0)  # Normalize to 10 containers max
        
        # Add size diversity bonus
        volumes = [c.inner_w_mm * c.inner_l_mm * c.inner_h_mm for c in containers]
        if len(volumes) > 1:
            size_diversity = max(volumes) / min(volumes)
            diversity_bonus = min(0.3, np.log(size_diversity) / 10)
            flexibility += diversity_bonus
        
        return min(1.0, flexibility)
    
    def _calculate_price_per_volume_efficiency(self, containers: List[Container]) -> float:
        """Calculate price efficiency of available containers"""
        if not containers:
            return 0.0
        
        efficiencies = []
        for c in containers:
            volume = c.inner_w_mm * c.inner_l_mm * c.inner_h_mm / 1000.0
            price = c.price_try or 1
            if volume > 0 and price > 0:
                efficiencies.append(volume / price)
        
        if not efficiencies:
            return 0.0
        
        # Normalize efficiency score
        max_efficiency = max(efficiencies)
        avg_efficiency = np.mean(efficiencies)
        
        return min(1.0, avg_efficiency / max_efficiency) if max_efficiency > 0 else 0.0
    
    def _calculate_container_utilization_variance(self, containers: List[Container]) -> float:
        """Calculate variance in container utilization potential"""
        if len(containers) < 2:
            return 0.0
        
        volumes = [c.inner_w_mm * c.inner_l_mm * c.inner_h_mm for c in containers]
        if not volumes:
            return 0.0
        
        # Calculate coefficient of variation
        mean_vol = np.mean(volumes)
        if mean_vol == 0:
            return 0.0
        
        cv = np.std(volumes) / mean_vol
        return min(1.0, cv)
    
    def _calculate_optimal_container_count(self, total_volume_cm3: float, containers: List[Container]) -> float:
        """Calculate optimal number of containers needed"""
        if not containers or total_volume_cm3 == 0:
            return 1.0
        
        # Find best container size for this volume
        best_volume = min(c.inner_w_mm * c.inner_l_mm * c.inner_h_mm / 1000.0 for c in containers)
        
        # Estimate optimal count (with 70% packing efficiency)
        optimal_count = total_volume_cm3 / (best_volume * 0.7)
        
        return min(5.0, max(1.0, optimal_count))  # Cap between 1-5 containers
    
    def _calculate_multi_container_cost_benefit(self, products: List[Product], containers: List[Container]) -> float:
        """Calculate cost benefit of multi-container vs single container"""
        if not products or not containers:
            return 0.0
        
        total_volume = sum(p.width_mm * p.length_mm * p.height_mm for p in products) / 1000.0
        
        # Compare single largest container vs multiple smaller containers
        largest_volume = max(c.inner_w_mm * c.inner_l_mm * c.inner_h_mm for c in containers) / 1000.0
        smallest_volume = min(c.inner_w_mm * c.inner_l_mm * c.inner_h_mm for c in containers) / 1000.0
        
        if largest_volume == 0:
            return 0.0
        
        # If items fit in largest container, single container is better
        if total_volume <= largest_volume * 0.7:
            return 0.2  # Small benefit for single container
        
        # Otherwise, calculate multi-container benefit
        multi_count = np.ceil(total_volume / (smallest_volume * 0.7))
        benefit = min(1.0, multi_count / 3.0)  # Benefit increases with more containers needed
        
        return benefit
    
    def _ensemble_predict(self, feature_vector: np.ndarray) -> Tuple[str, float]:
        """🚀 FAST ML: Lightweight ensemble prediction for maximum accuracy"""
        if not hasattr(self, 'ensemble_models') or not self.ensemble_models:
            # Fallback to single model
            strategy_idx = self.model.predict(feature_vector)[0]
            probabilities = self.model.predict_proba(feature_vector)[0]
            return self.strategies[strategy_idx], float(probabilities[strategy_idx])
        
        # Get predictions from all available models
        predictions = []
        weights = []
        
        # XGBoost (primary, highest weight)
        if 'xgboost' in self.ensemble_models:
            pred = self.ensemble_models['xgboost'].predict_proba(feature_vector)[0]
            predictions.append(pred)
            weights.append(0.5)  # 50% weight
        
        # LightGBM (secondary, medium weight)
        if 'lightgbm' in self.ensemble_models:
            pred = self.ensemble_models['lightgbm'].predict_proba(feature_vector)[0]
            predictions.append(pred)
            weights.append(0.3)  # 30% weight
        
        # RandomForest (fallback, lower weight)
        if 'randomforest' in self.ensemble_models:
            pred = self.ensemble_models['randomforest'].predict_proba(feature_vector)[0]
            predictions.append(pred)
            weights.append(0.2)  # 20% weight
        
        if not predictions:
            # Ultimate fallback
            strategy_idx = self.model.predict(feature_vector)[0]
            probabilities = self.model.predict_proba(feature_vector)[0]
            return self.strategies[strategy_idx], float(probabilities[strategy_idx])
        
        # Weighted ensemble prediction
        weights = np.array(weights)
        weights = weights / weights.sum()  # Normalize weights
        
        ensemble_pred = np.zeros_like(predictions[0])
        for pred, weight in zip(predictions, weights):
            ensemble_pred += pred * weight
        
        # Get final prediction
        strategy_idx = np.argmax(ensemble_pred)
        confidence = float(ensemble_pred[strategy_idx])
        
        return self.strategies[strategy_idx], confidence
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get caching performance statistics"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate_percent': round(hit_rate, 2),
            'total_predictions': total_requests,
            'cached_predictions': len(self.prediction_cache)
        }


# Global instance
strategy_predictor = StrategyPredictor()
