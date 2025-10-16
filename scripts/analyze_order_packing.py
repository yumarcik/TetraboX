#!/usr/bin/env python3
"""
Order Packing Analysis Tool

This script analyzes order packing using ML-enhanced algorithms with compatibility constraints.
It demonstrates how the ML system selects optimal packing strategies and groups products by compatibility.

Usage:
    python scripts/analyze_order_packing.py --order ORD-12345
    python scripts/analyze_order_packing.py --list
    python scripts/analyze_order_packing.py --top 10

Features:
- ML-based strategy prediction (XGBoost + LightGBM + RandomForest ensemble)
- Product compatibility analysis with safety constraints
- Enhanced packing algorithms (greedy, best-fit, large-first, adaptive)
- Optimized utilization packing with fallback strategies
- Detailed container utilization reports and cost analysis
- Real-time ML confidence scoring and strategy selection
"""

import sys
sys.path.insert(0, '.')

from src.io import load_products_csv, load_containers_csv, load_orders_csv
from src.server import try_aggressive_partial_packing
from src.models import Product, Container, OrderItem
from src.io import load_products_csv, load_containers_csv
from src.ml_strategy_selector import strategy_predictor
from src.packer import (
    pack_greedy_max_utilization, pack_best_fit, pack_largest_first_optimized,
    adaptive_strategy_selection, optimized_utilization_packing
)
from src.compatibility import CompatibilityChecker
from typing import Dict, List
import argparse


def print_separator(char='=', length=80):
    """Print a visual separator"""
    print(char * length)


def print_product_details(product, products_db):
    """Print detailed product information"""
    p = products_db.get(product.sku, product)
    
    # Get category
    category = CompatibilityChecker.get_product_category(p)
    all_categories = CompatibilityChecker.get_all_categories(p)
    
    # Build product info
    info = []
    info.append(f"📦 {p.sku}")
    
    # Add category badges
    category_icons = {
        'electronics': '🔋',
        'liquids': '💧',
        'flammable': '🔥',
        'corrosive': '⚠️',
        'compressed_gas': '💨',
        'aerosol': '💨',
        'fragile': '🔹',
        'general': '📌'
    }
    
    categories_str = ' '.join([f"{category_icons.get(c.value, '•')}{c.value}" 
                               for c in all_categories])
    info.append(f"   Categories: {categories_str}")
    
    # Add hazmat if present
    if p.hazmat_class:
        info.append(f"   ⚠️  Hazmat: {p.hazmat_class}")
    
    # Add dimensions
    info.append(f"   📏 Size: {p.width_mm}×{p.length_mm}×{p.height_mm}mm, {p.weight_g}g")
    
    # Add fragile flag
    if p.fragile:
        info.append(f"   🔹 FRAGILE")
    
    # Add packaging type
    if p.packaging_type:
        info.append(f"   📦 Package: {p.packaging_type}")
    
    return '\n'.join(info)


