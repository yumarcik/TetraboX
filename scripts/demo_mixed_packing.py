#!/usr/bin/env python3
"""
Demonstration: Packing with Incompatible Products

This script shows how the system handles orders with incompatible product types:
- Electronics (batteries)
- Liquids (cosmetics in glass jars)
- Flammable items
- General items
"""

import sys
sys.path.insert(0, '.')

from src.io import load_products_csv, load_containers_csv
from src.safe_packer import pack_order_safely
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
    result = pack_order_safely(mixed_order, containers)
    
    if result and result.success:
        print(f"✅ Successfully packed into {len(result.packed_containers)} container(s)")
        print(f"\n🗂️  {len(result.compatibility_groups)} compatibility group(s) created:")
        
        for i, group in enumerate(result.compatibility_groups, 1):
            categories = set(CompatibilityChecker.get_product_category(p).value for p in group)
            print(f"   Group {i}: {', '.join(categories)} ({len(group)} items)")
        
        print(f"\n💰 Total cost: {sum(c.price_try for c, _ in result.packed_containers):.2f}₺")
        
        # Show each container
        print(f"\n📦 CONTAINER DETAILS:")
        for idx, (container, packed) in enumerate(result.packed_containers, 1):
            print(f"\n   Container {idx}: {container.box_name or container.box_id} ({container.price_try}₺)")
            products_in_container = []
            for placement in packed.placements:
                p = next((prod for prod in mixed_order if prod.sku == placement.sku), None)
                if p:
                    products_in_container.append(p)
                    cat = CompatibilityChecker.get_product_category(p)
                    icon = '🔋' if cat.value == 'electronics' else '💧' if cat.value == 'liquids' else '📌'
                    print(f"      {icon} {p.sku} ({cat.value})")
    
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
    result = pack_order_safely(mixed_order, containers)
    
    if result and result.success:
        print(f"✅ Packed into {len(result.packed_containers)} container(s)")
        print(f"🗂️  {len(result.compatibility_groups)} compatibility group(s)")
    
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
    result = pack_order_safely(mixed_order, containers)
    
    if result and result.success:
        print(f"\n✅ SUCCESS!")
        print(f"   Containers: {len(result.packed_containers)}")
        print(f"   Total cost: {sum(c.price_try for c, _ in result.packed_containers):.2f}₺")
        
        # Calculate average utilization
        total_util = 0
        for container, packed in result.packed_containers:
            container_vol = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm
            used_vol = sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] for p in packed.placements)
            total_util += (used_vol / container_vol * 100) if container_vol > 0 else 0
        
        avg_util = total_util / len(result.packed_containers)
        print(f"   Avg utilization: {avg_util:.1f}%")
        
        if result.warnings:
            print(f"\n⚠️  WARNINGS:")
            for warning in result.warnings:
                print(f"   • {warning}")
    
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

