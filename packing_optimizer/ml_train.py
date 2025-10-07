import os
import joblib
import numpy as np
import pandas as pd
import ast
from itertools import zip_longest
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.neural_network import MLPClassifier, MLPRegressor
from xgboost import XGBClassifier, XGBRegressor
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.metrics import accuracy_score, mean_absolute_error, mean_squared_error
from ml_dataset import load_dataset
from ml_helpers import extract_features_for_electronics


def evaluate_classifiers(X_train, X_test, y_train, y_test):
    classifiers = {
        "RandomForest": RandomForestClassifier(n_estimators=200, random_state=42),
        "XGBoost": XGBClassifier(n_estimators=200, use_label_encoder=False, eval_metric='mlogloss', random_state=42),
        "LightGBM": LGBMClassifier(n_estimators=200, random_state=42),
        "MLP": MLPClassifier(hidden_layer_sizes=(100, 50), max_iter=500, random_state=42)
    }

    best_model = None
    best_acc = 0
    X_train.columns = X_train.columns.astype(str)
    X_test.columns = X_test.columns.astype(str)
    X_train_np = X_train.values
    X_test_np = X_test.values

    for name, clf in classifiers.items():
        if name in ["XGBoost", "LightGBM"]:
            clf.fit(X_train_np, y_train)
            preds = clf.predict(X_test_np)
        else:
            clf.fit(X_train, y_train)
            preds = clf.predict(X_test)
        acc = accuracy_score(y_test, preds)
        print(f"{name} Accuracy: {acc:.4f}")
        if acc > best_acc:
            best_acc = acc
            best_model = clf

    return best_model, best_acc


def evaluate_regressors(X_train, X_test, y_train, y_test):
    regressors = {
        "RandomForest": RandomForestRegressor(n_estimators=200, random_state=42),
        "XGBoost": XGBRegressor(n_estimators=200, random_state=42),
        "LightGBM": LGBMRegressor(n_estimators=200, random_state=42),
        "MLP": MLPRegressor(hidden_layer_sizes=(100, 50), max_iter=500, random_state=42)
    }

    best_model = None
    best_mae = float('inf')
    X_train.columns = X_train.columns.astype(str)
    X_test.columns = X_test.columns.astype(str)
    X_train_np = X_train.values
    X_test_np = X_test.values

    for name, reg in regressors.items():
        if name in ["XGBoost", "LightGBM"]:
            reg.fit(X_train_np, y_train)
            preds = reg.predict(X_test_np)
        else:
            reg.fit(X_train, y_train)
            preds = reg.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        print(f"{name} MAE: {mae:.2f}, RMSE: {rmse:.2f}")
        if mae < best_mae:
            best_mae = mae
            best_model = reg

    return best_model, best_mae


