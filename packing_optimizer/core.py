import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict
from packing_optimizer import get_logger



class HazardClass(Enum):
    CORROSIVE_8 = "Corrosive-8"
    FLAMMABLE_LIQUID_3 = "Flammable_Liquid-3"
    LITHIUM_BATTERY = "UN3481-Lithium_Ion_Battery"
    AEROSOL_2 = "Aerosol-2"
    COMPRESSED_GAS_2 = "Compressed_Gas-2"
    NONE = ""


class PackageType(Enum):
    POLY_BAG = "poly_bag"
    RIGID_BOX = "rigid_box"
    KRAFT_ENVELOPE = "kraft_envelope"
    GLASS_JAR = "glass_jar"
    CARDBOARD_BOX = "cardboard_box"
    PLASTIC_BOX = "plastic_box"
    METAL_BOX = "metal_box"
    UNKNOWN = "unknown"


class ExtraPackagingType(Enum):
    BUBBLE_WRAP = "bubble_wrap"
    CORNER_GUARD = "corner_guard"
    FOAM_PROTECTOR = "foam_protector"
    STRETCH_FILM = "stretch_film"
    DOUBLE_CARTON = "double_carton"
    AIR_CUSHION = "air_cushion"
    NONE = ""


@dataclass
class Product:
    product_id: int
    category: str
    brand: str
    model: str
    variant: str
    width_cm: float
    length_cm: float
    height_cm: float
    weight_kg: float
    is_fragile: bool
    package_type: PackageType
    hazard_class: HazardClass
    requires_extra_packaging: bool
    extra_width_cm: float
    extra_length_cm: float
    extra_packaging_type: ExtraPackagingType
    quantity: int
    basket_id: int
    customer_id: int


@dataclass
class Box:
    box_id: int
    box_name: str
    width_cm: float
    length_cm: float
    height_cm: float
    max_weight_kg: float
    box_type: str
    shipping_company: str
    price: float
    available_products: List[str]
    stock: int


