import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MultiLabelBinarizer
import ast

def load_dataset(file_path: str = None):
    """
    Loads the CSV, adds necessary features, and performs train-test split.
    Handles missing 'categories' column safely.
    """
    if file_path is None:
        updated_path = os.path.join(os.path.dirname(__file__), "data/products_train_updated.csv")
        default_path = os.path.join(os.path.dirname(__file__), "data/all_baskets_details.csv")
        file_path = updated_path if os.path.exists(updated_path) else default_path

    df = pd.read_csv(file_path)

    # Parse 'products' column if exists
    if 'products' in df.columns:
        df['products'] = df['products'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)
    else:
        df['products'] = [[] for _ in range(len(df))]

    # --- Feature Engineering ---
    df['total_weight'] = df['products'].apply(lambda products: sum(p.get('weight_kg',0)*p.get('quantity',0) for p in products))
    df['total_volume'] = df['products'].apply(lambda products: sum(p.get('volume_m3',0)*p.get('quantity',0) for p in products))
    df['electronics_count'] = df['products'].apply(lambda products: sum(1 for p in products if p.get('is_electronics', False)))
    df['fragile_count'] = df['products'].apply(lambda products: sum(1 for p in products if p.get('is_fragile', False)))

    # --- Categories ---
    if 'categories' in df.columns:
        df['num_categories'] = df['categories'].apply(lambda x: len(str(x).split(',')))
        mlb = MultiLabelBinarizer()
        categories_onehot = mlb.fit_transform(df['categories'].apply(lambda x: str(x).split(',')))
        categories_df = pd.DataFrame(categories_onehot, columns=[f"cat_{c}" for c in mlb.classes_])
    else:
        # Handle missing categories
        df['num_categories'] = 0
        categories_df = pd.DataFrame()
        mlb = None

    # --- Feature Set ---
    base_features = ['box_number', 'price', 'utilization', 'num_categories', 'total_weight', 'total_volume', 'electronics_count', 'fragile_count']
    X = df[base_features]
    if not categories_df.empty:
        X = pd.concat([X, categories_df], axis=1)

    # --- Targets ---
    y_box = df['box_name'] if 'box_name' in df.columns else None
    y_company = df['company'] if 'company' in df.columns else None
    y_price = df['price'] if 'price' in df.columns else None

    # --- Train-Test Split ---
    X_train, X_test, y_box_train, y_box_test, y_company_train, y_company_test, y_price_train, y_price_test = train_test_split(
        X, y_box, y_company, y_price, test_size=0.2, random_state=42
    )

    return X_train, X_test, y_box_train, y_box_test, y_company_train, y_company_test, y_price_train, y_price_test, mlb


if __name__ == "__main__":
    X_train, X_test, y_box_train, y_box_test, y_company_train, y_company_test, y_price_train, y_price_test, mlb = load_dataset()
    print("✅ Dataset loaded and features added.")
    print("Columns:", X_train.columns.tolist())
