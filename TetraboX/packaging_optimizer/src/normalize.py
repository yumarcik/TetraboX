import numpy as np
import pandas as pd
from .io_utils import load_config, read_csv_cfg, to_bool, unit_to_mm, unit_to_g, gen_auto_ids

def normalize_products(cfg) -> pd.DataFrame:
    c = cfg["product"]
    df = read_csv_cfg(c).copy()

    # IDs
    if c.get("id_col"):
        sku = df[c["id_col"]].astype(str)
    else:
        sku = pd.Series(gen_auto_ids(len(df),
                                     prefix=c.get("id_prefix","SKU"),
                                     start_index=int(c.get("id_start_index",1))))
    # Dimensions & weight
    width_mm  = df[c["width_col"]].apply(lambda v: unit_to_mm(v, c["width_unit"]))
    length_mm = df[c["length_col"]].apply(lambda v: unit_to_mm(v, c["length_unit"]))
    height_mm = df[c["height_col"]].apply(lambda v: unit_to_mm(v, c["height_unit"]))
    weight_g  = df[c["weight_col"]].apply(lambda v: unit_to_g(v, c["weight_unit"]))

    out = pd.DataFrame({
        "sku": sku,
        "width_mm": width_mm.astype(float),
        "length_mm": length_mm.astype(float),
        "height_mm": height_mm.astype(float),
        "weight_g": weight_g.astype(float),
    })

    # Flags / categories
    frag_col = c.get("fragile_col")
    out["fragile"] = df[frag_col].apply(to_bool) if frag_col in df.columns else False

    pack_col = c.get("packaging_type_col")
    out["packaging_type"] = df[pack_col] if pack_col in df.columns else "kutu"
    cmap = (c.get("categorical_maps") or {}).get("packaging_type") or {}
    out["packaging_type"] = out["packaging_type"].map(lambda x: cmap.get(str(x).lower(), x))

    # Hazmat
    haz_col = c.get("hazmat_col")
    def clean_haz(v):
        if pd.isna(v): return None
        s = str(v).strip()
        return None if s=="" or s.lower() in {"yok","none","0","-"} else s
    out["hazmat_class"] = df[haz_col].map(clean_haz) if haz_col in df.columns else None

    # Extra packaging
    flag_col = c.get("extra_pack_flag_col")
    out["extra_pack"] = df[flag_col].apply(to_bool) if flag_col in df.columns else False

    wcol = c.get("extra_pack_size_col_width")
    lcol = c.get("extra_pack_size_col_length")
    out["extra_pack_width_mm"]  = df[wcol].apply(lambda v: unit_to_mm(v, "cm")) if wcol in df.columns else np.nan
    out["extra_pack_length_mm"] = df[lcol].apply(lambda v: unit_to_mm(v, "cm")) if lcol in df.columns else np.nan

    # Price (USD → TRY)
    price_col = c.get("extra_pack_price_col")
    fx = float(c.get("fx_to_try", 1.0))
    if price_col and price_col in df.columns:
        out["extra_pack_price_try"] = df[price_col].astype(float) * fx
    else:
        out["extra_pack_price_try"] = np.nan

    # Extra type passthrough (if present)
    out["extra_pack_type"] = df.get("extra_type", pd.Series([np.nan]*len(df)))

    return out

def normalize_containers(cfg) -> pd.DataFrame:
    from .io_utils import read_csv_cfg, unit_to_mm, unit_to_g, gen_auto_ids
    import numpy as np
    import pandas as pd

    c = cfg["container"]
    df = read_csv_cfg(c).copy()

    # --- helpers ---
    def parse_num(v):
        if pd.isna(v): return np.nan
        s = str(v).strip().replace(",", ".")  # handle stray commas if any
        try:
            return float(s)
        except:
            return np.nan

    # --- box_id (auto if missing) ---
    if c.get("box_id_col") and c["box_id_col"] in df.columns:
        box_id = df[c["box_id_col"]].astype(str)
    else:
        box_id = pd.Series(gen_auto_ids(len(df),
                                        prefix=c.get("id_prefix","BOX"),
                                        start_index=int(c.get("id_start_index",1))))

    # --- dimensions (cm → mm) ---
    w_mm = df[c["inner_w_col"]].map(parse_num).apply(lambda v: unit_to_mm(v, c["width_unit"]))
    l_mm = df[c["inner_l_col"]].map(parse_num).apply(lambda v: unit_to_mm(v, c["length_unit"]))
    h_mm = df[c["inner_h_col"]].map(parse_num).apply(lambda v: unit_to_mm(v, c["height_unit"]))

    # --- weights ---
    tare = df[c["tare_weight_col"]].map(parse_num)
    tare_g = tare.apply(lambda v: unit_to_g(v, c["tare_weight_unit"]))

    # max weight: mixed data → auto + fallback from class
    raw_max = df[c["max_weight_col"]].map(parse_num)

    def auto_to_grams(x):
        if pd.isna(x): return np.nan
        # Heuristic: <=200 means kg (e.g., 4.0), else already grams
        return x*1000 if str(c.get("max_weight_unit","auto")).lower()=="auto" and x <= 200 else x

    max_g = raw_max.map(auto_to_grams)

    # fallback from 'maks_taşıma' category if missing or nonsense
    fb_col = c.get("max_weight_fallback_col")
    if fb_col and fb_col in df.columns:
        fb = df[fb_col].astype(str).str.strip().str.lower()
        fb_map = {"mikro": 2, "xs": 4, "s": 7, "m": 10, "l": 15, "xl": 20}
        fb_g = fb.map(fb_map).astype(float) * 1000
        # fill NA or clearly broken numbers (e.g., > 100000 g)
        max_g = max_g.where(~(max_g.isna() | (max_g > 100000)), fb_g)

    # --- material, stock, price ---
    material = df[c["material_col"]].astype(str).str.lower()
    stock = df[c["stock_col"]].map(parse_num).fillna(0).astype(int)
    price_try = df[c["price_col"]].map(parse_num)

    # --- usage_limit normalize ('Sıvı hariç' → 'sıvı-yasak') ---
    ucol = c.get("usage_limit_col")
    usage_limit = None
    if ucol and ucol in df.columns:
        usage_limit = (df[ucol].astype(str)
                            .str.strip()
                            .replace({"Sıvı hariç": "sıvı-yasak",
                                      "sıvı hariç": "sıvı-yasak",
                                      "liquid excluded": "sıvı-yasak"}))

    out = pd.DataFrame({
        "box_id": box_id,
        "inner_w_mm": w_mm.astype(float),
        "inner_l_mm": l_mm.astype(float),
        "inner_h_mm": h_mm.astype(float),
        "tare_weight_g": tare_g.astype(float),
        "max_weight_g": max_g.astype(float),
        "material": material,
        "stock": stock,
        "price_try": price_try.astype(float),
        "usage_limit": usage_limit if usage_limit is not None else None,
    })
    return out


def run_normalization(config_path="config.yaml"):
    cfg = load_config(config_path)
    products = normalize_products(cfg)
    containers = normalize_containers(cfg)
    products.to_csv(cfg["output"]["normalized_products"], index=False)
    containers.to_csv(cfg["output"]["normalized_containers"], index=False)
    return cfg["output"]["normalized_products"], cfg["output"]["normalized_containers"]
