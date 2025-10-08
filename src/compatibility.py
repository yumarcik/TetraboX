"""
Product Compatibility and Constraint System for Safe Packing

This module defines rules for which products can/cannot be packed together
based on safety, regulatory, and quality considerations.
"""

from typing import List, Set, Dict, Tuple
from .models import Product
from enum import Enum


class ProductCategory(Enum):
    """Product category classifications"""
    ELECTRONICS = "electronics"
    LIQUIDS = "liquids"
    CORROSIVE = "corrosive"
    FLAMMABLE = "flammable"
    COMPRESSED_GAS = "compressed_gas"
    AEROSOL = "aerosol"
    FRAGILE = "fragile"
    FOOD = "food"
    TEXTILE = "textile"
    GENERAL = "general"


class CompatibilityChecker:
    """Check product compatibility for safe packing"""
    
    # Define incompatible product combinations (safety rules)
    INCOMPATIBLE_PAIRS = {
        frozenset([ProductCategory.ELECTRONICS, ProductCategory.LIQUIDS]),
        frozenset([ProductCategory.ELECTRONICS, ProductCategory.CORROSIVE]),
        frozenset([ProductCategory.ELECTRONICS, ProductCategory.FLAMMABLE]),
        frozenset([ProductCategory.LIQUIDS, ProductCategory.ELECTRONICS]),
        frozenset([ProductCategory.FLAMMABLE, ProductCategory.COMPRESSED_GAS]),
        frozenset([ProductCategory.FLAMMABLE, ProductCategory.AEROSOL]),
        frozenset([ProductCategory.CORROSIVE, ProductCategory.FOOD]),
        frozenset([ProductCategory.LIQUIDS, ProductCategory.FOOD]),
        frozenset([ProductCategory.COMPRESSED_GAS, ProductCategory.FRAGILE]),
        frozenset([ProductCategory.AEROSOL, ProductCategory.FOOD]),
    }
    
    # Hazmat class to category mapping
    HAZMAT_CATEGORY_MAP = {
        "UN3481-Lithium_Ion_Battery": ProductCategory.ELECTRONICS,
        "UN3480-Lithium_Ion_Battery": ProductCategory.ELECTRONICS,
        "Flammable_Liquid-3": ProductCategory.FLAMMABLE,
        "Flammable_Solid-4": ProductCategory.FLAMMABLE,
        "Corrosive-8": ProductCategory.CORROSIVE,
        "Compressed_Gas-2": ProductCategory.COMPRESSED_GAS,
        "Aerosol-2": ProductCategory.AEROSOL,
    }
    
    # Packaging type hints for categorization
    PACKAGING_TYPE_HINTS = {
        "glass_jar": ProductCategory.LIQUIDS,
        "plastic_bottle": ProductCategory.LIQUIDS,
        "metal_box": ProductCategory.ELECTRONICS,
        "anti_static_bag": ProductCategory.ELECTRONICS,
    }
    
    @classmethod
    def get_product_category(cls, product: Product) -> ProductCategory:
        """
        Determine the primary category of a product based on its attributes
        
        Priority:
        1. Hazmat class (highest priority - safety critical)
        2. Fragile flag
        3. Packaging type hints
        4. Default to general
        """
        # Check hazmat class first (safety critical)
        if product.hazmat_class:
            hazmat_category = cls.HAZMAT_CATEGORY_MAP.get(product.hazmat_class)
            if hazmat_category:
                return hazmat_category
        
        # Check if fragile
        if product.fragile:
            return ProductCategory.FRAGILE
        
        # Check packaging type for hints
        if product.packaging_type:
            packaging_category = cls.PACKAGING_TYPE_HINTS.get(product.packaging_type)
            if packaging_category:
                return packaging_category
        
        return ProductCategory.GENERAL
    
    @classmethod
    def get_all_categories(cls, product: Product) -> Set[ProductCategory]:
        """
        Get all applicable categories for a product
        (a product can belong to multiple categories)
        """
        categories = set()
        
        # Add hazmat-based category
        if product.hazmat_class:
            hazmat_category = cls.HAZMAT_CATEGORY_MAP.get(product.hazmat_class)
            if hazmat_category:
                categories.add(hazmat_category)
        
        # Add fragile if applicable
        if product.fragile:
            categories.add(ProductCategory.FRAGILE)
        
        # Add packaging-based category
        if product.packaging_type:
            packaging_category = cls.PACKAGING_TYPE_HINTS.get(product.packaging_type)
            if packaging_category:
                categories.add(packaging_category)
        
        # If no specific categories, it's general
        if not categories:
            categories.add(ProductCategory.GENERAL)
        
        return categories
    
    @classmethod
    def are_compatible(cls, product1: Product, product2: Product) -> bool:
        """
        Check if two products can be safely packed together
        
        Returns:
            True if products are compatible, False otherwise
        """
        categories1 = cls.get_all_categories(product1)
        categories2 = cls.get_all_categories(product2)
        
        # Check all category combinations
        for cat1 in categories1:
            for cat2 in categories2:
                pair = frozenset([cat1, cat2])
                if pair in cls.INCOMPATIBLE_PAIRS:
                    return False
        
        return True
    
    @classmethod
    def can_pack_together(cls, products: List[Product]) -> bool:
        """
        Check if a list of products can all be packed together safely
        
        Returns:
            True if all products are mutually compatible, False otherwise
        """
        if len(products) <= 1:
            return True
        
        # Check each pair
        for i in range(len(products)):
            for j in range(i + 1, len(products)):
                if not cls.are_compatible(products[i], products[j]):
                    return False
        
        return True
    
    @classmethod
    def get_incompatibility_reason(cls, product1: Product, product2: Product) -> str:
        """
        Get human-readable reason why two products are incompatible
        """
        categories1 = cls.get_all_categories(product1)
        categories2 = cls.get_all_categories(product2)
        
        for cat1 in categories1:
            for cat2 in categories2:
                pair = frozenset([cat1, cat2])
                if pair in cls.INCOMPATIBLE_PAIRS:
                    return f"Cannot pack {cat1.value} with {cat2.value} (safety regulation)"
        
        return "Products are compatible"
    
    @classmethod
    def group_compatible_products(cls, products: List[Product]) -> List[List[Product]]:
        """
        Group products into compatible clusters for safe packing
        
        Uses greedy algorithm to minimize number of containers needed
        while respecting compatibility constraints.
        
        Returns:
            List of product groups where each group is mutually compatible
        """
        if not products:
            return []
        
        groups: List[List[Product]] = []
        remaining = products.copy()
        
        while remaining:
            # Start a new group with first remaining product
            current_group = [remaining.pop(0)]
            
            # Try to add more products to this group
            i = 0
            while i < len(remaining):
                product = remaining[i]
                
                # Check if product is compatible with all in current group
                if all(cls.are_compatible(product, p) for p in current_group):
                    current_group.append(product)
                    remaining.pop(i)
                else:
                    i += 1
            
            groups.append(current_group)
        
        return groups
    
    @classmethod
    def get_compatibility_matrix(cls, products: List[Product]) -> Dict[Tuple[str, str], bool]:
        """
        Generate a compatibility matrix for a set of products
        
        Returns:
            Dictionary mapping (sku1, sku2) -> compatibility boolean
        """
        matrix = {}
        
        for i, p1 in enumerate(products):
            for j, p2 in enumerate(products):
                if i != j:
                    key = (p1.sku, p2.sku)
                    matrix[key] = cls.are_compatible(p1, p2)
        
        return matrix
    
    @classmethod
    def get_product_info(cls, product: Product) -> Dict:
        """
        Get detailed compatibility information for a product
        """
        primary_category = cls.get_product_category(product)
        all_categories = cls.get_all_categories(product)
        
        # Find what this product is incompatible with
        incompatible_with = set()
        for cat in all_categories:
            for pair in cls.INCOMPATIBLE_PAIRS:
                if cat in pair:
                    incompatible_with.update(pair - {cat})
        
        return {
            "sku": product.sku,
            "primary_category": primary_category.value,
            "all_categories": [cat.value for cat in all_categories],
            "hazmat_class": product.hazmat_class,
            "fragile": product.fragile,
            "packaging_type": product.packaging_type,
            "incompatible_with": [cat.value for cat in incompatible_with],
        }


# Example usage and testing
if __name__ == "__main__":
    # Test example
    electronics = Product(
        sku="PHONE-001",
        width_mm=150, length_mm=75, height_mm=8,
        weight_g=180,
        hazmat_class="UN3481-Lithium_Ion_Battery"
    )
    
    liquid = Product(
        sku="SHAMPOO-001",
        width_mm=80, length_mm=80, height_mm=200,
        weight_g=500,
        packaging_type="glass_jar"
    )
    
    textile = Product(
        sku="SHIRT-001",
        width_mm=300, length_mm=200, height_mm=50,
        weight_g=200
    )
    
    checker = CompatibilityChecker()
    
    print(f"Electronics + Liquid compatible? {checker.are_compatible(electronics, liquid)}")
    print(f"Electronics + Textile compatible? {checker.are_compatible(electronics, textile)}")
    print(f"Liquid + Textile compatible? {checker.are_compatible(liquid, textile)}")
    
    if not checker.are_compatible(electronics, liquid):
        print(f"Reason: {checker.get_incompatibility_reason(electronics, liquid)}")

