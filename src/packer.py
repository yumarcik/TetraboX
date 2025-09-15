from typing import List, Tuple, Optional
from .models import Product, Container, PlacementItem, PackedContainer


def orientations(w: float, l: float, h: float):
	# All axis permutations; return unique sizes with rotation indices
	perms = [
		(w, l, h, (0,1,2)), (w, h, l, (0,2,1)),
		(l, w, h, (1,0,2)), (l, h, w, (1,2,0)),
		(h, w, l, (2,0,1)), (h, l, w, (2,1,0)),
	]
	seen = set()
	for ow, ol, oh, rot in perms:
		key = (ow, ol, oh)
		if key in seen: continue
		seen.add(key)
		yield ow, ol, oh, rot


def pack(products: List[Product], container: Container) -> Optional[PackedContainer]:
	"""
	Improved 3D bin packing algorithm with better space utilization.
	Uses a more sophisticated approach than simple shelf packing.
	"""
	if not products:
		return PackedContainer(
			box_id=container.box_id,
			inner_w_mm=container.inner_w_mm,
			inner_l_mm=container.inner_l_mm,
			inner_h_mm=container.inner_h_mm,
			placements=[],
		)
	
	placements: List[PlacementItem] = []
	
	# Sort products by volume (largest first) for better packing
	sorted_products = sorted(products, key=lambda p: p.width_mm * p.length_mm * p.height_mm, reverse=True)
	
	# Keep track of occupied spaces
	occupied_spaces = []
	
	for product in sorted_products:
		best_position = None
		best_orientation = None
		best_fitness = float('inf')
		
		# Try all orientations for this product
		for ow, ol, oh, rot in orientations(product.width_mm, product.length_mm, product.height_mm):
			# Skip if product doesn't fit in container at all
			if ow > container.inner_w_mm or ol > container.inner_l_mm or oh > container.inner_h_mm:
				continue
			
			# Try different positions
			positions_to_try = generate_candidate_positions(occupied_spaces, container, ow, ol, oh)
			
			for x, y, z in positions_to_try:
				# Check if position is valid (within container bounds)
				if (x + ow <= container.inner_w_mm and 
					y + ol <= container.inner_l_mm and 
					z + oh <= container.inner_h_mm):
					
					# Check if position conflicts with existing items
					if not conflicts_with_existing(x, y, z, ow, ol, oh, occupied_spaces):
						# Calculate fitness (prefer lower positions, then corner positions)
						fitness = calculate_position_fitness(x, y, z, ow, ol, oh, container)
						
						if fitness < best_fitness:
							best_fitness = fitness
							best_position = (x, y, z)
							best_orientation = (ow, ol, oh, rot)
		
		# If we found a valid position, place the item
		if best_position and best_orientation:
			x, y, z = best_position
			ow, ol, oh, rot = best_orientation
			
			placements.append(PlacementItem(
				sku=product.sku,
				position_mm=(x, y, z),
				size_mm=(ow, ol, oh),
				rotation=rot
			))
			
			# Add to occupied spaces
			occupied_spaces.append((x, y, z, x + ow, y + ol, z + oh))
		else:
			# Could not place this item
			return None
	
	return PackedContainer(
		box_id=container.box_id,
		inner_w_mm=container.inner_w_mm,
		inner_l_mm=container.inner_l_mm,
		inner_h_mm=container.inner_h_mm,
		placements=placements,
	)


