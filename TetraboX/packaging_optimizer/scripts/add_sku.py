import pandas as pd
from pathlib import Path
import hashlib


def slugify(s: str) -> str:
	s = (s or "").strip()
	s = s.replace(" ", "-")
	return "".join(ch for ch in s if ch.isalnum() or ch in {"-","_"}).upper()


def gen_sku(brand: str, model: str, variant: str) -> str:
	key = f"{brand}|{model}|{variant}".strip().lower()
	# Short hash to ensure uniqueness for long combos
	digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:6].upper()
	prefix = slugify(brand)[:4]
	return f"{prefix}-{digest}"


def main():
	inp = Path("data/products.csv")
	if not inp.exists():
		raise FileNotFoundError(inp)
	df = pd.read_csv(inp, sep=';', decimal=',')
	if 'sku' not in df.columns:
		brand = df.get('brand', '').astype(str)
		model = df.get('model', '').astype(str)
		variant = df.get('variant', '').astype(str)
		df.insert(0, 'sku', [gen_sku(brand.iloc[i], model.iloc[i], variant.iloc[i]) for i in range(len(df))])
		df.to_csv(inp, sep=';', decimal=',', index=False)
		print(f"Added 'sku' to {inp} (rows={len(df)})")
	else:
		print("'sku' already present. No change.")


if __name__ == '__main__':
	main()