class ElectronicsTogetherPacker:
    def __init__(self, safety_margin: float = 1.1, max_electronics_volume: float = 50000,
                 max_electronics_weight: float = 20):
        self.safety_margin = safety_margin
        self.max_electronics_volume = max_electronics_volume  # cm³
        self.max_electronics_weight = max_electronics_weight  # kg
        self.electronics_keywords = ["phone", "laptop", "tablet", "computer", "macbook",
                                     "iphone", "samsung", "xiaomi", "huawei", "oppo",
                                     "vacuum", "kettle", "fryer", "blender", "mixer",
                                     "television", "tv", "monitor", "camera", "drone"]

    def calculate_volume_with_packaging(self, product: Product) -> float:
        """Calculate volume with extra packaging"""
        base_volume = product.width_cm * product.length_cm * product.height_cm

        if product.requires_extra_packaging:
            extra_thickness = 0.01
            packed_width = product.width_cm * (1 + extra_thickness) + product.extra_width_cm
            packed_length = product.length_cm * (1 + extra_thickness) + product.extra_length_cm
            packed_height = product.height_cm * (1 + extra_thickness)
            return packed_width * packed_length * packed_height

        return base_volume

    def is_electronics_product(self, product: Product) -> bool:
        """Electronics detection"""
        product_info = f"{product.brand} {product.model} {product.variant}".lower()

        # Category-based detection
        if product.category in ["Electronics", "Appliance", "Electrical"]:
            return True

        # Keyword-based detection
        if any(keyword in product_info for keyword in self.electronics_keywords):
            return True

        return False

    def can_products_be_packed_together(self, product1: Product, product2: Product) -> bool:
        """Check if two products can be packed together"""

        # 1. Electronics can be packed together
        p1_electronics = self.is_electronics_product(product1)
        p2_electronics = self.is_electronics_product(product2)

        # ALLOW electronics to be packed together
        if p1_electronics and p2_electronics:
            return True

        # 2. Non-electronics compatibility rules
        if not p1_electronics and not p2_electronics:
            # Different hazard classes cannot be packed together
            if (product1.hazard_class != HazardClass.NONE and
                    product2.hazard_class != HazardClass.NONE and
                    product1.hazard_class != product2.hazard_class):
                return False

            # Fragile and heavy items should be separated
            if (product1.is_fragile and product2.weight_kg > 5) or \
                    (product2.is_fragile and product1.weight_kg > 5):
                return False

            return True

        # 3. Electronics CANNOT be packed with non-electronics
        return False

    def find_optimal_box_for_group(self, products: List[Product], available_boxes: List[Box],
                                   shipping_company: Optional[str] = None) -> Optional[Box]:
        """Find the optimal box for a product group, optionally filtered by shipping company"""
        total_volume = sum(self.calculate_volume_with_packaging(p) * p.quantity for p in products)
        total_weight = sum(p.weight_kg * p.quantity for p in products)

        suitable_boxes = []
        for box in available_boxes:
            # Filter by shipping company if specified
            if shipping_company and box.shipping_company != shipping_company:
                continue

            # Check box compatibility
            box_compatible = True
            for product in products:
                # 2D boxes cannot hold 3D products
                if pd.isna(box.height_cm) and product.height_cm > 2:
                    box_compatible = False
                    break

                # Check if box is designed for specific products
                if box.available_products:
                    product_name = f"{product.brand} {product.model}".lower()
                    available_names = [ap.lower() for ap in box.available_products if ap]
                    if not any(avail_name in product_name for avail_name in available_names):
                        box_compatible = False
                        break

            if not box_compatible:
                continue

            # Check volume and weight capacity
            box_height = box.height_cm if not pd.isna(box.height_cm) else 2
            box_volume = box.width_cm * box.length_cm * box_height

            if (box_volume >= total_volume * self.safety_margin and
                    box.max_weight_kg >= total_weight * self.safety_margin):
                suitable_boxes.append(box)

        # Return the smallest suitable box
        if suitable_boxes:
            return min(suitable_boxes,
                       key=lambda x: x.width_cm * x.length_cm * (x.height_cm if not pd.isna(x.height_cm) else 2))

        return None

    def group_electronics_products(self, electronics_products: List[Product]) -> List[List[Product]]:
        """Group electronics products based on volume and weight constraints"""
        if not electronics_products:
            return []

        groups = []
        current_group = []
        current_volume = 0
        current_weight = 0

        for product in electronics_products:
            product_volume = self.calculate_volume_with_packaging(product) * product.quantity
            product_weight = product.weight_kg * product.quantity

            # Check if product exceeds limits on its own
            if (product_volume > self.max_electronics_volume or
                    product_weight > self.max_electronics_weight):
                # Product is too big/heavy, put it in its own box
                if current_group:
                    groups.append(current_group)
                    current_group = []
                    current_volume = 0
                    current_weight = 0
                groups.append([product])
                continue

            # Check if adding this product would exceed limits
            if (current_volume + product_volume > self.max_electronics_volume or
                    current_weight + product_weight > self.max_electronics_weight):
                # Current group is full, start a new one
                if current_group:
                    groups.append(current_group)
                current_group = [product]
                current_volume = product_volume
                current_weight = product_weight
            else:
                # Add to current group
                current_group.append(product)
                current_volume += product_volume
                current_weight += product_weight

        # Add the last group
        if current_group:
            groups.append(current_group)

        return groups

    def group_products_together(self, products: List[Product]) -> List[List[Product]]:
        """Group products with electronics together, considering size/weight limits"""
        electronics_products = []
        non_electronics_products = []

        # Separate electronics from non-electronics
        for product in products:
            if self.is_electronics_product(product):
                electronics_products.append(product)
            else:
                non_electronics_products.append(product)

        groups = []

        # 1. Group electronics products (may be multiple groups based on size/weight)
        electronics_groups = self.group_electronics_products(electronics_products)
        groups.extend(electronics_groups)

        # 2. Group non-electronics products optimally
        current_group = []
        for ne_product in non_electronics_products:
            can_add_to_current = True

            # Check compatibility with current group
            for existing_product in current_group:
                if not self.can_products_be_packed_together(ne_product, existing_product):
                    can_add_to_current = False
                    break

            if can_add_to_current:
                current_group.append(ne_product)
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [ne_product]

        # Add the last group
        if current_group:
            groups.append(current_group)

        return groups

    def optimize_packaging_for_company(self, products: List[Product], available_boxes: List[Box],
                                       shipping_company: str) -> Optional[Dict]:
        """Optimize packaging for a specific shipping company"""
        product_groups = self.group_products_together(products)

        packaging_result = {
            "total_boxes": len(product_groups),
            "boxes": [],
            "requires_multiple_shipments": len(product_groups) > 1,
            "total_volume": 0,
            "total_weight": 0,
            "total_cost": 0,
            "electronics_boxes": 0,
            "non_electronics_boxes": 0,
            "shipping_company": shipping_company,
            "feasible": True
        }

        for group in product_groups:
            optimal_box = self.find_optimal_box_for_group(group, available_boxes, shipping_company)

            if not optimal_box:
                # No suitable box found for this group with this company
                packaging_result["feasible"] = False
                return None

            group_volume = sum(self.calculate_volume_with_packaging(p) * p.quantity for p in group)
            group_weight = sum(p.weight_kg * p.quantity for p in group)

            is_electronics_group = all(self.is_electronics_product(p) for p in group)

            box_info = {
                "box": optimal_box,
                "products": group,
                "total_volume": group_volume,
                "total_weight": group_weight,
                "is_electronics": is_electronics_group,
                "utilization": group_volume / (optimal_box.width_cm * optimal_box.length_cm *
                                               (optimal_box.height_cm if not pd.isna(optimal_box.height_cm) else 2))
            }

            packaging_result["boxes"].append(box_info)
            packaging_result["total_volume"] += group_volume
            packaging_result["total_weight"] += group_weight
            packaging_result["total_cost"] += optimal_box.price

            if is_electronics_group:
                packaging_result["electronics_boxes"] += 1
            else:
                packaging_result["non_electronics_boxes"] += 1

        return packaging_result

    def find_best_shipping_company(self, products: List[Product], available_boxes: List[Box]) -> Dict:
        """Find the best shipping company that can handle the entire order"""
        # Get all unique shipping companies
        shipping_companies = list(set(box.shipping_company for box in available_boxes))

        best_solution = None
        best_company = None

        for company in shipping_companies:
            solution = self.optimize_packaging_for_company(products, available_boxes, company)

            if solution and solution["feasible"]:
                if best_solution is None or solution["total_cost"] < best_solution["total_cost"]:
                    best_solution = solution
                    best_company = company

        if best_solution:
            return best_solution
        else:
            # Fallback: if no single company can handle all, use mixed companies (but this shouldn't happen)
            return self.optimize_packaging(products, available_boxes)

    def optimize_packaging(self, products: List[Product], available_boxes: List[Box]) -> Dict:
        """Fallback method if no single company can handle all packages"""
        product_groups = self.group_products_together(products)

        packaging_result = {
            "total_boxes": len(product_groups),
            "boxes": [],
            "requires_multiple_shipments": len(product_groups) > 1,
            "total_volume": 0,
            "total_weight": 0,
            "total_cost": 0,
            "electronics_boxes": 0,
            "non_electronics_boxes": 0,
            "shipping_company": "MIXED",
            "feasible": True
        }

        for group in product_groups:
            optimal_box = self.find_optimal_box_for_group(group, available_boxes)

            if optimal_box:
                group_volume = sum(self.calculate_volume_with_packaging(p) * p.quantity for p in group)
                group_weight = sum(p.weight_kg * p.quantity for p in group)

                is_electronics_group = all(self.is_electronics_product(p) for p in group)

                box_info = {
                    "box": optimal_box,
                    "products": group,
                    "total_volume": group_volume,
                    "total_weight": group_weight,
                    "is_electronics": is_electronics_group,
                    "utilization": group_volume / (optimal_box.width_cm * optimal_box.length_cm *
                                                   (optimal_box.height_cm if not pd.isna(optimal_box.height_cm) else 2))
                }

                packaging_result["boxes"].append(box_info)
                packaging_result["total_volume"] += group_volume
                packaging_result["total_weight"] += group_weight
                packaging_result["total_cost"] += optimal_box.price

                if is_electronics_group:
                    packaging_result["electronics_boxes"] += 1
                else:
                    packaging_result["non_electronics_boxes"] += 1

        return packaging_result


