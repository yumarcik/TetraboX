import pandas as pd
import numpy as np

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 300)
pd.set_option("display.max_colwidth", None)


df = pd.read_excel(r"C:\Users\ipeki\OneDrive\Masaüstü\Tetrabox_studies\boxes.xlsx")

df['boxes_id'] = range(1, len(df) + 1)

# Sadece NaN olan stokları 50 ile doldur
df['Stok'] = df['Stok'].fillna(50)

# 2D flag
df['is_2d_only'] = df['height_cm'].isna()

# hacim sütunu
df['volume_cm3'] = df.apply(lambda row: row['width_cm'] * row['length_cm'] * row['height_cm']
                            if not row['is_2d_only'] else np.nan, axis=1)


# kutu tipi kategorisi ekle
def categorize_box(row):
    name = str(row['box_name']).lower()

    # Boyut isimlerini Box olarak sınıflandır
    size_tokens = ["s", "m", "l", "xs", "xl", "xxl", "xxxl", "micro", "fresh", "fruit"]
    if any(token in name.split() for token in size_tokens):
        return "Box"

    # Mevcut kurallar
    if "box" in name or "cardboard" in name or "nano" in name or "maxi" in name:
        return "Box"
    elif "envelope" in name:
        return "Envelope"
    elif "bag" in name:
        return "Bag"
    elif "roll" in name or "film" in name:
        return "Roll"
    elif "air" in name or "protective" in name:
        return "AirPack/Protective"
    else:
        return "Other"

df['box_type'] = df.apply(categorize_box, axis=1)

# tahmini max ağırlık belirlenmesi
def estimate_max_weight(row):
    vol = row['volume_cm3']
    if pd.isna(vol):
        return np.nan  # hacim yoksa ağırlık bilinmiyor
    elif vol < 2000:
        return 2
    elif vol < 10000:
        return 5
    elif vol < 30000:
        return 10
    else:
        return 20

df['max_weight_kg'] = df.apply(estimate_max_weight, axis=1)

df.to_excel("C:/Users/ipeki/OneDrive/Masaüstü/Tetrabox_studies/boxes_final.xlsx", index=False)
print("İşlenmiş veri seti oluşturuldu: boxes_final.xlsx")