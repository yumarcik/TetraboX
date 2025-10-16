#!/usr/bin/env python3
"""
ML-Enhanced Packing Demonstration Script

This script demonstrates how TetraboX uses ML-enhanced algorithms to handle 
product compatibility constraints and automatically separates incompatible 
products into different containers.

Features demonstrated:
- ML-based strategy prediction (XGBoost + LightGBM + RandomForest ensemble)
- Automatic compatibility checking with safety constraints
- Enhanced packing algorithms (greedy, best-fit, large-first, adaptive)
- Product category-based separation (electronics, liquids, flammable, general)
- Optimized utilization packing with fallback strategies
- Real-time ML confidence scoring and strategy selection

Usage:
    python scripts/demo_mixed_packing.py
"""

import sys
sys.path.insert(0, '.')

from src.io import load_products_csv, load_containers_csv
from src.server import try_aggressive_partial_packing
from src.models import Product, Container, OrderItem
from src.io import load_products_csv, load_containers_csv
from src.ml_strategy_selector import strategy_predictor
from src.packer import (
    pack_greedy_max_utilization, pack_best_fit, pack_largest_first_optimized,
    adaptive_strategy_selection, optimized_utilization_packing
)
from src.compatibility import CompatibilityChecker


def print_separator(char='=', length=80):
    print(char * length)


def demo_scenario_1():
    """Electronics + Liquids - Must be separated"""
    print_separator('=')
    print("🧪 DEMO SCENARIO 1: Electronics + Liquids")
    print_separator('=')
    print()
    
    # Load data
    products_list = load_products_csv("data/products.csv")
    products_db = {p.sku: p for p in products_list}
    containers = load_containers_csv("data/container.csv")
    
    # Find products with different categories
    electronics = [p for p in products_list if p.hazmat_class and isinstance(p.hazmat_class, str) and "Lithium" in p.hazmat_class][:2]
    liquids = [p for p in products_list if p.packaging_type and isinstance(p.packaging_type, str) and "glass_jar" in p.packaging_type][:2]
    
    if not electronics:
        print("⚠️  No electronics with batteries found in database")
        return
    if not liquids:
        print("⚠️  No liquid products found in database")
        return
    
    print("📦 ORDER CONTENTS:")
    print()
    for i, p in enumerate(electronics, 1):
        cat = CompatibilityChecker.get_product_category(p)
        print(f"  {i}. 🔋 {p.sku} - {cat.value}")
        print(f"     Hazmat: {p.hazmat_class}")
        print(f"     Size: {p.width_mm}×{p.length_mm}×{p.height_mm}mm\n")
    
    for i, p in enumerate(liquids, len(electronics)+1):
        cat = CompatibilityChecker.get_product_category(p)
        print(f"  {i}. 💧 {p.sku} - {cat.value}")
        print(f"     Packaging: {p.packaging_type}")
        print(f"     Size: {p.width_mm}×{p.length_mm}×{p.height_mm}mm\n")
    
    # Test compatibility
    print("🔍 COMPATIBILITY CHECK:")
    print()
    if not CompatibilityChecker.are_compatible(electronics[0], liquids[0]):
        reason = CompatibilityChecker.get_incompatibility_reason(electronics[0], liquids[0])
        print(f"❌ {electronics[0].sku} ↔️ {liquids[0].sku}")
        print(f"   {reason}\n")
    
    # Pack the order
    print("📦 PACKING WITH SAFETY CONSTRAINTS:")
    print()
    
    mixed_order = electronics + liquids
    
    # Use ML-enhanced packing
    print("🤖 Using ML-enhanced packing algorithms...")
    try:
        predicted_strategy, confidence, features = strategy_predictor.predict_strategy(mixed_order, containers)
        print(f"   ML predicted: {predicted_strategy} (confidence: {confidence:.2f})")
        
        if predicted_strategy == 'greedy':
            result = pack_greedy_max_utilization(mixed_order, containers)
        elif predicted_strategy == 'best_fit':
            result = pack_best_fit(mixed_order, containers)
        elif predicted_strategy == 'large_first':
            result = pack_largest_first_optimized(mixed_order, containers)
        else:
            result = adaptive_strategy_selection(mixed_order, containers)
            
    except Exception as e:
        print(f"   ⚠️  ML prediction failed: {e}, using adaptive strategy")
        result = adaptive_strategy_selection(mixed_order, containers)
    
    # Try optimized utilization as fallback
    if not result:
        print("   🔄 Trying optimized utilization packing...")
        result = optimized_utilization_packing(mixed_order, containers)
    
    if result:
        # Handle both single container and multi-container results
        if isinstance(result, list) and len(result) > 0:
            print(f"✅ Successfully packed into {len(result)} container(s)")
            print(f"\n🗂️  Strategy: ML-enhanced packing")
            
            print(f"\n💰 Total cost: {sum(c.price_try or 0 for c, _ in result):.2f}₺")
            
            # Show each container
            print(f"\n📦 CONTAINER DETAILS:")
            for idx, (container, packed_container) in enumerate(result, 1):
                print(f"\n   Container {idx}: {container.box_name or container.box_id} ({container.price_try or 0}₺)")
                # Calculate utilization
                container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm
                used_volume = sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] for p in packed_container.placements)
                utilization = (used_volume / container_volume * 100) if container_volume > 0 else 0
                print(f"   Utilization: {utilization:.1f}%")
                products_in_container = []
                for placement in packed_container.placements:
                    p = next((prod for prod in mixed_order if prod.sku == placement.sku), None)
                    if p:
                        products_in_container.append(p)
                        cat = CompatibilityChecker.get_product_category(p)
                        icon = '🔋' if cat.value == 'electronics' else '💧' if cat.value == 'liquids' else '📌'
                        print(f"      {icon} {p.sku} ({cat.value})")
        else:
            print("❌ No valid packing result returned")
    else:
        print("❌ Packing failed - no suitable containers found")
    
    print()


