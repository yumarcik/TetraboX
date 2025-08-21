from .models import Product, Container

def fits_dimension(p: Product, c: Container) -> bool:
    # orientation-free check
    dims_p = sorted([p.width_mm, p.length_mm, p.height_mm])
    dims_c = sorted([c.inner_w_mm, c.inner_l_mm, c.inner_h_mm])
    return all(dp <= dc for dp, dc in zip(dims_p, dims_c))

def fits_weight(p: Product, c: Container) -> bool:
    return p.weight_g + c.tare_weight_g <= c.max_weight_g

def usage_allowed(p: Product, c: Container) -> bool:
    if c.usage_limit is None:
        return True
    if "sıvı-yasak" in str(c.usage_limit).lower() and p.packaging_type in ("şişe","kavanoz"):
        return False
    return True

def hazmat_ok(p: Product, c: Container) -> bool:
    if p.hazmat_class == "UN3481" and c.material == "plastik":
        return False
    return True

def fragile_ok(p: Product, c: Container) -> bool:
    if p.fragile and c.material == "plastik":
        return False
    return True

def all_constraints(p: Product, c: Container) -> bool:
    return (fits_dimension(p, c)
            and fits_weight(p, c)
            and usage_allowed(p, c)
            and hazmat_ok(p, c)
            and fragile_ok(p, c))
