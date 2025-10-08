import pandas as pd
from pathlib import Path
from typing import List
from datetime import datetime
from .models import Product, Container, Order, OrderItem


def load_products_csv(path: str) -> List[Product]:
	p = Path(path)
	if not p.exists():
		raise FileNotFoundError(f"Products CSV not found: {path}")
	# Try reading with common options (semicolon + comma decimals), fallback to default
	try:
		df = pd.read_csv(p, sep=';', decimal=',')
	except Exception:
		df = pd.read_csv(p)
	# Helper to pick a column and return the series and a flag
	def pick(col_cm: str, col_mm: str):
		if col_cm in df.columns:
			return df[col_cm].astype(float), "cm"
		elif col_mm in df.columns:
			return df[col_mm].astype(float), "mm"
		else:
			return pd.Series([float('nan')]*len(df)), None
	# Unit converters
	to_mm = lambda x: float(x) * 10.0
	to_g = lambda x: float(x) * 1000.0
	w_raw, w_unit = pick("width_cm", "width_mm")
	l_raw, l_unit = pick("length_cm", "length_mm")
	h_raw, h_unit = pick("height_cm", "height_mm")
	wg_raw, wg_unit = pick("weight_kg", "weight_g")
	width_mm  = w_raw.map(lambda v: to_mm(v) if w_unit == "cm" else float(v))
	length_mm = l_raw.map(lambda v: to_mm(v) if l_unit == "cm" else float(v))
	height_mm = h_raw.map(lambda v: to_mm(v) if h_unit == "cm" else float(v))
	weight_g  = wg_raw.map(lambda v: to_g(v) if wg_unit == "kg" else float(v))
	fragile = (df["fragile"].astype(bool) if "fragile" in df.columns else pd.Series([False]*len(df)))
	# Support both packaging_type and package_type column names
	packaging_type = (df["packaging_type"] if "packaging_type" in df.columns 
	                 else df["package_type"] if "package_type" in df.columns 
	                 else pd.Series([None]*len(df)))
	# Support both hazmat_class and hazard_class column names
	hazmat = (df["hazmat_class"] if "hazmat_class" in df.columns 
	         else df["hazard_class"] if "hazard_class" in df.columns 
	         else pd.Series([None]*len(df)))
	skus = (df["sku"].astype(str) if "sku" in df.columns else pd.Series([f"SKU-{i+1:06d}" for i in range(len(df))]))
	products: List[Product] = []
	for i in range(len(df)):
		products.append(Product(
			sku=str(skus.iloc[i]),
			width_mm=float(width_mm.iloc[i]),
			length_mm=float(length_mm.iloc[i]),
			height_mm=float(height_mm.iloc[i]),
			weight_g=float(weight_g.iloc[i]),
			fragile=bool(fragile.iloc[i]),
			packaging_type=None if packaging_type is None else packaging_type.iloc[i],
			hazmat_class=None if hazmat is None else hazmat.iloc[i],
		))
	return products


