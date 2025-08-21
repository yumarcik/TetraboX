import pandas as pd
import numpy as np
from pathlib import Path

def make_boxes():
    rng = np.random.default_rng(7)
    presets = [
        (120,180,60),(160,220,80),(200,250,100),(220,280,120),
        (240,300,140),(260,320,160),(280,340,180),(300,360,200),
        (320,380,220),(340,400,240),(360,420,260),(380,440,280),
        (400,460,300),(420,480,320),(440,500,340),(460,520,360),
        (480,540,380),(500,560,400),(520,580,420),(540,600,440),
        (560,620,460),(580,640,480),(600,660,500),(620,680,520),
    ]
    materials = ["karton","kraft","plastik","tahta"]
    rows = []
    for i,(w,l,h) in enumerate(presets, start=1):
        material = materials[i % len(materials)]
        vol = (w*l*h)/1000.0  # cm3
        tare = 150 + (vol/2000)
        max_w = 2000 + (vol/10)
        price = 3.9 + (vol/8000)
        usage_limit = None
        if material == "plastik" and i % 3 == 0:
            usage_limit = "gıda-yasak"
        rows.append({
            "box_id": f"BOX-{i:03d}",
            "inner_w_mm": w, "inner_l_mm": l, "inner_h_mm": h,
            "tare_weight_g": round(tare,1),
            "max_weight_g": round(max_w,0),
            "material": material,
            "stock": int(rng.integers(40, 400)),
            "price_try": round(price,2),
            "usage_limit": usage_limit
        })
    return pd.DataFrame(rows)

def main():
    out_dir = Path("data/raw")
    out_dir.mkdir(parents=True, exist_ok=True)
    df = make_boxes()
    path = out_dir / "containers.csv"
    df.to_csv(path, index=False)
    print(f"Wrote {path} ({len(df)} rows)")

if __name__ == "__main__":
    main()
