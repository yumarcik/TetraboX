import os
import pandas as pd
import joblib
from ml_helpers import extract_features_for_electronics, extract_features_for_box, extract_features_for_company, extract_features_for_price

# Show all rows and columns
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

# Electronics categories (rule-based)
electronics_categories = ['Electronics', 'Appliance', 'Electrical', 'Phone', 'Laptop', 'Tablet']

def predict_new_data(df_products: pd.DataFrame, basket_id: int):
    model_dir = os.path.join(os.path.dirname(__file__), "models")

    # --- Load ML models ---
    electronics_model = joblib.load(os.path.join(model_dir, "electronics_model.pkl"))
    electronics_features = joblib.load(os.path.join(model_dir, "electronics_feature_cols.pkl"))

    box_model = joblib.load(os.path.join(model_dir, "best_box_model.pkl"))
    box_features = joblib.load(os.path.join(model_dir, "best_box_feature_cols.pkl"))

    company_model = joblib.load(os.path.join(model_dir, "best_company_model.pkl"))
    company_features = joblib.load(os.path.join(model_dir, "best_company_feature_cols.pkl"))

    price_model = joblib.load(os.path.join(model_dir, "best_price_model.pkl"))
    price_features = joblib.load(os.path.join(model_dir, "best_price_feature_cols.pkl"))

    # Get basket data
    new_df = df_products[df_products['basket_id'] == basket_id].copy()

    # --- Fill missing categories from product_final.csv ---
    df_final = pd.read_csv(os.path.join(os.path.dirname(__file__), "../data/product_final.csv"))
    mask_missing = new_df['category'].isna() | (new_df['category'] == 'None')
    new_df.loc[mask_missing, 'category'] = new_df.loc[mask_missing, 'product_id'].map(
        df_final.set_index('product_id')['category']
    )

    # --- Rule-based electronics label ---
    new_df['is_electronics_rule'] = new_df['category'].isin(electronics_categories).astype(int)

    # --- Electronics feature + prediction ---
    X_elec = extract_features_for_electronics(new_df, fit=False, feature_cols_train=electronics_features)
    probs = electronics_model.predict_proba(X_elec)[:, 1]
    threshold = 0.6
    new_df['is_electronics_pred'] = (probs >= threshold).astype(int)

    # --- Hybrid: rule takes precedence ---
    new_df['is_electronics_final'] = new_df.apply(
        lambda row: row['is_electronics_rule'] if row['is_electronics_rule'] == 1 else row['is_electronics_pred'],
        axis=1
    )

    # --- Extract features for Box, Company, Price and reindex ---
    X_box = extract_features_for_box(new_df)
    X_box = X_box.reindex(columns=box_features, fill_value=0)

    X_company = extract_features_for_company(new_df)
    X_company = X_company.reindex(columns=company_features, fill_value=0)

    X_price = extract_features_for_price(new_df)
    X_price = X_price.reindex(columns=price_features, fill_value=0)

    # --- Predictions ---
    new_df['pred_box'] = box_model.predict(X_box)
    new_df['pred_company'] = company_model.predict(X_company)
    new_df['pred_price'] = price_model.predict(X_price)

    # --- Summary columns ---
    new_df['electronics_count'] = new_df['is_electronics_final']
    new_df['utilization'] = new_df['utilization']  # from original dataset
    new_df['categories'] = new_df['category']

    return new_df


def print_basket_summary(pred_df: pd.DataFrame):
    basket_id = pred_df['basket_id'].iloc[0]
    n_products = pred_df.shape[0]
    electronics_count = pred_df['is_electronics_final'].sum()

    # Aggregate boxes (one row per box)
    grouped = pred_df.groupby('box_number').agg(
        box_name=('box_name', 'first'),
        company=('company', 'first'),
        pred_price=('pred_price', 'first'),
        utilization=('utilization', 'mean'),
        is_electronics_final=('is_electronics_final', 'first'),
        product_ids=('product_id', list),
        categories=('category', lambda x: list(x.unique()))  # unique categories
    )

    total_boxes = grouped.shape[0]
    total_cost = grouped['pred_price'].sum()  # cost per box
    unique_companies = grouped['company'].unique()
    if len(unique_companies) > 1:
        company_mode = "MULTI"
    else:
        company_mode = unique_companies[0]

    # Electronics vs regular boxes
    electronics_boxes = grouped['is_electronics_final'].sum()
    regular_boxes = total_boxes - electronics_boxes

    print(f"🛒 Basket {basket_id}: {n_products} products")
    print(f"   📱 Electronics detected: {electronics_count}")
    print(f"   📦 Total boxes required: {total_boxes}")
    print(f"   🔌 Electronics boxes: {electronics_boxes}")
    print(f"   📦 Non-electronics boxes: {regular_boxes}")
    print(f"   💰 Total cost: {total_cost:.2f} TL")
    print(f"   🚚 Shipping company: {company_mode}")
    print(f"   📦 Multiple shipments: {'Yes' if total_boxes > 1 else 'No'}\n")

    for box_num, row in grouped.iterrows():
        is_elec = row['is_electronics_final']
        box_type = "ELECTRONICS" if is_elec else "REGULAR"
        price = row['pred_price']
        utilization = row['utilization'] * 100
        products = row['product_ids']
        categories = row['categories']

        print(f"     📱 {box_type} BOX {box_num}: {row['box_name']}")
        print(f"        🏢 Company: {row['company']}")
        print(f"        💰 Price: {price:.2f} TL")
        print(f"        🎯 Utilization: {utilization:.1f}%")
        print(f"        📋 Product IDs: {products}")
        print(f"        📊 Categories: {categories}\n")


if __name__ == "__main__":
    csv_path = os.path.join(os.path.dirname(__file__), "data/products_train_updated.csv")
    df_products = pd.read_csv(csv_path)
    basket_id = 3040
    result_df = predict_new_data(df_products, basket_id=basket_id)
    print_basket_summary(result_df)
