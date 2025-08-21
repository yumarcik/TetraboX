# Packing Engine

## Quick start
1. Create folders:
mkdir -p data/raw data/normalized

2. Place your products CSV at:
`data/raw/products.csv`

3. Provide a containers CSV at `data/raw/containers.csv`
- Or generate a sample set:
  ```
  python scripts/make_containers.py
  ```
4. Install deps:
pip install -r requirements.txt

5. Run:
python main.py

Outputs:
- `data/normalized/products.csv`
- `data/normalized/containers.csv`
- `data/normalized/assignments.csv` (chosen box, utilization, price)

## Configure
Edit `config.yaml` to map column names, units, and separators/decimals.