def load_containers_csv(path: str) -> List[Container]:
	p = Path(path)
	if not p.exists():
		raise FileNotFoundError(f"Container CSV not found: {path}")
	df = pd.read_csv(p)
	def pick(col_cm: str, col_mm: str):
		if col_cm in df.columns:
			return df[col_cm].astype(float), "cm"
		elif col_mm in df.columns:
			return df[col_mm].astype(float), "mm"
		else:
			return pd.Series([float('nan')]*len(df)), None
	to_mm = lambda x: float(x) * 10.0
	to_g = lambda x: float(x) * 1000.0
	w_raw, w_unit = pick("width_cm", "inner_w_mm")
	l_raw, l_unit = pick("length_cm", "inner_l_mm")
	h_raw, h_unit = pick("height_cm", "inner_h_mm")
	w_mm = w_raw.map(lambda v: to_mm(v) if w_unit == "cm" else float(v))
	l_mm = l_raw.map(lambda v: to_mm(v) if l_unit == "cm" else float(v))
	h_mm = h_raw.map(lambda v: to_mm(v) if h_unit == "cm" else float(v))
	tare_g = (df["tare_weight_g"].astype(float) if "tare_weight_g" in df.columns else pd.Series([0.0]*len(df)))
	if "max_weight_kg" in df.columns:
		max_g = df["max_weight_kg"].astype(float).map(to_g)
	elif "max_weight_g" in df.columns:
		max_g = df["max_weight_g"].astype(float)
	else:
		max_g = pd.Series([float('nan')]*len(df))
	# Fallback for missing max weight: 10kg conservative default
	max_g = max_g.fillna(10000.0)
	material = (df["box_type"].astype(str) if "box_type" in df.columns else (df["material"].astype(str) if "material" in df.columns else pd.Series([None]*len(df))))
	price = (df["price"].astype(float) if "price" in df.columns else pd.Series([None]*len(df)))
	stock = (df["Stok"].fillna(1).astype(int) if "Stok" in df.columns else (df["stock"].fillna(1).astype(int) if "stock" in df.columns else pd.Series([1]*len(df))))
	box_id = (df["boxes_id"].astype(str) if "boxes_id" in df.columns else (df["box_id"].astype(str) if "box_id" in df.columns else pd.Series([f"BOX-{i+1:06d}" for i in range(len(df))])))
	box_name = (df["box_name"].astype(str) if "box_name" in df.columns else pd.Series([None]*len(df)))
	shipping_company = (df["shipping_company"].astype(str) if "shipping_company" in df.columns else pd.Series([None]*len(df)))
	items: List[Container] = []
	boxes_count = 0
	envelopes_count = 0
	
	for i in range(len(df)):
		# Get dimensions
		w_val = float(w_mm.iloc[i]) if not pd.isna(w_mm.iloc[i]) else 0
		l_val = float(l_mm.iloc[i]) if not pd.isna(l_mm.iloc[i]) else 0
		h_val = float(h_mm.iloc[i]) if not pd.isna(h_mm.iloc[i]) else 0
		
		# Skip containers with invalid width or length
		if w_val <= 0 or l_val <= 0:
			print(f"Skipping container {box_id.iloc[i]} with invalid width/length: {w_val}x{l_val}mm")
			continue
		
		# Determine container type based on height
		if h_val > 0:
			# 3D Box - has valid height
			container_type = "box"
			boxes_count += 1
		else:
			# 2D Packaging - envelope, bag, protective material (no height or height=0)
			container_type = "envelope"
			h_val = 1.0  # Set minimal height for 2D packaging (1mm thickness)
			envelopes_count += 1
		
		# Create more meaningful container ID
		name = str(box_name.iloc[i]) if not pd.isna(box_name.iloc[i]) else f"Container-{box_id.iloc[i]}"
		company = str(shipping_company.iloc[i]) if not pd.isna(shipping_company.iloc[i]) else ""
		meaningful_id = f"{company}-{name}" if company else name
		
		items.append(Container(
			box_id=meaningful_id,
			inner_w_mm=w_val,
			inner_l_mm=l_val,
			inner_h_mm=h_val,
			tare_weight_g=float(tare_g.iloc[i]) if not pd.isna(tare_g.iloc[i]) else 0.0,
			max_weight_g=float(max_g.iloc[i]) if not pd.isna(max_g.iloc[i]) else 10000.0,
			material=None if material is None else (None if pd.isna(material.iloc[i]) else str(material.iloc[i])),
			price_try=None if price is None else (None if pd.isna(price.iloc[i]) else float(price.iloc[i])),
			stock=int(stock.iloc[i]) if not pd.isna(stock.iloc[i]) else 1,
			box_name=None if pd.isna(box_name.iloc[i]) else str(box_name.iloc[i]),
			shipping_company=None if pd.isna(shipping_company.iloc[i]) else str(shipping_company.iloc[i]),
			container_type=container_type,
		))
	
	print(f"Loaded {len(items)} containers: {boxes_count} 3D boxes, {envelopes_count} 2D packaging materials")
	return items


