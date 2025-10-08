"""
Safe Packing Module with Compatibility Constraints

This module wraps the core packing algorithms with product compatibility rules
to ensure hazardous materials, liquids, electronics, etc. are never packed together.
"""

from typing import List, Optional, Tuple, Dict
from .models import Product, Container, PackedContainer
from .packer import (
    pack, 
    pack_multi_container,
    pack_greedy_max_utilization,
    pack_best_fit,
    pack_largest_first_optimized
)
from .compatibility import CompatibilityChecker


class SafePackingResult:
    """Result of safe packing operation with compatibility info"""
    def __init__(
        self, 
        packed_containers: List[Tuple[Container, PackedContainer]],
        compatibility_groups: List[List[Product]],
        warnings: List[str] = None
    ):
        self.packed_containers = packed_containers
        self.compatibility_groups = compatibility_groups
        self.warnings = warnings or []
        self.success = len(packed_containers) > 0
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary for API response"""
        return {
            "success": self.success,
            "packed_containers": self.packed_containers,
            "compatibility_groups_count": len(self.compatibility_groups),
            "warnings": self.warnings,
            "container_count": len(self.packed_containers),
        }


def pack_with_compatibility_constraints(
    products: List[Product],
    containers: List[Container],
    strategy: str = "auto"
) -> Optional[SafePackingResult]:
    """
    Pack products respecting compatibility constraints
    
    Process:
    1. Group products by compatibility (incompatible items in separate groups)
    2. Try to pack each group in its own container(s)
    3. Optimize across all groups for minimum total cost
    
    Args:
        products: List of products to pack
        containers: Available containers
        strategy: Packing strategy - "auto", "greedy", "best_fit", "large_first"
    
    Returns:
        SafePackingResult with packed containers and compatibility info
    """
    if not products or not containers:
        return None
    
    print(f"\n{'='*60}")
    print(f"🔒 SAFE PACKING WITH COMPATIBILITY CONSTRAINTS")
    print(f"{'='*60}")
    print(f"Total products: {len(products)}")
    print(f"Available containers: {len(containers)}")
    
    # Step 1: Group products by compatibility
    print(f"\n📊 Step 1: Analyzing product compatibility...")
    compatibility_groups = CompatibilityChecker.group_compatible_products(products)
    
    print(f"✅ Created {len(compatibility_groups)} compatible group(s):")
    for i, group in enumerate(compatibility_groups, 1):
        categories = set()
        for product in group:
            cat = CompatibilityChecker.get_product_category(product)
            categories.add(cat.value)
        print(f"   Group {i}: {len(group)} items - Categories: {', '.join(categories)}")
        
        # Show any hazmat items
        hazmat_items = [p for p in group if p.hazmat_class]
        if hazmat_items:
            print(f"            ⚠️  Hazmat: {len(hazmat_items)} items")
        
        fragile_items = [p for p in group if p.fragile]
        if fragile_items:
            print(f"            🔹 Fragile: {len(fragile_items)} items")
    
    # Step 2: Pack each compatible group
    print(f"\n📦 Step 2: Packing each compatible group...")
    all_packed_containers = []
    warnings = []
    
    for group_idx, group in enumerate(compatibility_groups, 1):
        print(f"\n   Packing Group {group_idx} ({len(group)} items)...")
        
        # Select packing strategy
        if strategy == "auto":
            # Auto-select based on group characteristics
            if len(group) <= 3:
                packing_result = pack_single_container_attempt(group, containers)
            elif len(group) > 10:
                packing_result = pack_greedy_max_utilization(group, containers)
            else:
                packing_result = pack_best_fit(group, containers)
        elif strategy == "greedy":
            packing_result = pack_greedy_max_utilization(group, containers)
        elif strategy == "best_fit":
            packing_result = pack_best_fit(group, containers)
        elif strategy == "large_first":
            packing_result = pack_largest_first_optimized(group, containers)
        else:
            packing_result = pack_multi_container(group, containers)
        
        if packing_result:
            all_packed_containers.extend(packing_result)
            print(f"   ✅ Group {group_idx} packed into {len(packing_result)} container(s)")
            
            # Add warning if group requires multiple containers
            if len(packing_result) > 1:
                categories = set(CompatibilityChecker.get_product_category(p).value for p in group)
                warnings.append(
                    f"Group {group_idx} ({', '.join(categories)}) required "
                    f"{len(packing_result)} containers due to size/weight constraints"
                )
        else:
            print(f"   ❌ Failed to pack Group {group_idx}")
            warnings.append(f"Failed to pack group {group_idx} with {len(group)} items")
            return None  # Can't continue if any group fails
    
    # Step 3: Final validation
    print(f"\n🔍 Step 3: Validating packed containers...")
    if not validate_packing_safety(all_packed_containers, products):
        warnings.append("⚠️  Safety validation detected potential issues")
    else:
        print(f"   ✅ All containers passed safety validation")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"✅ SAFE PACKING COMPLETE")
    print(f"{'='*60}")
    print(f"Total containers used: {len(all_packed_containers)}")
    print(f"Compatibility groups: {len(compatibility_groups)}")
    print(f"Warnings: {len(warnings)}")
    if warnings:
        for warning in warnings:
            print(f"   ⚠️  {warning}")
    print(f"{'='*60}\n")
    
    return SafePackingResult(
        packed_containers=all_packed_containers,
        compatibility_groups=compatibility_groups,
        warnings=warnings
    )


def pack_single_container_attempt(
    products: List[Product],
    containers: List[Container]
) -> Optional[List[Tuple[Container, PackedContainer]]]:
    """Try to pack products in a single container"""
    # Sort containers by cost (cheapest first)
    sorted_containers = sorted(containers, key=lambda c: c.price_try or 0)
    
    for container in sorted_containers:
        result = pack(products, container)
        if result and len(result.placements) == len(products):
            # All products fit!
            return [(container, result)]
    
    # If single container fails, try multi-container
    return pack_multi_container(products, sorted_containers)


def validate_packing_safety(
    packed_containers: List[Tuple[Container, PackedContainer]],
    original_products: List[Product]
) -> bool:
    """
    Validate that no incompatible products ended up in the same container
    
    This is a safety check to catch any bugs in the packing algorithm
    """
    # Build product lookup
    product_lookup = {p.sku: p for p in original_products}
    
    all_valid = True
    
    for container_tuple in packed_containers:
        container, packed = container_tuple
        
        # Get all products in this container
        container_products = []
        for placement in packed.placements:
            if placement.sku in product_lookup:
                container_products.append(product_lookup[placement.sku])
        
        # Check if all products are compatible with each other
        if not CompatibilityChecker.can_pack_together(container_products):
            print(f"   ⚠️  WARNING: Container {container.box_id} contains incompatible products!")
            
            # Find which products are incompatible
            for i, p1 in enumerate(container_products):
                for p2 in container_products[i+1:]:
                    if not CompatibilityChecker.are_compatible(p1, p2):
                        reason = CompatibilityChecker.get_incompatibility_reason(p1, p2)
                        print(f"      - {p1.sku} ↔️ {p2.sku}: {reason}")
            
            all_valid = False
    
    return all_valid


def get_packing_report(
    products: List[Product],
    safe_result: SafePackingResult
) -> Dict:
    """
    Generate detailed packing report with compatibility analysis
    """
    report = {
        "total_products": len(products),
        "total_containers": len(safe_result.packed_containers),
        "compatibility_groups": len(safe_result.compatibility_groups),
        "warnings": safe_result.warnings,
        "product_analysis": {},
        "container_details": []
    }
    
    # Analyze products
    hazmat_count = sum(1 for p in products if p.hazmat_class)
    fragile_count = sum(1 for p in products if p.fragile)
    
    categories = {}
    for product in products:
        cat = CompatibilityChecker.get_product_category(product)
        categories[cat.value] = categories.get(cat.value, 0) + 1
    
    report["product_analysis"] = {
        "hazmat_items": hazmat_count,
        "fragile_items": fragile_count,
        "categories": categories
    }
    
    # Container details
    for i, (container, packed) in enumerate(safe_result.packed_containers, 1):
        container_info = {
            "container_number": i,
            "container_id": container.box_id,
            "container_name": container.box_name,
            "items_count": len(packed.placements),
            "items": [p.sku for p in packed.placements],
            "categories_in_container": []
        }
        
        # Get categories in this container
        container_categories = set()
        for placement in packed.placements:
            # Find the original product
            product = next((p for p in products if p.sku == placement.sku), None)
            if product:
                cat = CompatibilityChecker.get_product_category(product)
                container_categories.add(cat.value)
        
        container_info["categories_in_container"] = list(container_categories)
        report["container_details"].append(container_info)
    
    return report


# Convenience functions for specific scenarios

def pack_order_safely(
    products: List[Product],
    containers: List[Container]
) -> Optional[SafePackingResult]:
    """
    Pack an order with safety constraints, using auto strategy selection
    
    This is the recommended function to use for most order packing scenarios
    """
    return pack_with_compatibility_constraints(products, containers, strategy="auto")


def can_products_be_packed_together(products: List[Product]) -> bool:
    """
    Quick check if products can be packed together
    Returns True if all products are mutually compatible
    """
    return CompatibilityChecker.can_pack_together(products)


def explain_incompatibility(product1: Product, product2: Product) -> str:
    """
    Get human-readable explanation of why two products can't be packed together
    """
    return CompatibilityChecker.get_incompatibility_reason(product1, product2)

