import pandas as pd
import numpy as np


# -----------------------------
# Feature extraction for electronics
# -----------------------------
def extract_features_for_electronics(df: pd.DataFrame, fit=True, feature_cols_train=None) -> pd.DataFrame:
    X = pd.DataFrame()

    # Example features (you can add your own logic)
    X['price'] = df['price']
    X['utilization'] = df['utilization']
    X['is_known_category'] = (~df['category'].isna()).astype(int)

    if feature_cols_train is not None:
        # Add missing columns and reorder to match training
        missing_cols = set(feature_cols_train) - set(X.columns)
        for col in missing_cols:
            X[col] = 0
        X = X.reindex(columns=feature_cols_train, fill_value=0)

    return X


# -----------------------------
# Feature extraction for boxes
# -----------------------------
def extract_features_for_box(df: pd.DataFrame, fit=True, feature_cols_train=None) -> pd.DataFrame:
    X = pd.DataFrame()
    X['weight'] = df.get('weight', 0)
    X['volume'] = df.get('length', 0) * df.get('width', 0) * df.get('height', 0)
    X['price'] = df['price']
    X['utilization'] = df['utilization']
    X['electronics_count'] = df['is_electronics_final']

    # Example categorical one-hot encoding
    categories = df['category'].fillna('Unknown').unique()
    for cat in categories:
        col_name = f"cat_{cat}"
        X[col_name] = (df['category'] == cat).astype(int)

    if feature_cols_train is not None:
        missing_cols = set(feature_cols_train) - set(X.columns)
        for col in missing_cols:
            X[col] = 0
        X = X.reindex(columns=feature_cols_train, fill_value=0)

    return X


# -----------------------------
# Feature extraction for companies
# -----------------------------
def extract_features_for_company(df: pd.DataFrame, fit=True, feature_cols_train=None) -> pd.DataFrame:
    X = pd.DataFrame()
    X['electronics_count'] = df['is_electronics_final']
    X['total_price'] = df['price']

    if feature_cols_train is not None:
        missing_cols = set(feature_cols_train) - set(X.columns)
        for col in missing_cols:
            X[col] = 0
        X = X.reindex(columns=feature_cols_train, fill_value=0)

    return X


# -----------------------------
# Feature extraction for price
# -----------------------------
def extract_features_for_price(df: pd.DataFrame, fit=True, feature_cols_train=None) -> pd.DataFrame:
    X = pd.DataFrame()
    X['electronics_count'] = df['is_electronics_final']
    X['pred_box'] = df.get('pred_box', 1)
    X['pred_company'] = df.get('pred_company', 0)
    X['weight'] = df.get('weight', 0)
    X['volume'] = df.get('length', 0) * df.get('width', 0) * df.get('height', 0)
    X['price'] = df['price']
    X['utilization'] = df['utilization']

    if feature_cols_train is not None:
        missing_cols = set(feature_cols_train) - set(X.columns)
        for col in missing_cols:
            X[col] = 0
        X = X.reindex(columns=feature_cols_train, fill_value=0)

    return X