# UTILITY FUNCTIONS
def categorize_box(row):
    name = str(row['box_name']).lower()
    if "envelope" in name:
        return "Envelope"
    elif "bag" in name:
        return "Bag"
    elif "roll" in name or "film" in name:
        return "Roll"
    elif "air" in name or "protective" in name or "bubble" in name:
        return "AirPack/Protective"
    elif "box" in name or "cardboard" in name or "nano" in name or "maxi" in name or "mini" in name:
        return "Box"
    else:
        return "Other"


def estimate_max_weight(row):
    if pd.notna(row['width_cm']) and pd.notna(row['length_cm']):
        height = row['height_cm'] if pd.notna(row['height_cm']) else 2
        volume = row['width_cm'] * row['length_cm'] * height
        if volume < 2000:
            return 2
        elif volume < 10000:
            return 5
        elif volume < 30000:
            return 10
        else:
            return 20
    return 5


def parse_float(value):
    if pd.isna(value) or value == '': return 0.0
    try:
        return float(str(value).replace(',', '.'))
    except:
        return 0.0


def load_products_data(file_path: str) -> List[Product]:
    df = pd.read_csv(file_path)
    products_list = []

    for idx, row in df.iterrows():
        # Hazard class
        hazard_class = HazardClass.NONE
        if pd.notna(row['hazard_class']):
            for hc in HazardClass:
                if hc.value == row['hazard_class']:
                    hazard_class = hc
                    break

        # Package type
        package_type = PackageType.UNKNOWN
        if pd.notna(row['package_type']):
            for pt in PackageType:
                if pt.value == row['package_type']:
                    package_type = pt
                    break

        # Extra packaging type
        extra_packaging_type = ExtraPackagingType.NONE
        if pd.notna(row['extra_type']):
            for ept in ExtraPackagingType:
                if ept.value == row['extra_type']:
                    extra_packaging_type = ept
                    break

        product = Product(
            product_id=row['product_id'],
            category=row['category'],
            brand=row['brand'],
            model=row['model'],
            variant=str(row['variant']) if pd.notna(row['variant']) else "",
            width_cm=parse_float(row['width_cm']),
            length_cm=parse_float(row['length_cm']),
            height_cm=parse_float(row['height_cm_filled']),
            weight_kg=parse_float(row['weight_kg']),
            is_fragile=row['fragile_flag'],
            package_type=package_type,
            hazard_class=hazard_class,
            requires_extra_packaging=row['requires_special_handling'],
            extra_width_cm=parse_float(row['extra_width_cm']),
            extra_length_cm=parse_float(row['extra_length_cm']),
            extra_packaging_type=extra_packaging_type,
            quantity=row['quantity'],
            basket_id=row['basket_id'],
            customer_id=row['customer_id']
        )
        products_list.append(product)

    return products_list