def generate_candidate_positions(occupied_spaces, container, item_w, item_l, item_h):
	"""Generate candidate positions where an item might fit."""
	candidates = [(0, 0, 0)]  # Always try origin
	
	# Generate positions based on existing items
	for x1, y1, z1, x2, y2, z2 in occupied_spaces:
		# Try positions adjacent to existing items
		potential_positions = [
			(x2, y1, z1),  # Right of item
			(x1, y2, z1),  # Behind item  
			(x1, y1, z2),  # Above item
			(x2, y2, z1),  # Corner positions
			(x2, y1, z2),
			(x1, y2, z2),
			(x2, y2, z2),
		]
		candidates.extend(potential_positions)
	
	# Remove duplicates and invalid positions
	valid_candidates = []
	seen = set()
	
	for x, y, z in candidates:
		if (x, y, z) in seen:
			continue
		seen.add((x, y, z))
		
		# Check if position is within container bounds
		if (x >= 0 and y >= 0 and z >= 0 and
			x + item_w <= container.inner_w_mm and
			y + item_l <= container.inner_l_mm and
			z + item_h <= container.inner_h_mm):
			valid_candidates.append((x, y, z))
	
	# Sort by preference (lower positions first, then closer to origin)
	valid_candidates.sort(key=lambda pos: (pos[2], pos[1], pos[0]))
	
	return valid_candidates


def conflicts_with_existing(x, y, z, w, l, h, occupied_spaces):
	"""Check if a box at position (x,y,z) with size (w,l,h) conflicts with existing items."""
	item_x1, item_y1, item_z1 = x, y, z
	item_x2, item_y2, item_z2 = x + w, y + l, z + h
	
	for ox1, oy1, oz1, ox2, oy2, oz2 in occupied_spaces:
		# Check for 3D overlap
		if (item_x1 < ox2 and item_x2 > ox1 and
			item_y1 < oy2 and item_y2 > oy1 and
			item_z1 < oz2 and item_z2 > oz1):
			return True
	
	return False


def calculate_position_fitness(x, y, z, w, l, h, container):
	"""Calculate fitness score for a position (lower is better)."""
	# Prefer positions that are:
	# 1. Lower (smaller z)
	# 2. Closer to corners
	# 3. More stable (supported by other items or bottom)
	
	# Distance from bottom-left-front corner
	corner_distance = (x**2 + y**2 + z**2) ** 0.5
	
	# Height penalty (prefer lower positions)
	height_penalty = z * 10
	
	# Stability bonus for ground level
	stability_bonus = -100 if z == 0 else 0
	
	return corner_distance + height_penalty + stability_bonus


def pack_multi_container(products: List[Product], containers: List[Container]) -> Optional[List[Tuple[Container, PackedContainer]]]:
	"""
	Cost-optimized multi-container packing with maximum utilization.
	Tries different container combinations to find the most cost-effective solution.
	"""
	if not products or not containers:
		return None
	
	# Sort containers by cost per volume (best value first)
	def cost_per_volume(container):
		volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm / 1000.0  # cm³
		price = container.price_try or 0
		return price / volume if volume > 0 else float('inf')
	
	sorted_containers = sorted(containers, key=cost_per_volume)
	
	# Try different strategies and pick the best one
	strategies = []
	
	# Strategy 1: Greedy - Fill each container to maximum capacity
	greedy_result = pack_greedy_max_utilization(products, sorted_containers)
	if greedy_result:
		total_cost = sum(container.price_try or 0 for container, _ in greedy_result)
		strategies.append(("greedy", greedy_result, total_cost))
	
	# Strategy 2: Largest containers first (current approach but improved)
	large_first_result = pack_largest_first_optimized(products, containers)
	if large_first_result:
		total_cost = sum(container.price_try or 0 for container, _ in large_first_result)
		strategies.append(("large_first", large_first_result, total_cost))
	
	# Strategy 3: Best fit - try to minimize wasted space
	best_fit_result = pack_best_fit(products, sorted_containers)
	if best_fit_result:
		total_cost = sum(container.price_try or 0 for container, _ in best_fit_result)
		strategies.append(("best_fit", best_fit_result, total_cost))
	
	if not strategies:
		return None
	
	# Pick the strategy with lowest total cost
	best_strategy = min(strategies, key=lambda x: x[2])
	
	return best_strategy[1]


