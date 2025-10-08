# Quick Start: Safe Packing with Product Compatibility

## 🎯 What Problem Does This Solve?

**Before:** Electronics, liquids, and hazardous materials could accidentally be packed together, creating safety hazards.

**Now:** The system **automatically separates** incompatible products into different containers based on safety regulations.

## ⚡ Quick Examples

### Example 1: Phone + Shampoo Order

```python
from src.safe_packer import pack_order_safely
from src.io import load_products_csv, load_containers_csv

# Load data
products_db = {p.sku: p for p in load_products_csv("data/products.csv")}
containers = load_containers_csv("data/container.csv")

# Order with phone (battery) and shampoo (liquid)
order_products = [
    products_db["PHIL-822F1A"],  # Philips Kettle (UN3481 battery)
    products_db["LUMI-F2C6A3"],  # Lumine Day Cream (liquid)
]

# Pack with safety constraints
result = pack_order_safely(order_products, containers)

# Result: 2 separate containers automatically!
# Container 1: Kettle only (electronics)
# Container 2: Day Cream only (liquids)
```

### Example 2: Check Before Packing

```python
from src.compatibility import CompatibilityChecker

phone = products_db["PHIL-822F1A"]
shampoo = products_db["LUMI-F2C6A3"]

# Quick compatibility check
if CompatibilityChecker.are_compatible(phone, shampoo):
    print("✅ Can pack together")
else:
    reason = CompatibilityChecker.get_incompatibility_reason(phone, shampoo)
    print(f"❌ Cannot pack together: {reason}")
    # Output: "Cannot pack electronics with liquids (safety regulation)"
```

## 🔥 Common Scenarios

### Scenario 1: Mixed Order (Safe Items)

**Order:** Shirt + Book + Toy

```python
# All general items, no hazmat
result = pack_order_safely([shirt, book, toy], containers)
# ✅ Result: 1 container (all compatible)
```

### Scenario 2: Electronics + Clothes

**Order:** Laptop + T-Shirts (2x)

```python
result = pack_order_safely([laptop, tshirt1, tshirt2], containers)
# ✅ Result: 1 or 2 containers depending on size
# (Electronics and textiles CAN be together)
```

### Scenario 3: Hazmat Mix (Unsafe)

**Order:** Phone + Shampoo + Cleaning Spray

```python
result = pack_order_safely([phone, shampoo, spray], containers)
# ⚠️  Result: 3 containers minimum
# Container 1: Phone (electronics)
# Container 2: Shampoo (liquid)
# Container 3: Spray (corrosive/aerosol)
```

## 🚀 Integration with Existing Code

### Replace Your Current Packing Call

**OLD WAY (No Safety Checks):**
```python
from src.packer import pack_multi_container

result = pack_multi_container(products, containers)
```

**NEW WAY (With Safety):**
```python
from src.safe_packer import pack_order_safely

safe_result = pack_order_safely(products, containers)
packed_containers = safe_result.packed_containers
warnings = safe_result.warnings
```

## 📊 Understanding the Output

```python
result = pack_order_safely(products, containers)

print(f"Success: {result.success}")
print(f"Containers used: {len(result.packed_containers)}")
print(f"Compatibility groups: {len(result.compatibility_groups)}")

# Each group shows what categories of products
for i, group in enumerate(result.compatibility_groups):
    categories = [CompatibilityChecker.get_product_category(p).value for p in group]
    print(f"Group {i+1}: {len(group)} items - {set(categories)}")

# Warnings if any issues
for warning in result.warnings:
    print(f"⚠️  {warning}")
```

## 🎨 Product Categories

Your products are automatically categorized based on CSV data:

| CSV Field | Example Value | Category |
|-----------|---------------|----------|
| `hazard_class` | "UN3481-Lithium_Ion_Battery" | Electronics |
| `hazard_class` | "Flammable_Liquid-3" | Flammable |
| `hazard_class` | "Corrosive-8" | Corrosive |
| `package_type` | "glass_jar" | Liquids |
| `fragile` | true | Fragile |
| (none) | (none) | General |

## 💡 Pro Tips

### 1. Pre-Check Large Orders

```python
from src.compatibility import CompatibilityChecker

# Get expected number of containers before packing
groups = CompatibilityChecker.group_compatible_products(products)
print(f"Minimum {len(groups)} containers needed (based on compatibility)")
```

### 2. Get Detailed Report

```python
from src.safe_packer import get_packing_report

result = pack_order_safely(products, containers)
report = get_packing_report(products, result)

print(f"Hazmat items: {report['product_analysis']['hazmat_items']}")
print(f"Categories: {report['product_analysis']['categories']}")
```

### 3. Explain to Customer

```python
# If multiple containers are used, explain why
if len(result.compatibility_groups) > 1:
    print(f"Your order requires {len(result.packed_containers)} containers")
    print(f"for safety reasons:")
    
    for i, group in enumerate(result.compatibility_groups):
        categories = set(CompatibilityChecker.get_product_category(p).value 
                        for p in group)
        print(f"  • Package {i+1}: {', '.join(categories)}")
```

## 🐛 Troubleshooting

### Issue: "Failed to pack group X"

**Cause:** Products in the group don't fit even in largest container

**Solution:** 
- Check product dimensions
- Ensure containers are large enough
- May need to split order manually

### Issue: More containers than expected

**Cause:** Multiple incompatible product categories

**Solution:**
- This is correct behavior for safety
- Check `result.compatibility_groups` to see why
- Consider removing incompatible items

### Issue: Compatibility seems wrong

**Cause:** Missing or incorrect hazmat data in CSV

**Solution:**
- Verify `hazard_class` field in products.csv
- Check `package_type` for liquids
- Update product data if needed

## 📝 Testing Your Setup

```python
# Test script
from src.safe_packer import pack_order_safely
from src.io import load_products_csv, load_containers_csv

# Load all products
products_db = {p.sku: p for p in load_products_csv("data/products.csv")}
containers = load_containers_csv("data/container.csv")

# Test case 1: Electronics only
test1 = [products_db["PHIL-822F1A"]]  # Kettle with battery
result1 = pack_order_safely(test1, containers)
print(f"Test 1 - Electronics: {result1.success}, Groups: {len(result1.compatibility_groups)}")

# Test case 2: Mixed unsafe
test2 = [
    products_db["PHIL-822F1A"],  # Battery
    products_db["LUMI-F2C6A3"],  # Liquid
]
result2 = pack_order_safely(test2, containers)
print(f"Test 2 - Mixed: {result2.success}, Groups: {len(result2.compatibility_groups)}")
assert len(result2.compatibility_groups) >= 2, "Should create separate groups!"

print("✅ All tests passed!")
```

## 🔗 See Also

- Full rules: `COMPATIBILITY_RULES.md`
- API documentation: `TECHNICAL_DOCUMENTATION.md`
- Source code: `src/compatibility.py` and `src/safe_packer.py`

---

**Ready to use!** Just replace your `pack_multi_container` calls with `pack_order_safely`.

