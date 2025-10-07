import pandas as pd
import numpy as np

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 300)
pd.set_option("display.max_colwidth", None)


products = pd.read_csv(r"C:\Users\ipeki\OneDrive\Masaüstü\Tetrabox_studies\products.csv", sep=";")

#product_id ekleyelim
products['product_id'] = range(1, len(products) + 1)

# Simülasyon için rasgele müşteri ve basket id ekleyelim
num_customers = 500
num_baskets = 1000
np.random.seed(42)

# Her ürün için random customer ata
products['customer_id'] = np.random.randint(1000, 1000 + num_customers, size=len(products))

basket_id_counter = 2000

# Sepetleri oluştur
basket_ids = []
for customer in products['customer_id'].unique():
    customer_indices = products[products['customer_id'] == customer].index.to_numpy()
    np.random.shuffle(customer_indices)

    start_idx = 0
    while start_idx < len(customer_indices):
        basket_size = np.random.randint(2, 6)
        end_idx = min(start_idx + basket_size, len(customer_indices))
        basket_indices = customer_indices[start_idx:end_idx]
        products.loc[basket_indices, 'basket_id'] = basket_id_counter
        basket_id_counter += 1
        start_idx = end_idx

products['basket_id'] = products['basket_id'].astype(int)

# quantity kolonunu ekleyelim (1-3 arasında rasgele)
products['quantity'] = np.random.randint(1, 4, size=len(products))

# Eksik değerleri kontrol et
# height_cm boş olanlar için is_2d_only = True
products['is_2d_only'] = products['height_cm'].isna()

# Eksik height olanlara geçici height = 1 atayabiliriz (hacim hesaplaması için)
products['height_cm_filled'] = products['height_cm'].fillna(1)

# Önce stringlerdeki ',' işaretlerini '.' yap ve float'a çevir
for col in ['width_cm', 'length_cm', 'height_cm_filled']:
    products[col] = products[col].astype(str).str.replace(',', '.').astype(float)

# weight_kg kolonunu düzelt
products['weight_kg'] = products['weight_kg'].astype(str).str.replace(',', '.').astype(float)

# Ürün hacmi
products['volume_cm3'] = products['width_cm'] * products['length_cm'] * products['height_cm_filled']

# Hacim / ağırlık oranı
products['volume_to_weight_ratio'] = products['volume_cm3'] / products['weight_kg']

# Fragile flag
products['fragile_flag'] = products['fragile']

# Special handling: tehlikeli madde veya ekstra ambalaj
products['requires_special_handling'] = products['hazard_class'].notna() | products['extra_package'].fillna(False)


# extra_width_cm ve extra_length_cm kolonlarını düzelt
for col in ['extra_width_cm', 'extra_length_cm']:
    products[col] = products[col].fillna(0).astype(str).str.replace(',', '.').astype(float)

# Extra ambalaj hacmi (varsa)
products['extra_volume_cm3'] = np.where(
    products['extra_package'].fillna(False),
    products['extra_width_cm'] * products['extra_length_cm'] * products['height_cm_filled'],
    0
)

# Shape flag
products['shape_flag'] = products['package_type']


products.to_csv("C:/Users/ipeki/OneDrive/Masaüstü/Tetrabox_studies/products_final.csv", index=False)
print("İşlenmiş veri seti oluşturuldu: product_final.csv")