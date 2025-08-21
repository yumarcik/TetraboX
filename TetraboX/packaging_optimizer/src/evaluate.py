import pandas as pd

def summary(assignments_csv: str):
    a = pd.read_csv(assignments_csv)
    total = len(a)
    placed = a["box_id"].notna().sum()
    placement_rate = placed / total if total else 0
    avg_util = a["utilization"].mean()
    avg_price = a["price_try"].dropna().mean()
    return {
        "orders_total": int(total),
        "placed_rate": round(float(placement_rate), 3),
        "avg_utilization": round(float(avg_util), 3) if pd.notna(avg_util) else None,
        "avg_box_price_try": round(float(avg_price), 2) if pd.notna(avg_price) else None
    }