def load_orders_csv(orders_path: str, order_items_path: str) -> List[Order]:
	"""Load orders from CSV files"""
	orders_p = Path(orders_path)
	items_p = Path(order_items_path)
	
	if not orders_p.exists():
		raise FileNotFoundError(f"Orders CSV not found: {orders_path}")
	if not items_p.exists():
		raise FileNotFoundError(f"Order items CSV not found: {order_items_path}")
	
	# Load orders
	orders_df = pd.read_csv(orders_p)
	items_df = pd.read_csv(items_p)
	
	orders: List[Order] = []
	
	for _, order_row in orders_df.iterrows():
		order_id = str(order_row['order_id'])
		
		# Get items for this order
		order_items_df = items_df[items_df['order_id'] == order_id]
		items = []
		
		for _, item_row in order_items_df.iterrows():
			items.append(OrderItem(
				sku=str(item_row['sku']),
				quantity=int(item_row['quantity']),
				unit_price_try=float(item_row['unit_price_try']) if pd.notna(item_row['unit_price_try']) else None,
				total_price_try=float(item_row['total_price_try']) if pd.notna(item_row['total_price_try']) else None
			))
		
		# Parse order date
		order_date = datetime.strptime(str(order_row['order_date']), '%Y-%m-%d %H:%M:%S')
		
		order = Order(
			order_id=order_id,
			customer_name=str(order_row['customer_name']),
			customer_email=str(order_row['customer_email']),
			order_date=order_date,
			status=str(order_row['status']),
			items=items,
			total_items=int(order_row['total_items']) if pd.notna(order_row['total_items']) else 0,
			total_price_try=float(order_row['total_price_try']) if pd.notna(order_row['total_price_try']) else 0.0,
			shipping_company=str(order_row['shipping_company']) if pd.notna(order_row['shipping_company']) else None,
			container_count=int(order_row['container_count']) if pd.notna(order_row['container_count']) else 0,
			utilization_avg=float(order_row['utilization_avg']) if pd.notna(order_row['utilization_avg']) else 0.0,
			notes=str(order_row['notes']) if pd.notna(order_row['notes']) else None
		)
		
		orders.append(order)
	
	return orders


def save_order_to_csv(order: Order, orders_path: str, order_items_path: str):
	"""Save a single order to CSV files"""
	orders_p = Path(orders_path)
	items_p = Path(order_items_path)
	
	# Prepare order data
	order_data = {
		'order_id': order.order_id,
		'customer_name': order.customer_name,
		'customer_email': order.customer_email,
		'order_date': order.order_date.strftime('%Y-%m-%d %H:%M:%S'),
		'status': order.status,
		'total_items': order.total_items,
		'total_price_try': order.total_price_try,
		'shipping_company': order.shipping_company,
		'container_count': order.container_count,
		'utilization_avg': order.utilization_avg,
		'notes': order.notes
	}
	
	# Prepare items data
	items_data = []
	for item in order.items:
		items_data.append({
			'order_id': order.order_id,
			'sku': item.sku,
			'quantity': item.quantity,
			'unit_price_try': item.unit_price_try,
			'total_price_try': item.total_price_try
		})
	
	# Load existing data or create new
	if orders_p.exists():
		orders_df = pd.read_csv(orders_p)
		# Remove existing order if it exists
		orders_df = orders_df[orders_df['order_id'] != order.order_id]
	else:
		orders_df = pd.DataFrame()
	
	if items_p.exists():
		items_df = pd.read_csv(items_p)
		# Remove existing items for this order
		items_df = items_df[items_df['order_id'] != order.order_id]
	else:
		items_df = pd.DataFrame()
	
	# Add new data
	new_order_df = pd.DataFrame([order_data])
	new_items_df = pd.DataFrame(items_data)
	
	orders_df = pd.concat([orders_df, new_order_df], ignore_index=True)
	items_df = pd.concat([items_df, new_items_df], ignore_index=True)
	
	# Save to CSV
	orders_df.to_csv(orders_p, index=False)
	items_df.to_csv(items_p, index=False)
