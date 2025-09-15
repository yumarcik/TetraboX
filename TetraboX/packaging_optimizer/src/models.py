from dataclasses import dataclass
from typing import Optional, Tuple, List


@dataclass
class Product:
	sku: str
	width_mm: float
	length_mm: float
	height_mm: float
	weight_g: float
	fragile: bool = False
	packaging_type: Optional[str] = None
	hazmat_class: Optional[str] = None


@dataclass
class Container:
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
	box_name: Optional[str] = None
	shipping_company: Optional[str] = None
	container_type: str = "box"  # "box" for 3D containers, "envelope" for 2D packaging

	@property
	def is_3d_box(self) -> bool:
		"""Check if this container is a 3D box (has valid height)"""
		return self.container_type == "box" and self.inner_h_mm > 0

	@property
	def is_2d_packaging(self) -> bool:
		"""Check if this container is 2D packaging (envelope, bag, etc.)"""
		return self.container_type == "envelope"


@dataclass
class PlacementItem:
	sku: str
	position_mm: Tuple[float, float, float]
	size_mm: Tuple[float, float, float]
	rotation: Tuple[int, int, int]


@dataclass
class PackedContainer:
	box_id: str
	inner_w_mm: float
	inner_l_mm: float
	inner_h_mm: float
	placements: List[PlacementItem] 