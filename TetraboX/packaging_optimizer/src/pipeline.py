import pandas as pd
from typing import List
from .models import Product, Container
from .heuristics import choose_container, utilization

def _df_to_products(df: pd.DataFrame) -> List[Product]:
    items: List[Product] = []
    for _, r in df.iterrows():
        items.append(Product(
            sku=str(r["sku"]),
            width_mm=float(r["width_mm"]),
            length_mm=float(r["length_mm"]),
            height_mm=float(r["height_mm"]),
            weight_g=float(r["weight_g"]),
            fragile=bool(r["fragile"]),
            packaging_type=str(r["packaging_type"]),
            hazmat_class=(None if pd.isna(r["hazmat_class"]) else str(r["hazmat_class"])),
            extra_pack=bool(r["extra_pack"]),
            extra_pack_width_mm=(None if pd.isna(r["extra_pack_width_mm"]) else float(r["extra_pack_width_mm"])),
            extra_pack_length_mm=(None if pd.isna(r["extra_pack_length_mm"]) else float(r["extra_pack_length_mm"])),
            extra_pack_price_try=(None if pd.isna(r["extra_pack_price_try"]) else float(r["extra_pack_price_try"])),
            extra_pack_type=(None if ("extra_pack_type" not in r or pd.isna(r["extra_pack_type"])) else str(r["extra_pack_type"])),
        ))
    return items

def _df_to_containers(df: pd.DataFrame) -> List[Container]:
    items: List[Container] = []
    for _, r in df.iterrows():
        items.append(Container(
            box_id=str(r["box_id"]),
            inner_w_mm=float(r["inner_w_mm"]),
            inner_l_mm=float(r["inner_l_mm"]),
            inner_h_mm=float(r["inner_h_mm"]),
            tare_weight_g=float(r["tare_weight_g"]),
            max_weight_g=float(r["max_weight_g"]),
            material=str(r["material"]),
            stock=int(r["stock"]),
            price_try=float(r["price_try"]),
            usage_limit=(None if ("usage_limit" not in r or pd.isna(r["usage_limit"])) else str(r["usage_limit"])),
        ))
    return items

def assign_single_items(products_csv: str, containers_csv: str, out_csv: str):
    p_df = pd.read_csv(products_csv)
    c_df = pd.read_csv(containers_csv)

    products = _df_to_products(p_df)
    containers = _df_to_containers(c_df)

    rows = []
    for p in products:
        c = choose_container(p, containers)
        if c:
            rows.append({
                "sku": p.sku, "box_id": c.box_id,
                "utilization": round(utilization(p, c), 4),
                "price_try": c.price_try
            })
            c.stock -= 1
        else:
            rows.append({"sku": p.sku, "box_id": None, "utilization": 0.0, "price_try": None})

    out = pd.DataFrame(rows)
    out.to_csv(out_csv, index=False)
    return out_csv
