import pandas as pd
import yaml
from pathlib import Path

TRUE_SET = {"true","1","yes","y","evet","doğru","t"}
FALSE_SET = {"false","0","no","n","hayır","yanlış","f",""}

def load_config(path="config.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def read_csv_cfg(section: dict) -> pd.DataFrame:
    """
    Read CSV using delimiter/decimal/encoding from config.
    """
    from pathlib import Path
    path = section["path"]
    sep = section.get("sep", ",")
    decimal = section.get("decimal", ".")
    encoding = section.get("encoding", "utf-8")  # NEW
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    return pd.read_csv(p, sep=sep, decimal=decimal, encoding=encoding)  # CHANGED


def to_bool(v):
    if pd.isna(v): return False
    s = str(v).strip().lower()
    if s in TRUE_SET: return True
    if s in FALSE_SET: return False
    try:
        return float(s) != 0.0
    except:
        return False

def unit_to_mm(x, unit: str):
    if pd.isna(x): return x
    u = unit.lower()
    v = float(x)
    if u == "mm": return v
    if u == "cm": return v * 10.0
    if u == "m":  return v * 1000.0
    raise ValueError(f"Unknown length unit: {unit}")

def unit_to_g(x, unit: str):
    if pd.isna(x): return x
    u = unit.lower()
    v = float(x)
    if u == "g": return v
    if u == "kg": return v * 1000.0
    raise ValueError(f"Unknown weight unit: {unit}")

def gen_auto_ids(n: int, prefix: str = "SKU", start_index: int = 1):
    """
    Auto-generate SKUs when id_col is missing.
    """
    width = max(6, len(str(start_index + n - 1)))
    return [f"{prefix}-{i:0{width}d}" for i in range(start_index, start_index + n)]
