# Product Compatibility Rules & Safe Packing

## Overview

The TetraboX system now includes **intelligent product compatibility constraints** to ensure safe packing. The system automatically prevents incompatible products from being packed in the same container based on safety regulations and product characteristics.

## 🚨 Incompatibility Rules

The following product combinations are **NEVER** allowed in the same container:

### Critical Safety Rules

| Category 1 | Category 2 | Reason |
|------------|------------|--------|
| **Electronics** (Lithium batteries) | **Liquids** | Fire/short circuit hazard |
| **Electronics** | **Corrosive materials** | Damage to electronics |
| **Electronics** | **Flammable liquids** | Fire/explosion risk |
| **Flammable items** | **Compressed gas** | Explosion risk |
| **Flammable items** | **Aerosols** | Fire propagation |
| **Corrosive materials** | **Food items** | Contamination |
| **Liquids** | **Food items** | Contamination risk |
| **Compressed gas** | **Fragile items** | Pressure/breakage risk |
| **Aerosols** | **Food items** | Contamination |

## 📦 Product Categories

Products are automatically categorized based on their attributes:

### Category Detection Rules

1. **Electronics** - Products with:
   - `hazmat_class` = "UN3481-Lithium_Ion_Battery" or "UN3480-Lithium_Ion_Battery"
   - `packaging_type` = "metal_box" or "anti_static_bag"

2. **Liquids** - Products with:
   - `packaging_type` = "glass_jar" or "plastic_bottle"

3. **Flammable** - Products with:
   - `hazmat_class` = "Flammable_Liquid-3" or "Flammable_Solid-4"

4. **Corrosive** - Products with:
   - `hazmat_class` = "Corrosive-8"

5. **Compressed Gas** - Products with:
   - `hazmat_class` = "Compressed_Gas-2"

6. **Aerosol** - Products with:
   - `hazmat_class` = "Aerosol-2"

7. **Fragile** - Products with:
   - `fragile` = True

8. **General** - Products that don't match any specific category

## 🔄 How It Works

### 1. Product Grouping

When an order is received, the system:

```python
from src.safe_packer import pack_order_safely

# Products are automatically grouped by compatibility
result = pack_order_safely(products, containers)

# Example output:
# Group 1: [Phone, Tablet, Laptop] - Electronics only
# Group 2: [Shampoo, Soap, Lotion] - Liquids only
# Group 3: [T-shirt, Socks, Hat] - General items
```

### 2. Separate Packing

Each compatibility group is packed into its own container(s):
- Group 1 (Electronics) → Container A
- Group 2 (Liquids) → Container B  
- Group 3 (General) → Container C

### 3. Optimization

Within each group, the system applies packing algorithms to:
- Minimize number of containers
- Maximize space utilization
- Reduce total shipping cost

## 💡 Example Scenarios

### ✅ ALLOWED - Same Container

**Scenario 1: Electronics Only**
```
✓ Phone (UN3481 battery)
✓ Laptop (UN3481 battery)
✓ Tablet (UN3481 battery)
```
**Reason:** All electronics, compatible

**Scenario 2: Mixed General Items**
```
✓ T-Shirt (textile)
✓ Book (general)
✓ Toy (general, non-hazmat)
```
**Reason:** No hazmat conflicts

### ❌ BLOCKED - Separate Containers Required

**Scenario 1: Electronics + Liquids**
```
✗ Phone (UN3481 battery)
✗ Shampoo (liquid in glass jar)
```
**Reason:** Battery + liquid = fire hazard
**Solution:** 2 containers minimum

**Scenario 2: Food + Chemicals**
```
✗ Snack bar (food)
✗ Cleaning spray (Corrosive-8)
```
**Reason:** Chemical contamination risk
**Solution:** 2 containers minimum

**Scenario 3: Flammable + Aerosol**
```
✗ Paint thinner (Flammable_Liquid-3)
✗ Hair spray (Aerosol-2)
```
**Reason:** Fire propagation risk
**Solution:** 2 containers minimum

## 🛠️ API Usage

### Pack with Safety Constraints

```python
POST /pack/order/safe

{
  "order_id": "ORD-12345",
  "items": [
    {"sku": "PHONE-001", "quantity": 1},  # Electronics
    {"sku": "SHAMPOO-001", "quantity": 1}, # Liquid
    {"sku": "SHIRT-001", "quantity": 2}    # General
  ]
}
```

**Response:**
```json
{
  "success": true,
  "container_count": 2,
  "compatibility_groups": 3,
  "containers": [
    {
      "container_id": "BOX-A",
      "items": ["PHONE-001"],
      "categories": ["electronics"]
    },
    {
      "container_id": "BOX-B", 
      "items": ["SHAMPOO-001", "SHIRT-001", "SHIRT-001"],
      "categories": ["liquids", "general"]
    }
  ],
  "warnings": []
}
```

