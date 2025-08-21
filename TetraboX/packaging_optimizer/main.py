from src.io_utils import load_config
from src.normalize import run_normalization
from src.pipeline import assign_single_items
from src.evaluate import summary

if __name__ == "__main__":
    cfg = load_config("config.yaml")
    p_csv, c_csv = run_normalization("config.yaml")
    out = assign_single_items(p_csv, c_csv, cfg["output"]["assignments"])
    print("✅ Assignments written:", out)
    print(summary(out))