def train_best_models():
    # === ELECTRONICS MODEL ===
    print("\n=== Electronics Model ===")

    df = pd.read_csv("data/all_baskets_details.csv")
    rows = []
    for _, row in df.iterrows():
        product_ids = ast.literal_eval(row['product_ids'])
        categories = ast.literal_eval(row['categories'])
        for pid, cat in zip_longest(product_ids, categories):
            rows.append({
                'product_id': pid,
                'category': cat,
                'basket_id': row['basket_id'],
                'box_number': row['box_number'],
                'box_name': row['box_name'],
                'company': row['company'],
                'price': row['price'],
                'utilization': row['utilization'],
                'box_type': row['box_type']
            })

    df_products = pd.DataFrame(rows)

    # Fill missing categories from product_final.csv
    df_final = pd.read_csv("../data/product_final.csv")
    mask_missing = df_products['category'].isna() | (df_products['category'] == 'None')
    df_products.loc[mask_missing, 'category'] = df_products.loc[mask_missing, 'product_id'].map(
        df_final.set_index('product_id')['category']
    )

    # Rule-based electronics label
    electronics_categories = ['Electronics', 'Appliance', 'Electrical', 'Phone', 'Laptop', 'Tablet']
    df_products['is_electronics_rule'] = df_products['category'].apply(lambda x: 1 if x in electronics_categories else 0)

    # Extract ML features
    result = extract_features_for_electronics(df_products, fit=True)
    X_elec = result[0] if isinstance(result, tuple) else result
    X_elec_numeric = X_elec.select_dtypes(include=['int64', 'float64', 'bool'])
    y_elec = df_products['is_electronics_rule']

    # Train ML model
    electronics_model = LGBMClassifier(
        n_estimators=300,
        learning_rate=0.1,
        class_weight='balanced',
        random_state=42
    )
    electronics_model.fit(X_elec_numeric, y_elec)

    # Save model and feature list
    os.makedirs("models", exist_ok=True)
    joblib.dump(electronics_model, "models/electronics_model.pkl")
    joblib.dump(X_elec_numeric.columns.tolist(), "models/electronics_feature_cols.pkl")
    print("✅ Electronics model and features saved")

    # Hybrid (rule + ML) predictions
    probs = electronics_model.predict_proba(X_elec_numeric)[:, 1]
    df_products['is_electronics_pred'] = (probs >= 0.6).astype(int)
    df_products['is_electronics_final'] = df_products.apply(
        lambda row: 1 if row['is_electronics_rule'] == 1 else row['is_electronics_pred'],
        axis=1
    )

    # Save updated CSV
    new_output_path = "data/products_train_updated.csv"
    df_products.to_csv(new_output_path, index=False)
    print(f"✅ Updated product-level CSV saved: {new_output_path}")

    # === LOAD DATASET for other models ===
    X_train, X_test, y_box_train, y_box_test, y_company_train, y_company_test, y_price_train, y_price_test, mlb = load_dataset()

    # Label encoders
    le_box = LabelEncoder()
    y_box_train_enc = le_box.fit_transform(y_box_train)
    y_box_test_enc = np.array([le_box.transform([y])[0] if y in le_box.classes_ else -1 for y in y_box_test])

    le_company = LabelEncoder()
    y_company_train_enc = le_company.fit_transform(y_company_train)
    y_company_test_enc = np.array([le_company.transform([y])[0] if y in le_company.classes_ else -1 for y in y_company_test])

    # === BOX MODEL ===
    print("\n=== Box Model ===")
    best_box, box_acc = evaluate_classifiers(X_train, X_test, y_box_train_enc, y_box_test_enc)
    joblib.dump(best_box, "models/best_box_model.pkl")
    joblib.dump(list(X_train.columns), "models/best_box_feature_cols.pkl")
    print("✅ Box model and feature columns saved")

    # === COMPANY MODEL ===
    print("\n=== Company Model ===")
    best_company, company_acc = evaluate_classifiers(X_train, X_test, y_company_train_enc, y_company_test_enc)
    joblib.dump(best_company, "models/best_company_model.pkl")
    joblib.dump(list(X_train.columns), "models/best_company_feature_cols.pkl")
    print("✅ Company model and feature columns saved")

    # === PRICE MODEL ===
    print("\n=== Price Model ===")
    best_price, price_mae = evaluate_regressors(X_train, X_test, y_price_train, y_price_test)
    joblib.dump(best_price, "models/best_price_model.pkl")
    joblib.dump(list(X_train.columns), "models/best_price_feature_cols.pkl")
    print("✅ Price model and feature columns saved")

    # Save encoders and binarizer
    joblib.dump(mlb, "models/mlb.pkl")
    joblib.dump(le_box, "models/le_box.pkl")
    joblib.dump(le_company, "models/le_company.pkl")

    print("\n✅ All models saved successfully.")
    print(f"Box Accuracy: {box_acc:.4f}")
    print(f"Company Accuracy: {company_acc:.4f}")
    print(f"Price MAE: {price_mae:.2f}")


if __name__ == "__main__":
    train_best_models()
