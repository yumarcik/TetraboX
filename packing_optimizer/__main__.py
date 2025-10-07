from .core import main

def cli():
    import argparse
    p = argparse.ArgumentParser(description="TetraboX Packing Optimizer")
    p.add_argument("--products", required=True, help="Path to products CSV")
    p.add_argument("--boxes", required=True, help="Path to boxes XLSX")
    args = p.parse_args()

    main(products_path=args.products, boxes_path=args.boxes)

if __name__ == "__main__":
    cli()