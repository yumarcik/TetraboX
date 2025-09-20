import argparse
from .packing_optimizer import main  # mevcut main()'i kullanacağız

def cli():
    p = argparse.ArgumentParser(description="TetraboX Packing Optimizer")
    p.add_argument("--products", required=True, help="Path to products CSV")
    p.add_argument("--boxes", required=True, help="Path to boxes XLSX")
    p.add_argument("--top-n-baskets", type=int, default=5)
    p.add_argument("--max-elec-volume", type=float, default=50000)
    p.add_argument("--max-elec-weight", type=float, default=20)
    args = p.parse_args()

    # main() fonksiyonunu parametreli çalıştır
    main(
        products_path=args.products,
        boxes_path=args.boxes,
        top_n_baskets=args.top_n_baskets,
        max_elec_volume=args.max_elec_volume,
        max_elec_weight=args.max_elec_weight,
    )

if __name__ == "__main__":
    cli()
