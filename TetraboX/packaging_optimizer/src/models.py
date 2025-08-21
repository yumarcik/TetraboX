from dataclasses import dataclass
from typing import Optional, Literal

Fragility = bool
HazmatClass = Optional[str]
PackagingType = Literal["kutu","poşet","şişe","kavanoz","zarf"]
MaterialType = Literal["karton","kraft","plastik","tahta"]

@dataclass
class Product:
    sku: str
    width_mm: float
    length_mm: float
    height_mm: float
    weight_g: float
    fragile: Fragility
    packaging_type: PackagingType
    hazmat_class: HazmatClass
    extra_pack: bool
    extra_pack_width_mm: Optional[float] = None
    extra_pack_length_mm: Optional[float] = None
    extra_pack_price_try: Optional[float] = None
    extra_pack_type: Optional[str] = None

@dataclass
class Container:
    box_id: str
    inner_w_mm: float
    inner_l_mm: float
    inner_h_mm: float
    tare_weight_g: float
    max_weight_g: float
    material: MaterialType
    stock: int
    price_try: float
    usage_limit: Optional[str] = None
