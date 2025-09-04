import pandas as pd
import numpy as np

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 300)
pd.set_option("display.max_colwidth", None)


def load_data(products_path: str, boxes_path: str):
    """
    Loads the product and box datasets
    """
    # Boxes
    boxes_df = pd.read_excel(boxes_path)

    # Products
    boxes_df['boxes_id'] = boxes_df['boxes_id'].astype(int)

    # Products
    products_df = pd.read_csv(products_path)

    return products_df, boxes_df


def assign_boxes_to_baskets(products_df, boxes_df):
    """
    Places products into boxes for each basket_id.
    - If all products fit into a single box, assigns that box.
    - If they don't fit, marks them as MULTI_BOX_NEEDED.
    """
    products_df['assigned_box'] = None

    for basket_id, basket_group in products_df.groupby('basket_id'):
        total_volume = basket_group['volume_cm3'].sum()
        total_weight = basket_group['weight_kg'].sum()

        suitable_boxes = boxes_df[
            (boxes_df['volume_cm3'] >= total_volume) &
            (boxes_df['max_weight_kg'] >= total_weight)
            ]

        if not suitable_boxes.empty:
            chosen_box = suitable_boxes.loc[suitable_boxes['volume_cm3'].idxmin()]
            products_df.loc[products_df['basket_id'] == basket_id, 'assigned_box'] = chosen_box['box_name']
        else:
            for idx, product_row in basket_group.iterrows():
                product_suitable_boxes = boxes_df[
                    (boxes_df['width_cm'] >= product_row['width_cm']) &
                    (boxes_df['length_cm'] >= product_row['length_cm']) &
                    (boxes_df['height_cm'] >= product_row['height_cm_filled']) &
                    (boxes_df['max_weight_kg'] >= product_row['weight_kg'])
                    ]
                if not product_suitable_boxes.empty:
                    chosen_box = product_suitable_boxes.loc[product_suitable_boxes['volume_cm3'].idxmin()]
                    products_df.at[idx, 'assigned_box'] = chosen_box['box_name']
                else:
                    products_df.at[idx, 'assigned_box'] = 'MULTI_BOX_NEEDED'

    return products_df


if __name__ == "__main__":
    products_path = "../data/products_final.csv"
    boxes_path = "../data/boxes_final.xlsx"

    products, boxes = load_data(products_path, boxes_path)
    products = assign_boxes_to_baskets(products, boxes)

    # Example
    basket_example = 2001
    print(products[products['basket_id'] == basket_example][
              ['basket_id','product_id', 'quantity', 'assigned_box']])

    # Save the dataset
    #products.to_csv("../data/products_with_boxes.csv", index=False)
