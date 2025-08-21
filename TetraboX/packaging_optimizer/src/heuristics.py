from typing import List, Optional
from .models import Product, Container
from .constraints import all_constraints

def choose_container(product: Product, containers: List[Container]) -> Optional[Container]:
    # Baseline: smallest feasible volume, then cheapest
    sorted_boxes = sorted(
        containers,
        key=lambda c: (c.inner_w_mm*c.inner_l_mm*c.inner_h_mm, c.price_try)
    )
    for c in sorted_boxes:
        if c.stock <= 0:
            continue
        if all_constraints(product, c):
            return c
    return None

def utilization(product: Product, container: Container) -> float:
    pv = product.width_mm*product.length_mm*product.height_mm/1000.0
    cv = container.inner_w_mm*container.inner_l_mm*container.inner_h_mm/1000.0
    return min(1.0, pv/cv) if cv > 0 else 0.0