def pack_greedy_max_utilization(products: List[Product], containers: List[Container]) -> Optional[List[Tuple[Container, PackedContainer]]]:
	"""Greedy approach: Fill each container to maximum capacity before moving to next."""
	remaining_products = products.copy()
	packed_containers = []
	
	while remaining_products:
		best_pack = None
		best_container = None
		best_count = 0
		
		# Try each container type to find the one that packs the most items
		for container in containers:
			result = pack(remaining_products, container)
			if result and len(result.placements) > best_count:
				best_pack = result
				best_container = container
				best_count = len(result.placements)
		
		if not best_pack:
			return None
		
		# Add this container to solution
		packed_containers.append((best_container, best_pack))
		
		# Remove packed items
		packed_skus = [p.sku for p in best_pack.placements]
		for sku in packed_skus:
			for i, product in enumerate(remaining_products):
				if product.sku == sku:
					remaining_products.pop(i)
					break
	
	return packed_containers


def pack_largest_first_optimized(products: List[Product], containers: List[Container]) -> Optional[List[Tuple[Container, PackedContainer]]]:
	"""Try largest containers first but with better item distribution."""
	# Sort containers by volume (largest first)
	sorted_containers = sorted(containers, key=lambda c: c.inner_w_mm * c.inner_l_mm * c.inner_h_mm, reverse=True)
	
	remaining_products = products.copy()
	packed_containers = []
	
	while remaining_products:
		best_pack = None
		best_container = None
		best_efficiency = 0.0
		
		for container in sorted_containers:
			result = pack(remaining_products, container)
			if result and len(result.placements) > 0:
				# Calculate efficiency (items packed / container cost)
				items_packed = len(result.placements)
				container_cost = container.price_try or 1
				efficiency = items_packed / container_cost
				
				if efficiency > best_efficiency:
					best_pack = result
					best_container = container
					best_efficiency = efficiency
		
		if not best_pack:
			return None
		
		packed_containers.append((best_container, best_pack))
		
		# Remove packed items
		packed_skus = [p.sku for p in best_pack.placements]
		for sku in packed_skus:
			for i, product in enumerate(remaining_products):
				if product.sku == sku:
					remaining_products.pop(i)
					break
	
	return packed_containers


def pack_best_fit(products: List[Product], containers: List[Container]) -> Optional[List[Tuple[Container, PackedContainer]]]:
	"""Best fit approach: minimize wasted space."""
	remaining_products = products.copy()
	packed_containers = []
	
	while remaining_products:
		best_pack = None
		best_container = None
		best_waste_ratio = float('inf')
		
		for container in containers:
			result = pack(remaining_products, container)
			if result and len(result.placements) > 0:
				# Calculate waste ratio
				used_volume = sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] for p in result.placements)
				container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm
				waste_ratio = (container_volume - used_volume) / container_volume if container_volume > 0 else 1
				
				# Prefer containers that waste less space
				if waste_ratio < best_waste_ratio:
					best_pack = result
					best_container = container
					best_waste_ratio = waste_ratio
		
		if not best_pack:
			return None
		
		packed_containers.append((best_container, best_pack))
		
		# Remove packed items
		packed_skus = [p.sku for p in best_pack.placements]
		for sku in packed_skus:
			for i, product in enumerate(remaining_products):
				if product.sku == sku:
					remaining_products.pop(i)
					break
	
	return packed_containers


def find_optimal_multi_packing(products: List[Product], containers: List[Container]) -> Optional[List[Tuple[Container, PackedContainer]]]:
	"""
	Find the most cost-effective multi-container packing solution.
	First tries single container, then multi-container if needed.
	Only uses 3D boxes for packing (filters out 2D packaging materials).
	"""
	# Filter containers to only include 3D boxes
	box_containers = [c for c in containers if c.is_3d_box]
	
	if not box_containers:
		return None
	
	# Try single container first (existing logic)
	for container in sorted(box_containers, key=lambda c: c.price_try or 0):
		result = pack(products, container)
		if result:
			return [(container, result)]
	
	# If single container fails, try multi-container
	return pack_multi_container(products, box_containers)
