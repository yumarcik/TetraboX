import pandas as pd
from typing import List, Dict, Any
from .io import load_products_csv, load_containers_csv


def validate_products(path: str) -> List[Dict[str, Any]]:
	reports: List[Dict[str, Any]] = []
	try:
		prods = load_products_csv(path)
	except Exception as e:
		reports.append({"level":"error","message":f"Reading products failed: {e}"})
		return reports
	for p in prods:
		if p.width_mm <= 0 or p.length_mm <= 0 or p.height_mm <= 0:
			reports.append({"level":"error","sku":p.sku,"message":"Non-positive dimension detected"})
		if p.weight_g <= 0:
			reports.append({"level":"warning","sku":p.sku,"message":"Non-positive weight"})
	return reports


def validate_containers(path: str) -> List[Dict[str, Any]]:
	reports: List[Dict[str, Any]] = []
	try:
		boxes = load_containers_csv(path)
	except Exception as e:
		reports.append({"level":"error","message":f"Reading containers failed: {e}"})
		return reports
	for c in boxes:
		if c.inner_w_mm <= 0 or c.inner_l_mm <= 0 or c.inner_h_mm <= 0:
			reports.append({"level":"error","box_id":c.box_id,"message":"Non-positive inner dimension"})
		if c.max_weight_g is None or c.max_weight_g <= 0:
			reports.append({"level":"warning","box_id":c.box_id,"message":"Missing or non-positive max weight"})
		if c.stock < 0:
			reports.append({"level":"warning","box_id":c.box_id,"message":"Negative stock"})
	return reports


def print_report(items: List[Dict[str, Any]]):
	if not items:
		print("No issues found.")
		return
	for i in items:
		lvl = i.get("level","info").upper()
		detail = {k:v for k,v in i.items() if k not in {"level"}}
		print(f"[{lvl}] {detail}")


if __name__ == "__main__":
	import argparse
	parser = argparse.ArgumentParser(description="Validate products and containers CSVs")
	parser.add_argument("--products", default="data/products.csv")
	parser.add_argument("--containers", default="data/container.csv")
	args = parser.parse_args()
	print("Products:")
	print_report(validate_products(args.products))
	print("Containers:")
	print_report(validate_containers(args.containers))