def demo_scenario_2():
    """Flammable + Aerosol - Must be separated"""
    print_separator('=')
    print("🧪 DEMO SCENARIO 2: Flammable + Aerosol")
    print_separator('=')
    print()
    
    products_list = load_products_csv("data/products.csv")
    products_db = {p.sku: p for p in products_list}
    containers = load_containers_csv("data/container.csv")
    
    # Find flammable and aerosol products
    flammable = [p for p in products_list if p.hazmat_class and isinstance(p.hazmat_class, str) and "Flammable" in p.hazmat_class][:1]
    aerosol = [p for p in products_list if p.hazmat_class and isinstance(p.hazmat_class, str) and "Aerosol" in p.hazmat_class][:1]
    general = [p for p in products_list if not p.hazmat_class and not p.fragile][:2]
    
    if not flammable or not aerosol:
        print("⚠️  Required product types not found")
        return
    
    print("📦 ORDER CONTENTS:")
    print()
    
    for i, p in enumerate(flammable, 1):
        print(f"  {i}. 🔥 {p.sku} - FLAMMABLE")
        print(f"     Hazmat: {p.hazmat_class}\n")
    
    for i, p in enumerate(aerosol, len(flammable)+1):
        print(f"  {i}. 💨 {p.sku} - AEROSOL")
        print(f"     Hazmat: {p.hazmat_class}\n")
    
    for i, p in enumerate(general, len(flammable)+len(aerosol)+1):
        print(f"  {i}. 📌 {p.sku} - GENERAL\n")
    
    # Test compatibility
    print("🔍 COMPATIBILITY CHECK:")
    print()
    if not CompatibilityChecker.are_compatible(flammable[0], aerosol[0]):
        reason = CompatibilityChecker.get_incompatibility_reason(flammable[0], aerosol[0])
        print(f"❌ {flammable[0].sku} ↔️ {aerosol[0].sku}")
        print(f"   {reason}\n")
    
    # Pack the order
    print("📦 PACKING RESULT:")
    print()
    
    mixed_order = flammable + aerosol + general
    
    # Use ML-enhanced packing
    print("🤖 Using ML-enhanced packing algorithms...")
    try:
        predicted_strategy, confidence, features = strategy_predictor.predict_strategy(mixed_order, containers)
        print(f"   ML predicted: {predicted_strategy} (confidence: {confidence:.2f})")
        
        if predicted_strategy == 'greedy':
            result = pack_greedy_max_utilization(mixed_order, containers)
        elif predicted_strategy == 'best_fit':
            result = pack_best_fit(mixed_order, containers)
        elif predicted_strategy == 'large_first':
            result = pack_largest_first_optimized(mixed_order, containers)
        else:
            result = adaptive_strategy_selection(mixed_order, containers)
            
    except Exception as e:
        print(f"   ⚠️  ML prediction failed: {e}, using adaptive strategy")
        result = adaptive_strategy_selection(mixed_order, containers)
    
    # Try optimized utilization as fallback
    if not result:
        print("   🔄 Trying optimized utilization packing...")
        result = optimized_utilization_packing(mixed_order, containers)
    
    if result:
        if isinstance(result, list) and len(result) > 0:
            print(f"✅ Packed into {len(result)} container(s)")
            print(f"🗂️  Strategy: ML-enhanced packing")
        else:
            print("❌ No valid packing result returned")
    else:
        print("❌ Packing failed - no suitable containers found")
    
    print()