### Check Compatibility Before Packing

```python
from src.compatibility import CompatibilityChecker

# Check if two products can be packed together
phone = Product(sku="PHONE-001", hazmat_class="UN3481-Lithium_Ion_Battery", ...)
shampoo = Product(sku="SHAMPOO-001", packaging_type="glass_jar", ...)

compatible = CompatibilityChecker.are_compatible(phone, shampoo)
# Returns: False

reason = CompatibilityChecker.get_incompatibility_reason(phone, shampoo)
# Returns: "Cannot pack electronics with liquids (safety regulation)"
```

## 📊 Data Model Requirements

For the compatibility system to work, your product data should include:

```csv
sku,width_cm,length_cm,height_cm,weight_kg,fragile,package_type,hazard_class
PHONE-001,15,7.5,0.8,0.18,true,metal_box,UN3481-Lithium_Ion_Battery
SHAMPOO-001,8,8,20,0.5,true,glass_jar,
SHIRT-001,30,20,5,0.2,false,poly_bag,
```

**Required Fields:**
- `sku` - Product identifier
- `fragile` - Boolean flag
- `package_type` - Packaging material
- `hazard_class` - UN hazmat classification (if applicable)

## 🎯 ML Strategy Selection

The advanced ML system (XGBoost + LightGBM + RandomForest ensemble) works seamlessly **within** compatibility constraints:

1. Products are first grouped by compatibility
2. ML extracts 34 engineered features for each group
3. Ensemble model predicts optimal strategy for each group
4. Each group is packed using the recommended algorithm
5. Results are combined for final solution

**Enhanced ML Features for Compatibility:**
- `fragility_ratio` - Percentage of fragile items
- `hazmat_flag` - Presence of hazardous materials
- `category_diversity` - Number of different product categories
- `container_volume_ratio` - Spatial intelligence for compatible groups
- `packing_efficiency_estimate` - Estimated efficiency per compatibility group
- `dimensional_harmony_score` - Shape compatibility within safe groups
- `stacking_compatibility_index` - Safe stacking potential
- `container_flexibility_score` - Container options for each group

## 🔍 Validation & Safety Checks

Every packing solution is validated:

```python
# Automatic validation after packing
result = pack_order_safely(products, containers)

# Validation checks:
# 1. No incompatible products in same container ✓
# 2. All products accounted for ✓
# 3. Weight/size constraints respected ✓
# 4. Hazmat regulations followed ✓
```

## 📝 Logging & Warnings

The system provides detailed logging:

```
============================================================
🔒 SAFE PACKING WITH COMPATIBILITY CONSTRAINTS
============================================================
Total products: 5
Available containers: 10

📊 Step 1: Analyzing product compatibility...
✅ Created 3 compatible group(s):
   Group 1: 1 items - Categories: electronics
            ⚠️  Hazmat: 1 items
   Group 2: 1 items - Categories: liquids
   Group 3: 3 items - Categories: general

📦 Step 2: Packing each compatible group...
   ✅ Group 1 packed into 1 container(s)
   ✅ Group 2 packed into 1 container(s)
   ✅ Group 3 packed into 1 container(s)

🔍 Step 3: Validating packed containers...
   ✅ All containers passed safety validation

============================================================
✅ SAFE PACKING COMPLETE
============================================================
```

## 🚀 Benefits

1. **Safety Compliance** - Automatic adherence to shipping regulations
2. **No Manual Checking** - System prevents dangerous combinations
3. **Audit Trail** - Full logging of decisions and rationale
4. **Flexibility** - Easy to add new rules or categories
5. **ML Integration** - Works seamlessly with AI optimization

## 🔧 Customization

To add new compatibility rules, edit `src/compatibility.py`:

```python
# Add new incompatible pair
INCOMPATIBLE_PAIRS = {
    frozenset([ProductCategory.YOUR_CATEGORY_1, ProductCategory.YOUR_CATEGORY_2]),
    # ... existing rules ...
}

# Add new hazmat mapping
HAZMAT_CATEGORY_MAP = {
    "UN1234-YourHazmat": ProductCategory.YOUR_CATEGORY,
    # ... existing mappings ...
}
```

## 📚 References

- UN Hazmat Classifications: https://unece.org/transportdangerous-goods
- IATA Dangerous Goods Regulations
- IMDG Code for Maritime Transport

---

**Last Updated:** October 2024  
**Version:** 2.0.0 (Enhanced with 34-feature ML system)

