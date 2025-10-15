from typing import List, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime


class APIProduct(BaseModel):
	sku: str
	width_mm: float
	length_mm: float
	height_mm: float
	weight_g: float
	fragile: bool = False
	packaging_type: Optional[str] = None
	hazmat_class: Optional[str] = None


class APIContainer(BaseModel):
	box_id: str
	inner_w_mm: float
	inner_l_mm: float
	inner_h_mm: float
	tare_weight_g: float
	max_weight_g: float
	material: Optional[str] = None
	price_try: Optional[float] = None
	stock: int = 1
	usage_limit: Optional[str] = None


class PackRequest(BaseModel):
	order_id: str = Field(..., description="Client order identifier")
	products: List[APIProduct]
	containers: List[APIContainer]


class Placement(BaseModel):
	sku: str
	position_mm: Tuple[float, float, float]
	size_mm: Tuple[float, float, float]
	rotation: Tuple[int, int, int]


class PackResponse(BaseModel):
	order_id: str
	box_id: Optional[str]
	placements: List[Placement]
	utilization: float
	price_try: Optional[float]


# Order-based API models
class OrderItem(BaseModel):
	sku: str
	quantity: int = Field(ge=1)


class OrderPackRequest(BaseModel):
	order_id: str
	items: List[OrderItem]


class ContainerResult(BaseModel):
	container_id: str
	container_name: Optional[str] = None
	shipping_company: Optional[str] = None
	container_material: Optional[str] = None
	container_type: str = "box"  # "box" for 3D containers, "envelope" for 2D packaging
	placements: List[Placement]
	utilization: float
	remaining_volume_cm3: float
	container_volume_cm3: float
	price_try: Optional[float] = None
	inner_w_mm: Optional[float] = None
	inner_l_mm: Optional[float] = None
	inner_h_mm: Optional[float] = None

class OrderPackResponse(BaseModel):
	order_id: str
	success: bool
	containers: List[ContainerResult] = []
	total_price: float = 0.0
	total_items: int = 0
	container_count: int = 0
	# Legacy fields for backward compatibility
	box_id: Optional[str] = None
	placements: List[Placement] = []
	utilization: float = 0.0
	remaining_volume_cm3: float = 0.0
	container_volume_cm3: float = 0.0
	price_try: Optional[float] = None
	used_container_id: Optional[str] = None
	container_name: Optional[str] = None
	shipping_company: Optional[str] = None
	container_material: Optional[str] = None
	inner_w_mm: Optional[float] = None
	inner_l_mm: Optional[float] = None
	inner_h_mm: Optional[float] = None


# Order Management API models
class APIOrderItem(BaseModel):
	sku: str
	quantity: int = Field(ge=1)
	unit_price_try: Optional[float] = None
	total_price_try: Optional[float] = None


class CreateOrderRequest(BaseModel):
	customer_name: str = Field(..., min_length=1)
	customer_email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
	items: List[APIOrderItem]
	notes: Optional[str] = None


class UpdateOrderRequest(BaseModel):
	customer_name: Optional[str] = None
	customer_email: Optional[str] = None
	items: Optional[List[APIOrderItem]] = None
	notes: Optional[str] = None


class OrderResponse(BaseModel):
	order_id: str
	customer_name: str
	customer_email: str
	order_date: datetime
	items: List[APIOrderItem]
	total_items: int
	total_price_try: float
	shipping_company: Optional[str] = None
	container_count: int = 0
	utilization_avg: float = 0.0
	notes: Optional[str] = None


class OrderListResponse(BaseModel):
	orders: List[OrderResponse]
	total_count: int 