def analyze_order(order_id: str, orders, products_db, containers):
    """Analyze and display packing for a specific order"""
    
    # Find the order
    order = next((o for o in orders if o.order_id == order_id), None)
    if not order:
        print(f"❌ Order {order_id} not found!")
        return
    
    print_separator('=')
    print(f"📋 ORDER ANALYSIS: {order.order_id}")
    print_separator('=')
    print(f"Customer: {order.customer_name}")
    print(f"Email: {order.customer_email}")
    print(f"Date: {order.order_date}")
    print(f"Status: PACKED")  # Default status since Order model doesn't have status field
    print(f"Total Items: {order.total_items}")
    print(f"Total Price: {order.total_price_try}₺")
    print()
    
    # Get products for this order
    order_products = []
    for item in order.items:
        if item.sku in products_db:
            for _ in range(item.quantity):
                order_products.append(products_db[item.sku])
        else:
            print(f"⚠️  Warning: SKU {item.sku} not found in products database")
    
    if not order_products:
        print("❌ No products found for this order")
        return
    
    # Show all products in order
    print_separator('-')
    print(f"📦 PRODUCTS IN ORDER ({len(order_products)} items)")
    print_separator('-')
    
    for i, product in enumerate(order_products, 1):
        print(f"\n{i}. {print_product_details(product, products_db)}")
    
    print()
    
    # Analyze compatibility
    print_separator('-')
    print("🔍 COMPATIBILITY ANALYSIS")
    print_separator('-')
    
    # Check all pairs
    incompatible_pairs = []
    for i, p1 in enumerate(order_products):
        for p2 in order_products[i+1:]:
            if not CompatibilityChecker.are_compatible(p1, p2):
                reason = CompatibilityChecker.get_incompatibility_reason(p1, p2)
                incompatible_pairs.append((p1.sku, p2.sku, reason))
    
    if incompatible_pairs:
        print(f"\n❌ Found {len(incompatible_pairs)} incompatible product pair(s):")
        for sku1, sku2, reason in incompatible_pairs:
            print(f"   • {sku1} ↔️ {sku2}")
            print(f"     Reason: {reason}")
    else:
        print("\n✅ All products are compatible with each other!")
        print("   → Can potentially pack in single container (if size permits)")
    
    print()
    
    # Show compatibility groups
    print_separator('-')
    print("🗂️  COMPATIBILITY GROUPS")
    print_separator('-')
    
    groups = CompatibilityChecker.group_compatible_products(order_products)
    print(f"\nProducts split into {len(groups)} compatible group(s):\n")
    
    for i, group in enumerate(groups, 1):
        print(f"📁 Group {i}: {len(group)} item(s)")
        
        # Show categories in group
        categories = set()
        hazmat_count = 0
        fragile_count = 0
        
        for p in group:
            cat = CompatibilityChecker.get_product_category(p)
            categories.add(cat.value)
            if p.hazmat_class:
                hazmat_count += 1
            if p.fragile:
                fragile_count += 1
        
        print(f"   Categories: {', '.join(sorted(categories))}")
        if hazmat_count > 0:
            print(f"   ⚠️  Hazmat items: {hazmat_count}")
        if fragile_count > 0:
            print(f"   🔹 Fragile items: {fragile_count}")
        
        print(f"   Items:")
        for p in group:
            print(f"      • {p.sku}")
        print()
    
    # Perform packing
    print_separator('-')
    print("📦 PACKING SIMULATION")
    print_separator('-')
    print("\nAttempting to pack order with safety constraints...\n")
    
    try:
        # Try ML-based packing first
        print("🤖 Using ML-enhanced packing algorithms...")
        
        # Use ML to predict best strategy
        try:
            predicted_strategy, confidence, features = strategy_predictor.predict_strategy(order_products, containers)
            print(f"   ML predicted: {predicted_strategy} (confidence: {confidence:.2f})")
            
            if predicted_strategy == 'greedy':
                result = pack_greedy_max_utilization(order_products, containers)
                strategy_used = 'enhanced_greedy'
            elif predicted_strategy == 'best_fit':
                result = pack_best_fit(order_products, containers)
                strategy_used = 'enhanced_best_fit'
            elif predicted_strategy == 'large_first':
                result = pack_largest_first_optimized(order_products, containers)
                strategy_used = 'enhanced_large_first'
            else:
                result = adaptive_strategy_selection(order_products, containers)
                strategy_used = 'adaptive'
                
        except Exception as e:
            print(f"   ⚠️  ML prediction failed: {e}, using adaptive strategy")
            result = adaptive_strategy_selection(order_products, containers)
            strategy_used = 'adaptive'
        
        # Try optimized utilization as fallback
        if not result:
            print("   🔄 Trying optimized utilization packing...")
            result = optimized_utilization_packing(order_products, containers)
            strategy_used = 'optimized_utilization'
        
        if result:
            print(f"✅ PACKING SUCCESSFUL using {strategy_used} strategy!")
            print(f"\n📊 PACKING SUMMARY:")
            
            # Handle both single container and multi-container results
            if isinstance(result, list) and len(result) > 0:
                # Multi-container result
                print(f"   • Containers used: {len(result)}")
                print(f"   • Strategy: {strategy_used}")
                
                # Show detailed container breakdown
                print()
                print_separator('-')
                print("📦 CONTAINER BREAKDOWN")
                print_separator('-')
                
                total_cost = 0
                total_utilization = 0
                
                for idx, (container, packed_container) in enumerate(result, 1):
                    print(f"\n🎁 Container {idx}: {container.box_name or container.box_id}")
                    print(f"   Shipping: {container.shipping_company or 'Unknown'}")
                    print(f"   Dimensions: {container.inner_w_mm}×{container.inner_l_mm}×{container.inner_h_mm}mm")
                    print(f"   Max Weight: {container.max_weight_g}g")
                    print(f"   Price: {container.price_try}₺")
                    # Calculate utilization
                    container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm
                    used_volume = sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] for p in packed_container.placements)
                    utilization = (used_volume / container_volume * 100) if container_volume > 0 else 0
                    print(f"   Utilization: {utilization:.1f}%")
                    print(f"   Items packed: {len(packed_container.placements)}")
                    
                    # Show items in this container with categories
                    print(f"\n   📦 Items in this container:")
                    container_products = []
                    for placement in packed_container.placements:
                        p = products_db.get(placement.sku)
                        if p:
                            container_products.append(p)
                            cat = CompatibilityChecker.get_product_category(p)
                            cat_icon = {'electronics': '🔋', 'liquids': '💧', 'flammable': '🔥', 
                                       'corrosive': '⚠️', 'fragile': '🔹', 'general': '📌'}.get(cat.value, '•')
                            print(f"      {cat_icon} {placement.sku} ({cat.value})")
                    
                    # Show unique categories in container
                    container_categories = set(CompatibilityChecker.get_product_category(p).value 
                                              for p in container_products)
                    print(f"\n   🏷️  Categories in container: {', '.join(sorted(container_categories))}")
                    
                    # Verify compatibility
                    if CompatibilityChecker.can_pack_together(container_products):
                        print(f"   ✅ All items in this container are compatible")
                    else:
                        print(f"   ⚠️  WARNING: Incompatible items detected!")
                    
                    total_cost += container.price_try or 0
                    total_utilization += utilization
                
                # Final summary
                print()
                print_separator('-')
                print("💰 COST SUMMARY")
                print_separator('-')
                print(f"\nTotal shipping cost: {total_cost:.2f}₺")
                print(f"Average utilization: {total_utilization / len(result):.1f}%")
                print(f"Containers needed: {len(result)}")
                print(f"Strategy used: {strategy_used}")
                
                if len(groups) > 1:
                    print(f"\n💡 OPTIMIZATION NOTE:")
                    print(f"   This order required {len(result)} container(s) due to:")
                    if len(incompatible_pairs) > 0:
                        print(f"   • Product safety constraints ({len(incompatible_pairs)} incompatible pair(s))")
                    print(f"   • {len(groups)} compatibility group(s) identified")
            else:
                print("❌ No valid packing result returned")
        else:
            print("❌ PACKING FAILED - no suitable containers found")
            print("   Try using different containers or check product dimensions")
    
    except Exception as e:
        print(f"❌ Error during packing: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print_separator('=')


def show_order_list(orders):
    """Show list of available orders"""
    print_separator('=')
    print("📋 AVAILABLE ORDERS")
    print_separator('=')
    print()
    
    for order in orders[:20]:  # Show first 20
        # Orders don't have status in current model, use a default icon
        status_icon = '📦'  # Default to packed status
        print(f"{status_icon} {order.order_id:15} | {order.customer_name:30} | "
              f"{order.total_items:3} items | {order.total_price_try:8.2f}₺")
    
    if len(orders) > 20:
        print(f"\n... and {len(orders) - 20} more orders")
    
    print()
    print(f"Total orders: {len(orders)}")
    print()


def main():
    parser = argparse.ArgumentParser(description='Analyze order packing with compatibility constraints')
    parser.add_argument('--order', '-o', help='Order ID to analyze')
    parser.add_argument('--list', '-l', action='store_true', help='List all available orders')
    parser.add_argument('--top', '-t', type=int, default=5, help='Analyze top N orders')
    
    args = parser.parse_args()
    
    # Load data
    print("Loading data...")
    products_list = load_products_csv("data/products.csv")
    products_db = {p.sku: p for p in products_list}
    containers = load_containers_csv("data/container.csv")
    orders = load_orders_csv("data/orders.csv", "data/order_items.csv")
    
    print(f"✅ Loaded {len(products_db)} products, {len(containers)} containers, {len(orders)} orders\n")
    
    if args.list:
        show_order_list(orders)
    elif args.order:
        analyze_order(args.order, orders, products_db, containers)
    else:
        # Analyze top N orders
        print(f"Analyzing top {args.top} orders...\n")
        for i, order in enumerate(orders[:args.top], 1):
            analyze_order(order.order_id, orders, products_db, containers)
            if i < args.top:
                print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()