def demo_scenario_3():
    """Large mixed order with multiple product types"""
    print_separator('=')
    print("🧪 DEMO SCENARIO 3: Large Mixed Order")
    print_separator('=')
    print()
    
    products_list = load_products_csv("data/products.csv")
    containers = load_containers_csv("data/container.csv")
    
    # Create a diverse order
    electronics = [p for p in products_list if p.hazmat_class and isinstance(p.hazmat_class, str) and "Lithium" in p.hazmat_class][:2]
    liquids = [p for p in products_list if p.packaging_type and isinstance(p.packaging_type, str) and "glass_jar" in p.packaging_type][:3]
    fragile = [p for p in products_list if p.fragile and not p.hazmat_class][:2]
    general = [p for p in products_list if not p.hazmat_class and not p.fragile][:5]
    
    mixed_order = electronics + liquids + fragile + general
    
    print(f"📦 ORDER WITH {len(mixed_order)} ITEMS:")
    print()
    
    # Show category breakdown
    category_counts = {}
    for p in mixed_order:
        cat = CompatibilityChecker.get_product_category(p)
        category_counts[cat.value] = category_counts.get(cat.value, 0) + 1
    
    print("📊 Product Categories:")
    icons = {'electronics': '🔋', 'liquids': '💧', 'fragile': '🔹', 'general': '📌'}
    for cat, count in sorted(category_counts.items()):
        icon = icons.get(cat, '•')
        print(f"   {icon} {cat}: {count} items")
    
    print()
    
    # Check incompatibilities
    print("🔍 Analyzing compatibility...")
    groups = CompatibilityChecker.group_compatible_products(mixed_order)
    print(f"\n✅ Created {len(groups)} compatibility group(s):")
    for i, group in enumerate(groups, 1):
        categories = set(CompatibilityChecker.get_product_category(p).value for p in group)
        print(f"   Group {i}: {len(group)} items - {', '.join(sorted(categories))}")
    
    print()
    
    # Pack the order
    print("📦 PACKING...")
    
    # Use ML-enhanced packing
    print("🤖 Using ML-enhanced packing algorithms...")
    try:
        predicted_strategy, confidence, features = strategy_predictor.predict_strategy(mixed_order, containers)
        print(f"   ML predicted: {predicted_strategy} (confidence: {confidence:.2f})")
        
        if predicted_strategy == 'greedy':
            result = pack_greedy_max_utilization(mixed_order, containers)
        elif predicted_strategy == 'best_fit':
            result = pack_best_fit(mixed_order, containers)
        elif predicted_strategy == 'large_first':
            result = pack_largest_first_optimized(mixed_order, containers)
        else:
            result = adaptive_strategy_selection(mixed_order, containers)
            
    except Exception as e:
        print(f"   ⚠️  ML prediction failed: {e}, using adaptive strategy")
        result = adaptive_strategy_selection(mixed_order, containers)
    
    # Try optimized utilization as fallback
    if not result:
        print("   🔄 Trying optimized utilization packing...")
        result = optimized_utilization_packing(mixed_order, containers)
    
    if result:
        if isinstance(result, list) and len(result) > 0:
            print(f"\n✅ SUCCESS!")
            print(f"   Containers: {len(result)}")
            print(f"   Strategy: ML-enhanced packing")
            print(f"   Total cost: {sum(c.price_try or 0 for c, _ in result):.2f}₺")
            
            # Calculate average utilization
            total_util = 0
            for container, packed_container in result:
                container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm
                used_volume = sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] for p in packed_container.placements)
                utilization = (used_volume / container_volume * 100) if container_volume > 0 else 0
                total_util += utilization
            
            avg_util = total_util / len(result)
            print(f"   Avg utilization: {avg_util:.1f}%")
        else:
            print("❌ No valid packing result returned")
    else:
        print("❌ Packing failed - no suitable containers found")
    
    print()


def main():
    print()
    print_separator('*')
    print("  TETRABOX SAFE PACKING DEMONSTRATION")
    print("  Showing automatic product compatibility handling")
    print_separator('*')
    print()
    
    try:
        demo_scenario_1()
        demo_scenario_2()
        demo_scenario_3()
        
        print_separator('=')
        print("✅ DEMONSTRATION COMPLETE")
        print_separator('=')
        print()
        print("Key Takeaways:")
        print("  1. Electronics and liquids are automatically separated")
        print("  2. Flammable items and aerosols never mix")
        print("  3. Each compatibility group gets its own container(s)")
        print("  4. System optimizes cost within safety constraints")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