def load_boxes_data(file_path: str) -> List[Box]:
    df = pd.read_excel(file_path)
    boxes_list = []

    for idx, row in df.iterrows():
        available_products = []
        if pd.notna(row['Available Products']):
            available_products = [p.strip() for p in str(row['Available Products']).split(',')]

        box = Box(
            box_id=idx + 1,
            box_name=row['box_name'],
            width_cm=row['width_cm'] if pd.notna(row['width_cm']) else 0,
            length_cm=row['length_cm'] if pd.notna(row['length_cm']) else 0,
            height_cm=row['height_cm'] if pd.notna(row['height_cm']) else np.nan,
            max_weight_kg=estimate_max_weight(row),
            box_type=categorize_box(row),
            shipping_company=row['shipping_company'],
            price=row['price'],
            available_products=available_products,
            stock=row['Stok'] if pd.notna(row['Stok']) else 50
        )
        boxes_list.append(box)

    return boxes_list


def main(products_path: str,
         boxes_path: str,
         max_elec_volume: float = 50000,
         max_elec_weight: float = 20):
    """
    Works with paths and parameters provided from the command line.
    Processes all baskets.
    """
    logger = get_logger()

    logger.info("📦 OPTIMAL SHIPPING COMPANY SELECTION SYSTEM")
    logger.info("🎯 PRIMARY RULE: ALL PACKAGES SAME SHIPPING COMPANY")
    logger.info("📱 Electronics grouped together (may split if too big/heavy)")

    try:
        logger.info("Loading data...")
        products = load_products_data(products_path)
        boxes = load_boxes_data(boxes_path)
        logger.info("✅ %d products, ✅ %d boxes", len(products), len(boxes))

        packer = ElectronicsTogetherPacker(
            max_electronics_volume=max_elec_volume,
            max_electronics_weight=max_elec_weight
        )

        basket_ids = sorted(set(p.basket_id for p in products))
        logger.info("🔍 Found %d baskets", len(basket_ids))

        # List to store rows for CSV
        all_rows = []

        # Process all baskets
        for i, basket_id in enumerate(basket_ids, start=1):
            basket_products = [p for p in products if p.basket_id == basket_id]
            electronics_count = sum(1 for p in basket_products if packer.is_electronics_product(p))

            print(f"\n🛒 Basket {i} (ID: {basket_id}): {len(basket_products)} products")
            print(f"   📱 Electronics detected: {electronics_count}")

            # Find best shipping company for the entire order
            result = packer.find_best_shipping_company(basket_products, boxes)
            if not result:
                print("   ⚠️ No feasible solution for any single company. Trying MIXED strategy...")
                result = packer.optimize_packaging(basket_products, boxes)

            print(f"   📦 Total boxes required: {result['total_boxes']}")
            print(f"   🔌 Electronics boxes: {result['electronics_boxes']}")
            print(f"   📦 Non-electronics boxes: {result['non_electronics_boxes']}")
            print(f"   💰 Total cost: {result['total_cost']:.2f} TL")
            print(f"   🚚 Shipping company: {result['shipping_company']}")
            print(f"   📦 Multiple shipments: {'Yes' if result['requires_multiple_shipments'] else 'No'}")

            # Show box details and add them to the CSV rows
            for j, box_info in enumerate(result['boxes'], start=1):
                box = box_info['box']
                utilization = box_info['utilization']
                product_ids = [p.product_id for p in box_info['products']]
                categories = list(set(p.category for p in box_info['products']))
                box_type = "Electronics" if box_info['is_electronics'] else "Regular"

                row = {
                    "basket_id": basket_id,
                    "box_number": j,
                    "box_name": box.box_name,
                    "box_type": box_type,
                    "company": box.shipping_company,
                    "price": box.price,
                    "utilization": utilization,
                    "product_ids": str(product_ids),
                    "categories": str(categories)
                }
                all_rows.append(row)

        # Create DataFrame and save as CSV
        df_output = pd.DataFrame(all_rows)
        output_path = "packing_optimizer/data/all_baskets_details.csv"
        df_output.to_csv(output_path, index=False)
        logger.info("✅ CSV saved to %s", output_path)
        print(f"\n✅ CSV saved to {output_path}")

    except Exception as e:
        logger.exception("Error: %s", e)
        import traceback
        traceback.print_exc()
