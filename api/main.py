# main.py
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import pandas as pd
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))  # bir üst dizin

# --- Packing fonksiyonunu import et ---
from packing_optimizer.packing_optimizer import assign_boxes_to_baskets

# --- FastAPI uygulaması ---
app = FastAPI(title="TetraBoX Packing API")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
products = pd.read_csv(os.path.join(BASE_DIR, "data", "products_final.csv"))
boxes = pd.read_excel(os.path.join(BASE_DIR, "data", "boxes_final.xlsx"))

# --- Kutuları ata ---
products = assign_boxes_to_baskets(products, boxes)

# --- Pydantic modeli (POST için) ---
class BasketRequest(BaseModel):
    basket_id: int

# --- GET endpoint: /pack?basket_id=xxxx ---
@app.get("/pack")
def get_basket_pack(basket_id: int):
    basket_products = products[products['basket_id'] == basket_id]
    if basket_products.empty:
        return {"detail": "Basket not found"}
    return basket_products[["product_id", "quantity", "assigned_box"]].to_dict(orient="records")

# --- POST endpoint: JSON ile basket_id ver ---
@app.post("/pack")
def post_basket_pack(request: BasketRequest):
    basket_id = request.basket_id
    basket_products = products[products['basket_id'] == basket_id]
    if basket_products.empty:
        return {"detail": "Basket not found"}
    return basket_products[["product_id", "quantity", "assigned_box"]].to_dict(orient="records")

# --- HTML form endpoint ---
@app.get("/pack_form", response_class=HTMLResponse)
def pack_form():
    return """
    <form action="/pack_form_result" method="post">
        Basket ID: <input type="number" name="basket_id" required>
        <input type="submit" value="Get Pack Info">
    </form>
    """

@app.post("/pack_form_result")
def pack_form_result(basket_id: int = Form(...)):
    basket_products = products[products['basket_id'] == basket_id]
    if basket_products.empty:
        return HTMLResponse(content="<h3>Basket not found</h3>", status_code=404)
    # Basit HTML tablo ile göster
    html_content = "<h3>Basket ID: {}</h3>".format(basket_id)
    html_content += "<table border='1'><tr><th>Product ID</th><th>Quantity</th><th>Assigned Box</th></tr>"
    for _, row in basket_products.iterrows():
        html_content += f"<tr><td>{row['product_id']}</td><td>{row['quantity']}</td><td>{row['assigned_box']}</td></tr>"
    html_content += "</table>"
    return HTMLResponse(content=html_content)
