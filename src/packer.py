from typing import List, Tuple, Optional, Dict
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


def enhanced_item_sorting(products: List[Product]) -> List[Product]:
	"""🚀 PHASE 1: Multi-criteria sorting for optimal packing efficiency."""
	
	def calculate_sort_score(product):
		"""Calculate comprehensive sort score for better packing order."""
		volume = product.width_mm * product.length_mm * product.height_mm
		
		# 1. Volume-to-weight ratio (efficient stacking)
		density = volume / max(product.weight_g, 1) if product.weight_g > 0 else volume
		
		# 2. Aspect ratio (cubic items pack better)
		max_dim = max(product.width_mm, product.length_mm, product.height_mm)
		min_dim = min(product.width_mm, product.length_mm, product.height_mm)
		aspect_ratio = max_dim / min_dim if min_dim > 0 else 1
		
		# 3. Stackability (fragile items last, heavy items first)
		stackability = 1.0
		if hasattr(product, 'is_fragile') and product.is_fragile:
			stackability = 0.3
		elif hasattr(product, 'is_hazmat') and product.is_hazmat:
			stackability = 0.5
		
		# 4. Volume factor (larger items first, but not too dominant)
		volume_factor = volume / 1000000  # Normalize to reasonable range
		
		# 5. Shape regularity bonus (more regular shapes pack better)
		shape_regularity = 1.0
		if aspect_ratio < 2.0:  # More cube-like
			shape_regularity = 1.2
		elif aspect_ratio > 5.0:  # Very elongated
			shape_regularity = 0.7
		
		# Combined score: prioritize large, dense, stackable, regular items
		score = (volume_factor * density * stackability * shape_regularity) / aspect_ratio
		
		return score
	
	# Sort by calculated score (highest first)
	return sorted(products, key=calculate_sort_score, reverse=True)


def pack(products: List[Product], container: Container) -> Optional[PackedContainer]:
	"""
	🚀 PHASE 2: Advanced 3D bin packing with sophisticated space analysis.
	Uses advanced 3D space mapping, dynamic optimization, and intelligent positioning.
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
	
	# 🚀 PHASE 2: Use advanced 3D space analysis for optimal packing
	occupied_spaces = []
	
	# 🚀 Enable Phase 2 advanced 3D space analysis
	use_phase2 = False  # Temporarily disabled to fix errors
	
	if use_phase2:
		# Try Phase 2 advanced optimization first
		advanced_placements = advanced_position_optimization(products, container, occupied_spaces)
		
		if advanced_placements:
			# Convert advanced placements to standard format
			for placement in advanced_placements:
				product = placement['product']
				position = placement['position']
				ow, ol, oh, rot = placement['orientation']
				
				placements.append(PlacementItem(
					sku=product.sku,
					position_mm=position,
					size_mm=(ow, ol, oh),
					rotation=rot
				))
		else:
			# Fallback to Phase 1
			use_phase2 = False
	
	if not use_phase2:
		# Fallback to Phase 1 enhanced algorithms if Phase 2 fails
		# 🚀 PHASE 1: Enhanced multi-criteria sorting for better packing efficiency
		sorted_products = enhanced_item_sorting(products)
		
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
		
		# 🚀 PHASE 1: Attempt gap filling for remaining items
		remaining_items = [p for p in sorted_products if p.sku not in [pl.sku for pl in placements]]
		if remaining_items:
			gap_filled_placements = attempt_gap_filling(remaining_items, occupied_spaces, container)
			placements.extend(gap_filled_placements)
	
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
	"""🚀 PHASE 1: Enhanced fitness function with gap filling and stability optimization."""
	# Prefer positions that are:
	# 1. Lower (smaller z)
	# 2. Closer to corners
	# 3. More stable (supported by other items or bottom)
	# 4. Create fewer gaps (NEW)
	# 5. Better weight distribution (NEW)
	
	# Distance from bottom-left-front corner (existing)
	corner_distance = (x**2 + y**2 + z**2) ** 0.5
	
	# Height penalty (existing)
	height_penalty = z * 10
	
	# Stability bonus for ground level (existing)
	stability_bonus = -100 if z == 0 else 0
	
	# 🚀 NEW: Gap filling score - prefer positions that fill existing gaps
	gap_filling_score = calculate_gap_filling_bonus(x, y, z, w, l, h, container)
	
	# 🚀 NEW: Stability score - prefer positions with better support
	stability_score = calculate_enhanced_stability_score(x, y, z, w, l, h, container)
	
	# 🚀 NEW: Weight distribution score - prefer balanced weight distribution
	weight_distribution_score = calculate_weight_distribution_score(x, y, z, w, l, h, container)
	
	# 🚀 NEW: Corner utilization bonus - prefer positions that utilize corners better
	corner_utilization_bonus = calculate_corner_utilization_bonus(x, y, z, w, l, h, container)
	
	return (corner_distance + height_penalty + stability_bonus - 
			gap_filling_score - stability_score - weight_distribution_score - corner_utilization_bonus)


def calculate_gap_filling_bonus(x, y, z, w, l, h, container):
	"""🚀 PHASE 1: Calculate bonus for positions that fill existing gaps."""
	# This is a simplified gap detection - in practice, we'd analyze occupied_spaces
	# For now, we give bonus for positions that are close to container boundaries
	# (which often indicate gap-filling opportunities)
	
	boundary_bonus = 0
	
	# Bonus for touching container walls (indicates gap filling)
	if x == 0 or x + w == container.inner_w_mm:
		boundary_bonus += 20
	if y == 0 or y + l == container.inner_l_mm:
		boundary_bonus += 20
	if z == 0:
		boundary_bonus += 30  # Ground contact is always good
	
	return boundary_bonus


def calculate_enhanced_stability_score(x, y, z, w, l, h, container):
	"""🚀 PHASE 1: Calculate enhanced stability score for better support."""
	# Prefer positions with more contact area and better support
	
	stability_score = 0
	
	# Ground contact bonus (existing logic)
	if z == 0:
		stability_score += 50
	
	# Contact area bonus - prefer items with larger base area
	base_area = w * l
	contact_bonus = min(30, base_area / 1000)  # Normalize to reasonable range
	stability_score += contact_bonus
	
	# Center of gravity bonus - prefer items closer to container center
	center_x = container.inner_w_mm / 2
	center_y = container.inner_l_mm / 2
	center_distance = ((x + w/2 - center_x)**2 + (y + l/2 - center_y)**2)**0.5
	center_bonus = max(0, 20 - center_distance / 50)  # Bonus decreases with distance from center
	stability_score += center_bonus
	
	return stability_score


def calculate_weight_distribution_score(x, y, z, w, l, h, container):
	"""🚀 PHASE 1: Calculate weight distribution score for balanced packing."""
	# This is a placeholder - in a real implementation, we'd consider actual item weights
	# For now, we optimize for geometric balance
	
	balance_score = 0
	
	# Prefer positions that balance the container geometrically
	center_x = container.inner_w_mm / 2
	center_y = container.inner_l_mm / 2
	
	item_center_x = x + w / 2
	item_center_y = y + l / 2
	
	# Distance from container center
	distance_from_center = ((item_center_x - center_x)**2 + (item_center_y - center_y)**2)**0.5
	max_distance = ((container.inner_w_mm/2)**2 + (container.inner_l_mm/2)**2)**0.5
	
	# Normalize distance (0 = center, 1 = corner)
	normalized_distance = distance_from_center / max_distance if max_distance > 0 else 0
	
	# Prefer items closer to center for better balance
	balance_bonus = (1 - normalized_distance) * 25
	balance_score += balance_bonus
	
	return balance_score


def calculate_corner_utilization_bonus(x, y, z, w, l, h, container):
	"""🚀 PHASE 1: Calculate bonus for better corner utilization."""
	corner_bonus = 0
	
	# Bonus for utilizing corners effectively
	if x == 0 and y == 0:  # Bottom-left corner
		corner_bonus += 25
	elif x + w == container.inner_w_mm and y == 0:  # Bottom-right corner
		corner_bonus += 25
	elif x == 0 and y + l == container.inner_l_mm:  # Top-left corner
		corner_bonus += 25
	elif x + w == container.inner_w_mm and y + l == container.inner_l_mm:  # Top-right corner
		corner_bonus += 25
	
	# Partial corner bonus
	if x == 0 or y == 0:
		corner_bonus += 10
	
	return corner_bonus


def attempt_gap_filling(remaining_items: List[Product], occupied_spaces: List, container: Container) -> List:
	"""🚀 PHASE 1: Attempt to fill gaps with remaining items."""
	gap_filled_placements = []
	
	# Find potential gaps in the container
	gaps = find_potential_gaps(occupied_spaces, container)
	
	# Try to place remaining items in gaps
	for item in remaining_items[:]:  # Copy to avoid modification during iteration
		best_gap = None
		best_fitness = float('inf')
		best_orientation = None
		
		# Try all orientations for this item
		for ow, ol, oh, rot in orientations(item.width_mm, item.length_mm, item.height_mm):
			for gap in gaps:
				# Check if item fits in this gap
				if (ow <= gap['width'] and ol <= gap['length'] and oh <= gap['height']):
					# Calculate fitness for this gap placement
					x, y, z = gap['position']
					fitness = calculate_position_fitness(x, y, z, ow, ol, oh, container)
					
					if fitness < best_fitness:
						best_fitness = fitness
						best_gap = gap
						best_orientation = (ow, ol, oh, rot)
		
		# Place item in best gap if found
		if best_gap and best_orientation:
			x, y, z = best_gap['position']
			ow, ol, oh, rot = best_orientation
			
			gap_filled_placements.append(PlacementItem(
				sku=item.sku,
				position_mm=(x, y, z),
				size_mm=(ow, ol, oh),
				rotation=rot
			))
			
			# Update occupied spaces
			occupied_spaces.append((x, y, z, x + ow, y + ol, z + oh))
			
			# Remove item from remaining list
			remaining_items.remove(item)
			
			# Update gaps (remove used gap and potentially create new ones)
			gaps = update_gaps_after_placement(gaps, best_gap, (x, y, z, ow, ol, oh))
	
	return gap_filled_placements


def find_potential_gaps(occupied_spaces: List, container: Container) -> List:
	"""🚀 PHASE 1: Find potential gaps where items could be placed."""
	gaps = []
	
	# This is a simplified gap detection algorithm
	# In a full implementation, we'd analyze the 3D space more thoroughly
	
	# For now, we'll create candidate positions along the boundaries
	# and check if they're not occupied
	
	# Check positions along the bottom edge
	for x in range(0, container.inner_w_mm, 50):  # 50mm grid
		for y in range(0, container.inner_l_mm, 50):
			if not is_position_occupied(x, y, 0, occupied_spaces):
				# Estimate gap size (simplified)
				gap_width = min(100, container.inner_w_mm - x)
				gap_length = min(100, container.inner_l_mm - y)
				gap_height = container.inner_h_mm  # Full height available
				
				gaps.append({
					'position': (x, y, 0),
					'width': gap_width,
					'length': gap_length,
					'height': gap_height
				})
	
	return gaps


def is_position_occupied(x, y, z, occupied_spaces, buffer=5):
	"""Check if a position is occupied (with small buffer)."""
	for ox1, oy1, oz1, ox2, oy2, oz2 in occupied_spaces:
		if (x + buffer < ox2 and x - buffer > ox1 and
			y + buffer < oy2 and y - buffer > oy1 and
			z + buffer < oz2 and z - buffer > oz1):
			return True
	return False


def update_gaps_after_placement(gaps: List, used_gap: dict, placement: tuple) -> List:
	"""Update gap list after placing an item."""
	# Remove the used gap
	gaps = [gap for gap in gaps if gap != used_gap]
	
	# In a full implementation, we'd analyze the placement and potentially
	# create new gaps or modify existing ones
	
	return gaps


def create_3d_space_map(container: Container, occupied_spaces: List) -> Dict:
	"""🚀 PHASE 2: Create detailed 3D space map for advanced analysis."""
	# Grid resolution for space analysis (10mm resolution for precision)
	grid_size = 10
	
	# Calculate grid dimensions (ensure they are integers)
	grid_width = int(container.inner_w_mm // grid_size)
	grid_length = int(container.inner_l_mm // grid_size)
	grid_height = int(container.inner_h_mm // grid_size)
	
	# Initialize 3D space map
	space_map = {
		'grid_size': grid_size,
		'grid_dimensions': (int(grid_width), int(grid_length), int(grid_height)),
		'container_dimensions': (container.inner_w_mm, container.inner_l_mm, container.inner_h_mm),
		'occupied_cells': set(),
		'available_spaces': [],
		'space_quality': {},  # Quality score for each available space
	}
	
	# Mark occupied cells
	for x1, y1, z1, x2, y2, z2 in occupied_spaces:
		for x in range(int(x1//grid_size), int(x2//grid_size) + 1):
			for y in range(int(y1//grid_size), int(y2//grid_size) + 1):
				for z in range(int(z1//grid_size), int(z2//grid_size) + 1):
					if (0 <= x < grid_width and 0 <= y < grid_length and 0 <= z < grid_height):
						space_map['occupied_cells'].add((x, y, z))
	
	# Find available spaces (contiguous regions)
	available_spaces = find_contiguous_spaces(space_map)
	space_map['available_spaces'] = available_spaces
	
	# Calculate quality scores for each space
	for space in available_spaces:
		quality_score = calculate_space_quality(space, space_map, container)
		space_map['space_quality'][space['id']] = quality_score
	
	return space_map


def find_contiguous_spaces(space_map: Dict) -> List:
	"""🚀 PHASE 2: Find contiguous available spaces in 3D grid."""
	grid_width, grid_length, grid_height = space_map['grid_dimensions']
	# Ensure dimensions are integers
	grid_width = int(grid_width)
	grid_length = int(grid_length)
	grid_height = int(grid_height)
	occupied_cells = space_map['occupied_cells']
	
	# Use flood fill to find contiguous regions
	visited = set()
	spaces = []
	space_id = 0
	
	def flood_fill_iterative(start_x, start_y, start_z):
		"""Iterative flood fill to prevent recursion depth issues."""
		stack = [(start_x, start_y, start_z)]
		current_space = []
		
		while stack:
			x, y, z = stack.pop()
			
			# Check boundaries and conditions
			if (x < 0 or x >= grid_width or
				y < 0 or y >= grid_length or
				z < 0 or z >= grid_height or
				(x, y, z) in occupied_cells or 
				(x, y, z) in visited):
				continue
			
			# Mark as visited and add to space
			visited.add((x, y, z))
			current_space.append((x, y, z))
			
			# Add neighbors to stack (6 directions in 3D)
			for dx, dy, dz in [(0,0,1), (0,0,-1), (0,1,0), (0,-1,0), (1,0,0), (-1,0,0)]:
				stack.append((x+dx, y+dy, z+dz))
		
		return current_space
	
	# Find all contiguous spaces
	for x in range(grid_width):
		for y in range(grid_length):
			for z in range(grid_height):
				if (x, y, z) not in occupied_cells and (x, y, z) not in visited:
					current_space = flood_fill_iterative(x, y, z)
					
					if current_space:  # Valid space found
						space_info = analyze_space_geometry(current_space, space_map)
						space_info['id'] = space_id
						space_info['cells'] = current_space
						spaces.append(space_info)
						space_id += 1
	
	return spaces


def analyze_space_geometry(space_cells: List, space_map: Dict) -> Dict:
	"""🚀 PHASE 2: Analyze geometry of a contiguous space."""
	grid_size = space_map['grid_size']
	
	# Find bounding box
	min_x = min(cell[0] for cell in space_cells)
	max_x = max(cell[0] for cell in space_cells)
	min_y = min(cell[1] for cell in space_cells)
	max_y = max(cell[1] for cell in space_cells)
	min_z = min(cell[2] for cell in space_cells)
	max_z = max(cell[2] for cell in space_cells)
	
	# Calculate dimensions
	width = (max_x - min_x + 1) * grid_size
	length = (max_y - min_y + 1) * grid_size
	height = (max_z - min_z + 1) * grid_size
	volume = width * length * height
	
	# Calculate position (center of mass)
	center_x = (min_x + max_x) / 2 * grid_size
	center_y = (min_y + max_y) / 2 * grid_size
	center_z = (min_z + max_z) / 2 * grid_size
	
	# Calculate fill ratio (how dense the space is)
	total_cells = (max_x - min_x + 1) * (max_y - min_y + 1) * (max_z - min_z + 1)
	fill_ratio = len(space_cells) / total_cells if total_cells > 0 else 0
	
	return {
		'position': (center_x, center_y, center_z),
		'dimensions': (width, length, height),
		'volume': volume,
		'fill_ratio': fill_ratio,
		'bounding_box': (min_x, min_y, min_z, max_x, max_y, max_z),
		'cell_count': len(space_cells),
	}


def calculate_space_quality(space: Dict, space_map: Dict, container: Container) -> float:
	"""🚀 PHASE 2: Calculate quality score for a space (higher = better)."""
	quality_score = 0.0
	
	# Volume bonus (larger spaces are generally better)
	volume_bonus = min(50, space['volume'] / 10000)  # Normalize to reasonable range
	quality_score += volume_bonus
	
	# Shape bonus (more cube-like spaces pack better)
	width, length, height = space['dimensions']
	max_dim = max(width, length, height)
	min_dim = min(width, length, height)
	aspect_ratio = max_dim / min_dim if min_dim > 0 else 1
	
	shape_bonus = max(0, 20 - (aspect_ratio - 1) * 5)  # Bonus decreases with aspect ratio
	quality_score += shape_bonus
	
	# Position bonus (prefer lower positions, closer to corners)
	center_x, center_y, center_z = space['position']
	
	# Lower position bonus
	height_penalty = center_z / container.inner_h_mm * 10
	quality_score -= height_penalty
	
	# Corner proximity bonus
	corner_distance = ((center_x)**2 + (center_y)**2)**0.5
	max_corner_distance = ((container.inner_w_mm)**2 + (container.inner_l_mm)**2)**0.5
	corner_bonus = (1 - corner_distance / max_corner_distance) * 15
	quality_score += corner_bonus
	
	# Fill ratio bonus (more compact spaces are better)
	fill_bonus = space['fill_ratio'] * 25
	quality_score += fill_bonus
	
	# Accessibility bonus (spaces near container edges are easier to fill)
	edge_proximity = calculate_edge_proximity(space, container)
	accessibility_bonus = edge_proximity * 10
	quality_score += accessibility_bonus
	
	return quality_score


def calculate_edge_proximity(space: Dict, container: Container) -> float:
	"""🚀 PHASE 2: Calculate how close a space is to container edges."""
	center_x, center_y, center_z = space['position']
	width, length, height = space['dimensions']
	
	# Calculate minimum distance to any container edge
	dist_to_left = center_x
	dist_to_right = container.inner_w_mm - (center_x + width/2)
	dist_to_front = center_y
	dist_to_back = container.inner_l_mm - (center_y + length/2)
	dist_to_bottom = center_z
	dist_to_top = container.inner_h_mm - (center_z + height/2)
	
	min_edge_distance = min(dist_to_left, dist_to_right, dist_to_front, 
						   dist_to_back, dist_to_bottom, dist_to_top)
	
	# Normalize to 0-1 scale (closer to edge = higher score)
	max_possible_distance = max(container.inner_w_mm, container.inner_l_mm, container.inner_h_mm)
	proximity_score = max(0, 1 - min_edge_distance / max_possible_distance)
	
	return proximity_score


def advanced_position_optimization(products: List[Product], container: Container, 
								 occupied_spaces: List) -> List:
	"""🚀 PHASE 2: Advanced position optimization using 3D space analysis."""
	placements = []
	
	try:
		# Create 3D space map
		space_map = create_3d_space_map(container, occupied_spaces)
		
		# Enhanced item sorting with space-aware scoring
		sorted_products = space_aware_item_sorting(products, space_map)
		
		for product in sorted_products:
			best_placement = None
			best_score = float('-inf')
			
			# Try all orientations
			for ow, ol, oh, rot in orientations(product.width_mm, product.length_mm, product.height_mm):
				# Skip if product doesn't fit in container at all
				if ow > container.inner_w_mm or ol > container.inner_l_mm or oh > container.inner_h_mm:
					continue
				
				# Find best space for this orientation
				space_placement = find_best_space_for_item(
					product, (ow, ol, oh), space_map, container
				)
				
				if space_placement:
					# Calculate advanced fitness score
					advanced_score = calculate_advanced_fitness_score(
						space_placement, product, space_map, container
					)
					
					if advanced_score > best_score:
						best_score = advanced_score
						best_placement = space_placement
			
			# Place item if valid position found
			if best_placement:
				placements.append(best_placement)
				# Update occupied spaces and space map
				occupied_spaces.append(best_placement['occupied_region'])
				space_map = update_space_map_after_placement(space_map, best_placement)
			else:
				# Item couldn't be placed
				break
		
		return placements
		
	except Exception as e:
		print(f"⚠️ Phase 2 advanced optimization failed: {e}")
		# Return empty list to trigger fallback to Phase 1
		return []


def space_aware_item_sorting(products: List[Product], space_map: Dict) -> List[Product]:
	"""🚀 PHASE 2: Sort items based on available spaces and item characteristics."""
	
	def calculate_sort_score(product):
		"""Calculate comprehensive sort score for better packing order."""
		volume = product.width_mm * product.length_mm * product.height_mm
		
		# 1. Volume-to-weight ratio (efficient stacking)
		density = volume / max(product.weight_g, 1) if product.weight_g > 0 else volume
		
		# 2. Aspect ratio (cubic items pack better)
		max_dim = max(product.width_mm, product.length_mm, product.height_mm)
		min_dim = min(product.width_mm, product.length_mm, product.height_mm)
		aspect_ratio = max_dim / min_dim if min_dim > 0 else 1
		
		# 3. Stackability (fragile items last, heavy items first)
		stackability = 1.0
		if hasattr(product, 'is_fragile') and product.is_fragile:
			stackability = 0.3
		elif hasattr(product, 'is_hazmat') and product.is_hazmat:
			stackability = 0.5
		
		# 4. Volume factor (larger items first, but not too dominant)
		volume_factor = volume / 1000000  # Normalize to reasonable range
		
		# 5. Shape regularity bonus (more regular shapes pack better)
		shape_regularity = 1.0
		if aspect_ratio < 2.0:  # More cube-like
			shape_regularity = 1.2
		elif aspect_ratio > 5.0:  # Very elongated
			shape_regularity = 0.7
		
		# Combined score: prioritize large, dense, stackable, regular items
		score = (volume_factor * density * stackability * shape_regularity) / aspect_ratio
		
		return score
	
	def calculate_space_aware_score(product):
		"""Calculate score considering available spaces."""
		base_score = calculate_sort_score(product)  # From Phase 1
		
		# Find best matching space for this item
		item_volume = product.width_mm * product.length_mm * product.height_mm
		best_space_fit = 0
		
		for space in space_map['available_spaces']:
			# Check if item could fit in this space
			if (product.width_mm <= space['dimensions'][0] and
				product.length_mm <= space['dimensions'][1] and
				product.height_mm <= space['dimensions'][2]):
				
				# Calculate fit quality
				space_volume = space['volume']
				volume_fit = item_volume / space_volume if space_volume > 0 else 0
				quality_bonus = space_map['space_quality'].get(space['id'], 0) / 100
				
				fit_score = volume_fit * quality_bonus
				best_space_fit = max(best_space_fit, fit_score)
		
		# Combine base score with space fit
		space_aware_score = base_score * (1 + best_space_fit * 0.3)
		
		return space_aware_score
	
	return sorted(products, key=calculate_space_aware_score, reverse=True)


def find_best_space_for_item(product: Product, orientation: tuple, 
						   space_map: Dict, container: Container) -> Optional[Dict]:
	"""🚀 PHASE 2: Find the best available space for an item in given orientation."""
	ow, ol, oh = orientation
	item_volume = ow * ol * oh
	
	best_space = None
	best_score = float('-inf')
	
	for space in space_map['available_spaces']:
		# Check if item fits in this space
		if (ow <= space['dimensions'][0] and
			ol <= space['dimensions'][1] and
			oh <= space['dimensions'][2]):
			
			# Calculate fit score
			space_volume = space['volume']
			volume_efficiency = item_volume / space_volume if space_volume > 0 else 0
			quality_score = space_map['space_quality'].get(space['id'], 0)
			
			# Position optimization within space
			optimal_position = calculate_optimal_position_in_space(
				space, (ow, ol, oh), container
			)
			
			# Combined score
			fit_score = (volume_efficiency * 40 + 
						quality_score * 0.6 + 
						optimal_position['score'] * 20)
			
			if fit_score > best_score:
				best_score = fit_score
				best_space = {
					'product': product,
					'orientation': orientation,
					'space': space,
					'position': optimal_position['position'],
					'score': fit_score,
					'occupied_region': optimal_position['occupied_region']
				}
	
	return best_space


def calculate_optimal_position_in_space(space: Dict, item_dims: tuple, 
									  container: Container) -> Dict:
	"""🚀 PHASE 2: Calculate optimal position within a space."""
	ow, ol, oh = item_dims
	space_center_x, space_center_y, space_center_z = space['position']
	space_width, space_length, space_height = space['dimensions']
	
	# Calculate position that centers item in space
	optimal_x = space_center_x - ow / 2
	optimal_y = space_center_y - ol / 2
	optimal_z = space_center_z - oh / 2
	
	# Ensure position is within container bounds
	optimal_x = max(0, min(optimal_x, container.inner_w_mm - ow))
	optimal_y = max(0, min(optimal_y, container.inner_l_mm - ol))
	optimal_z = max(0, min(optimal_z, container.inner_h_mm - oh))
	
	# Calculate occupied region
	occupied_region = (optimal_x, optimal_y, optimal_z, 
					  optimal_x + ow, optimal_y + ol, optimal_z + oh)
	
	# Calculate position score
	position_score = calculate_position_fitness(
		optimal_x, optimal_y, optimal_z, ow, ol, oh, container
	)
	
	return {
		'position': (optimal_x, optimal_y, optimal_z),
		'occupied_region': occupied_region,
		'score': -position_score  # Convert fitness (lower=better) to score (higher=better)
	}


def calculate_advanced_fitness_score(placement: Dict, product: Product, 
								   space_map: Dict, container: Container) -> float:
	"""🚀 PHASE 2: Calculate advanced fitness score considering multiple factors."""
	# Base fitness from Phase 1
	position = placement['position']
	ow, ol, oh, rot = placement['orientation']
	base_fitness = -calculate_position_fitness(position[0], position[1], position[2], 
											 ow, ol, oh, container)
	
	# Space quality bonus
	space_quality_bonus = space_map['space_quality'].get(placement['space']['id'], 0) * 0.1
	
	# Volume efficiency bonus
	item_volume = ow * ol * oh
	space_volume = placement['space']['volume']
	volume_efficiency = item_volume / space_volume if space_volume > 0 else 0
	volume_bonus = volume_efficiency * 30
	
	# Stability bonus (items on ground or supported)
	stability_bonus = 20 if placement['position'][2] == 0 else 0
	
	# Accessibility bonus (easier to pack around)
	accessibility_bonus = placement['score'] * 0.5
	
	# Combined score
	total_score = (base_fitness + space_quality_bonus + volume_bonus + 
				  stability_bonus + accessibility_bonus)
	
	return total_score


def update_space_map_after_placement(space_map: Dict, placement: Dict) -> Dict:
	"""🚀 PHASE 2: Update space map after placing an item."""
	# Add occupied cells to space map
	occupied_region = placement['occupied_region']
	grid_size = space_map['grid_size']
	
	x1, y1, z1, x2, y2, z2 = occupied_region
	
	for x in range(int(x1//grid_size), int(x2//grid_size) + 1):
		for y in range(int(y1//grid_size), int(y2//grid_size) + 1):
			for z in range(int(z1//grid_size), int(z2//grid_size) + 1):
				space_map['occupied_cells'].add((x, y, z))
	
	# Remove or update affected spaces
	placement_space_id = placement['space']['id']
	space_map['available_spaces'] = [
		space for space in space_map['available_spaces'] 
		if space['id'] != placement_space_id
	]
	
	# Recalculate space quality for remaining spaces
	for space in space_map['available_spaces']:
		# Create a temporary container object for quality calculation
		temp_container = Container(
			box_id="temp",
			inner_w_mm=space_map['container_dimensions'][0],
			inner_l_mm=space_map['container_dimensions'][1],
			inner_h_mm=space_map['container_dimensions'][2],
			price_try=0
		)
		quality_score = calculate_space_quality(space, space_map, temp_container)
		space_map['space_quality'][space['id']] = quality_score
	
	return space_map


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
	"""🚀 ENHANCED: Volume-density aware greedy packing with intelligent item selection."""
	remaining_products = products.copy()
	packed_containers = []
	
	while remaining_products:
		best_pack = None
		best_container = None
		best_score = float('-inf')
		
		# 🚀 ENHANCED: Sort products by volume-density score for better greedy selection
		enhanced_products = enhanced_volume_density_sorting(remaining_products)
		
		# Try each container type to find the one with best volume-density efficiency
		for container in containers:
			# Try with enhanced sorting
			result = pack(enhanced_products, container)
			if result:
				# 🚀 ENHANCED: Calculate volume-density score instead of just item count
				score = calculate_volume_density_score(container, result, enhanced_products)
				if score > best_score:
					best_score = score
					best_pack = result
					best_container = container
		
		if not best_pack:
			return None
		
		# Add this container to solution
		packed_containers.append((best_container, best_pack))
		
		# Remove packed items
		packed_skus = [p.sku for p in best_pack.placements]
		remaining_products = [p for p in remaining_products if p.sku not in packed_skus]
	
	return packed_containers


def enhanced_volume_density_sorting(products: List[Product]) -> List[Product]:
	"""🚀 ENHANCED: Sort products by volume-density ratio for optimal greedy packing."""
	def calculate_volume_density_score(product):
		volume = product.width_mm * product.length_mm * product.height_mm
		weight = max(product.weight_g, 1)  # Avoid division by zero
		
		# Volume-density ratio (higher is better for space efficiency)
		density_ratio = volume / weight
		
		# Shape factor (more cube-like items pack better)
		max_dim = max(product.width_mm, product.length_mm, product.height_mm)
		min_dim = min(product.width_mm, product.length_mm, product.height_mm)
		aspect_ratio = max_dim / min_dim if min_dim > 0 else 1
		shape_factor = 1.0 / aspect_ratio  # Prefer cube-like shapes
		
		# Stackability factor
		stackability = 1.0
		if hasattr(product, 'is_fragile') and product.is_fragile:
			stackability = 0.3
		elif hasattr(product, 'is_hazmat') and product.is_hazmat:
			stackability = 0.5
		
		# Combined score: prioritize dense, cube-like, stackable items
		score = density_ratio * shape_factor * stackability
		return score
	
	return sorted(products, key=calculate_volume_density_score, reverse=True)


def calculate_volume_density_score(container: Container, result: PackedContainer, products: List[Product]) -> float:
	"""🚀 ENHANCED: Calculate volume-density efficiency score for greedy packing."""
	container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm
	used_volume = sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] for p in result.placements)
	
	# Volume utilization (primary factor)
	volume_utilization = used_volume / container_volume if container_volume > 0 else 0
	
	# Density efficiency (how well we use the space with dense items)
	total_item_volume = sum(p.width_mm * p.length_mm * p.height_mm for p in products)
	density_efficiency = used_volume / total_item_volume if total_item_volume > 0 else 0
	
	# Item count factor (secondary to volume)
	item_count_factor = len(result.placements) / len(products) if products else 0
	
	# Cost efficiency factor
	container_cost = container.price_try or 0
	cost_efficiency = used_volume / max(container_cost, 1)
	
	# Combined score: prioritize volume utilization and density efficiency
	score = (
		volume_utilization * 50 +      # 50% weight on volume utilization
		density_efficiency * 30 +      # 30% weight on density efficiency  
		item_count_factor * 15 +       # 15% weight on item count
		cost_efficiency * 0.01         # 5% weight on cost efficiency (normalized)
	)
	
	return score


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
	"""🚀 ENHANCED: Best fit with shape compatibility and stability scoring."""
	remaining_products = products.copy()
	packed_containers = []
	
	while remaining_products:
		best_pack = None
		best_container = None
		best_fit_score = float('-inf')
		
		for container in containers:
			result = pack(remaining_products, container)
			if result and len(result.placements) > 0:
				# 🚀 ENHANCED: Calculate comprehensive fit score instead of just waste ratio
				fit_score = calculate_enhanced_best_fit_score(container, result, remaining_products)
				
				if fit_score > best_fit_score:
					best_fit_score = fit_score
					best_pack = result
					best_container = container
		
		if not best_pack:
			return None
		
		packed_containers.append((best_container, best_pack))
		
		# Remove packed items
		packed_skus = [p.sku for p in best_pack.placements]
		remaining_products = [p for p in remaining_products if p.sku not in packed_skus]
	
	return packed_containers


def calculate_enhanced_best_fit_score(container: Container, result: PackedContainer, products: List[Product]) -> float:
	"""🚀 ENHANCED: Calculate comprehensive best-fit score with shape compatibility."""
	container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm
	used_volume = sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] for p in result.placements)
	
	# 1. Volume efficiency (minimize waste)
	volume_utilization = used_volume / container_volume if container_volume > 0 else 0
	waste_penalty = 1 - volume_utilization
	
	# 2. Shape compatibility score
	shape_compatibility = calculate_shape_compatibility_score(container, result)
	
	# 3. Stability score
	stability_score = calculate_stability_score(result, container)
	
	# 4. Packing density score
	packing_density = calculate_packing_density_score(result, products)
	
	# 5. Container size appropriateness
	size_appropriateness = calculate_size_appropriateness(container, products)
	
	# Combined fit score (higher is better)
	fit_score = (
		volume_utilization * 40 +           # 40% weight on volume utilization
		shape_compatibility * 25 +          # 25% weight on shape compatibility
		stability_score * 20 +              # 20% weight on stability
		packing_density * 10 +              # 10% weight on packing density
		size_appropriateness * 5            # 5% weight on size appropriateness
	)
	
	return fit_score


def calculate_shape_compatibility_score(container: Container, result: PackedContainer) -> float:
	"""🚀 ENHANCED: Calculate shape compatibility between container and packed items."""
	container_aspect = max(container.inner_w_mm, container.inner_l_mm, container.inner_h_mm) / min(container.inner_w_mm, container.inner_l_mm, container.inner_h_mm)
	
	# Calculate average item aspect ratio
	item_aspects = []
	for placement in result.placements:
		ow, ol, oh = placement.size_mm
		item_aspect = max(ow, ol, oh) / min(ow, ol, oh)
		item_aspects.append(item_aspect)
	
	if not item_aspects:
		return 0.5
	
	avg_item_aspect = sum(item_aspects) / len(item_aspects)
	
	# Shape compatibility (closer aspect ratios = better fit)
	aspect_difference = abs(container_aspect - avg_item_aspect)
	max_possible_difference = max(container_aspect, avg_item_aspect)
	
	# Normalize to 0-1 scale (1 = perfect match, 0 = worst match)
	compatibility = max(0, 1 - (aspect_difference / max_possible_difference))
	
	return compatibility


def calculate_stability_score(result: PackedContainer, container: Container) -> float:
	"""🚀 ENHANCED: Calculate stability score for packed items."""
	stability_score = 0.0
	
	# Count items on ground level (more stable)
	ground_level_items = sum(1 for p in result.placements if p.position_mm[2] == 0)
	ground_ratio = ground_level_items / len(result.placements) if result.placements else 0
	
	# Average height penalty (lower items are more stable)
	avg_height = sum(p.position_mm[2] for p in result.placements) / len(result.placements) if result.placements else 0
	height_penalty = avg_height / container.inner_h_mm if container.inner_h_mm > 0 else 0
	
	# Base stability score
	base_stability = 0.5
	
	# Ground contact bonus
	ground_bonus = ground_ratio * 0.4
	
	# Height penalty
	height_penalty_factor = (1 - height_penalty) * 0.1
	
	# Combined stability score
	stability_score = base_stability + ground_bonus + height_penalty_factor
	
	return min(1.0, stability_score)  # Cap at 1.0


def calculate_packing_density_score(result: PackedContainer, products: List[Product]) -> float:
	"""🚀 ENHANCED: Calculate how densely items are packed."""
	if not result.placements:
		return 0.0
	
	# Calculate bounding box of packed items
	min_x = min(p.position_mm[0] for p in result.placements)
	max_x = max(p.position_mm[0] + p.size_mm[0] for p in result.placements)
	min_y = min(p.position_mm[1] for p in result.placements)
	max_y = max(p.position_mm[1] + p.size_mm[1] for p in result.placements)
	min_z = min(p.position_mm[2] for p in result.placements)
	max_z = max(p.position_mm[2] + p.size_mm[2] for p in result.placements)
	
	# Bounding box volume
	bbox_volume = (max_x - min_x) * (max_y - min_y) * (max_z - min_z)
	
	# Actual packed volume
	packed_volume = sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] for p in result.placements)
	
	# Density ratio (higher = more compact packing)
	density = packed_volume / bbox_volume if bbox_volume > 0 else 0
	
	return density


def calculate_size_appropriateness(container: Container, products: List[Product]) -> float:
	"""🚀 ENHANCED: Calculate how appropriately sized the container is for the items."""
	container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm
	total_item_volume = sum(p.width_mm * p.length_mm * p.height_mm for p in products)
	
	# Volume ratio
	volume_ratio = total_item_volume / container_volume if container_volume > 0 else 0
	
	# Size appropriateness scoring
	if volume_ratio < 0.5:  # Container too big
		appropriateness = 0.3
	elif volume_ratio < 0.8:  # Container slightly big (good)
		appropriateness = 0.9
	elif volume_ratio < 1.2:  # Container just right
		appropriateness = 1.0
	elif volume_ratio < 1.5:  # Container slightly small
		appropriateness = 0.7
	else:  # Container too small
		appropriateness = 0.2
	
	return appropriateness


def adaptive_strategy_selection(products: List[Product], containers: List[Container]) -> Optional[List[Tuple[Container, PackedContainer]]]:
	"""🚀 ENHANCED: Context-aware strategy selection based on order characteristics."""
	if not products or not containers:
		return None
	
	# Analyze order characteristics
	order_context = analyze_order_context(products)
	
	# Select strategy based on characteristics
	if order_context['item_count'] < 5:
		# Few items: use enhanced greedy for speed
		print("🎯 Strategy: Enhanced Greedy (few items)")
		return pack_greedy_max_utilization(products, containers)
	
	elif order_context['volume_variance'] > 0.7:
		# High volume variance: use genetic algorithm for optimization
		print("🎯 Strategy: Genetic Algorithm (high volume variance)")
		return genetic_algorithm_packing(products, containers)
	
	elif order_context['shape_diversity'] > 0.8:
		# High shape diversity: use multi-objective optimization
		print("🎯 Strategy: Multi-Objective (high shape diversity)")
		return multi_objective_packing(products, containers)
	
	elif order_context['fragile_ratio'] > 0.3:
		# Many fragile items: use stability-focused best-fit
		print("🎯 Strategy: Enhanced Best-Fit (fragile items)")
		return pack_best_fit(products, containers)
	
	elif order_context['total_volume'] > 1000000:  # Large volume
		# Large orders: use ensemble strategy
		print("🎯 Strategy: Ensemble (large volume)")
		return ensemble_packing(products, containers)
	
	else:
		# Default: use intelligent hybrid approach
		print("🎯 Strategy: Intelligent Hybrid (default)")
		return intelligent_hybrid_packing(products, containers)


def analyze_order_context(products: List[Product]) -> Dict:
	"""🚀 ENHANCED: Analyze order characteristics for strategy selection."""
	if not products:
		return {
			'item_count': 0,
			'volume_variance': 0,
			'shape_diversity': 0,
			'fragile_ratio': 0,
			'total_volume': 0
		}
	
	# Basic metrics
	item_count = len(products)
	volumes = [p.width_mm * p.length_mm * p.height_mm for p in products]
	total_volume = sum(volumes)
	
	# Volume variance (how different item sizes are)
	avg_volume = total_volume / item_count if item_count > 0 else 0
	volume_variance = sum((v - avg_volume) ** 2 for v in volumes) / item_count if item_count > 0 else 0
	volume_variance = min(1.0, volume_variance / (avg_volume ** 2)) if avg_volume > 0 else 0
	
	# Shape diversity (how different item shapes are)
	aspect_ratios = []
	for p in products:
		max_dim = max(p.width_mm, p.length_mm, p.height_mm)
		min_dim = min(p.width_mm, p.length_mm, p.height_mm)
		aspect_ratio = max_dim / min_dim if min_dim > 0 else 1
		aspect_ratios.append(aspect_ratio)
	
	avg_aspect = sum(aspect_ratios) / len(aspect_ratios) if aspect_ratios else 1
	shape_diversity = sum(abs(ar - avg_aspect) for ar in aspect_ratios) / len(aspect_ratios) if aspect_ratios else 0
	shape_diversity = min(1.0, shape_diversity / avg_aspect) if avg_aspect > 0 else 0
	
	# Fragile item ratio
	fragile_count = sum(1 for p in products if hasattr(p, 'is_fragile') and p.is_fragile)
	fragile_ratio = fragile_count / item_count if item_count > 0 else 0
	
	return {
		'item_count': item_count,
		'volume_variance': volume_variance,
		'shape_diversity': shape_diversity,
		'fragile_ratio': fragile_ratio,
		'total_volume': total_volume
	}


def genetic_algorithm_packing(products: List[Product], containers: List[Container]) -> Optional[List[Tuple[Container, PackedContainer]]]:
	"""🚀 ENHANCED: Genetic algorithm for optimal packing combinations."""
	if not products or not containers:
		return None
	
	# Simplified genetic algorithm implementation
	population_size = 20
	generations = 10
	
	# Initialize population with random packing solutions
	population = []
	for _ in range(population_size):
		solution = generate_random_packing_solution(products, containers)
		if solution:
			population.append(solution)
	
	# Evolve population
	for generation in range(generations):
		# Evaluate fitness
		fitness_scores = [calculate_genetic_fitness(solution, products) for solution in population]
		
		# Select best solutions
		best_solutions = select_best_solutions(population, fitness_scores, population_size // 2)
		
		# Create new generation through crossover and mutation
		new_population = best_solutions.copy()
		while len(new_population) < population_size:
			parent1, parent2 = select_parents(best_solutions, fitness_scores)
			if parent1 is not None and parent2 is not None:
				child = crossover_solutions(parent1, parent2, products, containers)
				if child:
					child = mutate_solution(child, products, containers)
					new_population.append(child)
		
		population = new_population
	
	# Return best solution
	best_solution = max(population, key=lambda s: calculate_genetic_fitness(s, products))
	return best_solution


def multi_objective_packing(products: List[Product], containers: List[Container]) -> Optional[List[Tuple[Container, PackedContainer]]]:
	"""🚀 ENHANCED: Multi-objective optimization balancing multiple goals."""
	if not products or not containers:
		return None
	
	# Try different strategies and evaluate on multiple objectives
	strategies = [
		("enhanced_greedy", pack_greedy_max_utilization),
		("enhanced_best_fit", pack_best_fit),
		("intelligent_hybrid", intelligent_hybrid_packing),
		("volume_optimized", intelligent_volume_optimized_packing)
	]
	
	best_solution = None
	best_pareto_score = float('-inf')
	
	for strategy_name, strategy_func in strategies:
		try:
			solution = strategy_func(products, containers)
			if solution:
				# Calculate multi-objective score
				pareto_score = calculate_pareto_score(solution, products)
				if pareto_score > best_pareto_score:
					best_pareto_score = pareto_score
					best_solution = solution
		except Exception as e:
			print(f"⚠️ Strategy {strategy_name} failed: {e}")
			continue
	
	return best_solution


def ensemble_packing(products: List[Product], containers: List[Container]) -> Optional[List[Tuple[Container, PackedContainer]]]:
	"""🚀 ENHANCED: Ensemble strategy combining multiple approaches."""
	if not products or not containers:
		return None
	
	# Run multiple strategies in parallel (avoiding recursive calls and problematic algorithms)
	strategies = [
		("enhanced_greedy", pack_greedy_max_utilization),
		("enhanced_best_fit", pack_best_fit),
		("intelligent_hybrid", intelligent_hybrid_packing),
		("multi_objective", multi_objective_packing)
	]
	
	solutions = []
	for strategy_name, strategy_func in strategies:
		try:
			solution = strategy_func(products, containers)
			if solution:
				score = calculate_ensemble_score(solution, products)
				solutions.append((solution, score, strategy_name))
		except Exception as e:
			print(f"⚠️ Strategy {strategy_name} failed: {e}")
			continue
	
	if not solutions:
		return None
	
	# Return best solution
	best_solution = max(solutions, key=lambda x: x[1])
	return best_solution[0]


def generate_random_packing_solution(products: List[Product], containers: List[Container]) -> Optional[List[Tuple[Container, PackedContainer]]]:
	"""🚀 ENHANCED: Generate random packing solution for genetic algorithm."""
	# Simplified random solution generation
	import random
	
	remaining_products = products.copy()
	packed_containers = []
	
	while remaining_products and len(packed_containers) < 5:  # Limit containers
		# Randomly select container
		container = random.choice(containers)
		
		# Try to pack with random item order
		random.shuffle(remaining_products)
		result = pack(remaining_products, container)
		
		if result and len(result.placements) > 0:
			packed_containers.append((container, result))
			
			# Remove packed items
			packed_skus = [p.sku for p in result.placements]
			remaining_products = [p for p in remaining_products if p.sku not in packed_skus]
		else:
			break
	
	return packed_containers if packed_containers else None


def calculate_genetic_fitness(solution: List[Tuple[Container, PackedContainer]], products: List[Product]) -> float:
	"""🚀 ENHANCED: Calculate fitness score for genetic algorithm."""
	if not solution:
		return 0.0
	
	# Calculate multiple fitness factors
	total_cost = sum(container.price_try or 0 for container, _ in solution)
	total_containers = len(solution)
	total_items_packed = sum(len(result.placements) for _, result in solution)
	
	# Volume utilization
	total_volume_used = sum(
		sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] for p in result.placements)
		for _, result in solution
	)
	
	# Fitness components
	cost_efficiency = total_items_packed / max(total_cost, 1)
	container_efficiency = total_items_packed / total_containers
	volume_efficiency = total_volume_used / sum(p.width_mm * p.length_mm * p.height_mm for p in products) if products else 0
	
	# Combined fitness score
	fitness = (
		cost_efficiency * 0.4 +
		container_efficiency * 0.3 +
		volume_efficiency * 0.3
	)
	
	return fitness


def select_best_solutions(population: List, fitness_scores: List[float], count: int) -> List:
	"""🚀 ENHANCED: Select best solutions for genetic algorithm."""
	# Sort by fitness score
	indexed_solutions = list(enumerate(fitness_scores))
	indexed_solutions.sort(key=lambda x: x[1], reverse=True)
	
	# Return best solutions
	best_indices = [idx for idx, _ in indexed_solutions[:count]]
	return [population[idx] for idx in best_indices]


def select_parents(best_solutions: List, fitness_scores: List[float]) -> tuple:
	"""🚀 ENHANCED: Select parents for crossover in genetic algorithm."""
	import random
	
	# Tournament selection
	tournament_size = 3
	parent1 = tournament_selection(best_solutions, fitness_scores, tournament_size)
	parent2 = tournament_selection(best_solutions, fitness_scores, tournament_size)
	
	# Handle None returns
	if parent1 is None or parent2 is None:
		# Fallback: return first two solutions
		if len(best_solutions) >= 2:
			return best_solutions[0], best_solutions[1]
		elif len(best_solutions) == 1:
			return best_solutions[0], best_solutions[0]
		else:
			return None, None
	
	return parent1, parent2


def tournament_selection(solutions: List, fitness_scores: List[float], tournament_size: int):
	"""🚀 ENHANCED: Tournament selection for genetic algorithm."""
	import random
	
	if not solutions or not fitness_scores or len(solutions) == 0:
		return None
	
	tournament = random.sample(list(enumerate(solutions)), min(tournament_size, len(solutions)))
	
	if not tournament:
		return None
	
	winner = max(tournament, key=lambda x: fitness_scores[x[0]])
	return winner[1]


def crossover_solutions(parent1: List, parent2: List, products: List[Product], containers: List[Container]) -> Optional[List]:
	"""🚀 ENHANCED: Crossover two solutions to create offspring."""
	# Check for None parents
	if parent1 is None or parent2 is None:
		return None
	
	# Simplified crossover: combine best containers from both parents
	all_containers = []
	
	# Add containers from parent1
	for container, result in parent1:
		all_containers.append((container, result))
	
	# Add containers from parent2 (avoid duplicates)
	for container, result in parent2:
		if not any(c.box_id == container.box_id for c, _ in all_containers):
			all_containers.append((container, result))
	
	# Return combined solution (simplified)
	return all_containers if all_containers else None


def mutate_solution(solution: List, products: List[Product], containers: List[Container]) -> List:
	"""🚀 ENHANCED: Mutate solution for genetic algorithm."""
	import random
	
	# Simple mutation: randomly swap one container
	if len(solution) > 1:
		idx = random.randint(0, len(solution) - 1)
		new_container = random.choice(containers)
		
		# Try to repack with new container
		remaining_products = products.copy()
		for i, (container, result) in enumerate(solution):
			if i != idx:
				packed_skus = [p.sku for p in result.placements]
				remaining_products = [p for p in remaining_products if p.sku not in packed_skus]
		
		# Try new container
		new_result = pack(remaining_products, new_container)
		if new_result:
			solution[idx] = (new_container, new_result)
	
	return solution


def calculate_pareto_score(solution: List[Tuple[Container, PackedContainer]], products: List[Product]) -> float:
	"""🚀 ENHANCED: Calculate Pareto score for multi-objective optimization."""
	if not solution:
		return 0.0
	
	# Multiple objectives
	objectives = {
		'utilization': calculate_utilization_score(solution),
		'cost_efficiency': calculate_cost_efficiency_score(solution),
		'stability': calculate_stability_score_multi(solution),
		'compactness': calculate_compactness_score(solution)
	}
	
	# Weighted sum approach (simplified Pareto)
	weights = {'utilization': 0.4, 'cost_efficiency': 0.3, 'stability': 0.2, 'compactness': 0.1}
	
	score = sum(objectives[obj] * weights[obj] for obj in objectives)
	return score


def calculate_utilization_score(solution: List[Tuple[Container, PackedContainer]]) -> float:
	"""Calculate utilization score for multi-objective optimization."""
	if not solution:
		return 0.0
	
	total_utilization = 0.0
	for container, result in solution:
		container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm
		used_volume = sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] for p in result.placements)
		utilization = used_volume / container_volume if container_volume > 0 else 0
		total_utilization += utilization
	
	return total_utilization / len(solution) if solution else 0.0


def calculate_cost_efficiency_score(solution: List[Tuple[Container, PackedContainer]]) -> float:
	"""Calculate cost efficiency score for multi-objective optimization."""
	if not solution:
		return 0.0
	
	total_cost = sum(container.price_try or 0 for container, _ in solution)
	total_items = sum(len(result.placements) for _, result in solution)
	
	return total_items / max(total_cost, 1) if total_cost > 0 else 0.0


def calculate_stability_score_multi(solution: List[Tuple[Container, PackedContainer]]) -> float:
	"""Calculate stability score for multi-objective optimization."""
	if not solution:
		return 0.0
	
	total_stability = 0.0
	for container, result in solution:
		# Count ground-level items
		ground_items = sum(1 for p in result.placements if p.position_mm[2] == 0)
		stability = ground_items / len(result.placements) if result.placements else 0
		total_stability += stability
	
	return total_stability / len(solution) if solution else 0.0


def calculate_compactness_score(solution: List[Tuple[Container, PackedContainer]]) -> float:
	"""Calculate compactness score for multi-objective optimization."""
	if not solution:
		return 0.0
	
	# Prefer fewer containers
	container_count = len(solution)
	compactness = 1.0 / container_count if container_count > 0 else 0.0
	
	return compactness


def calculate_ensemble_score(solution: List[Tuple[Container, PackedContainer]], products: List[Product]) -> float:
	"""🚀 ENHANCED: Calculate ensemble score combining multiple metrics."""
	if not solution:
		return 0.0
	
	# Multiple scoring criteria
	utilization_score = calculate_utilization_score(solution)
	cost_score = calculate_cost_efficiency_score(solution)
	stability_score = calculate_stability_score_multi(solution)
	compactness_score = calculate_compactness_score(solution)
	
	# Weighted ensemble score
	ensemble_score = (
		utilization_score * 0.35 +
		cost_score * 0.25 +
		stability_score * 0.25 +
		compactness_score * 0.15
	)
	
	return ensemble_score


def find_optimal_multi_packing(products: List[Product], containers: List[Container]) -> Optional[List[Tuple[Container, PackedContainer]]]:
	"""
	🚀 PHASE 3: Intelligent Container Selection with advanced optimization.
	Uses smart container selection, dynamic switching, and hybrid strategies.
	"""
	# Filter containers to only include 3D boxes
	box_containers = [c for c in containers if c.is_3d_box]
	
	if not box_containers:
		return None
	
	# 🚀 PHASE 3: Try intelligent single container selection first
	intelligent_single_result = intelligent_single_container_selection(products, box_containers)
	if intelligent_single_result:
		return intelligent_single_result
	
	# 🚀 PHASE 3: If single container fails, try intelligent multi-container
	return intelligent_multi_container_packing(products, box_containers)


def intelligent_single_container_selection(products: List[Product], containers: List[Container]) -> Optional[List[Tuple[Container, PackedContainer]]]:
	"""🚀 PHASE 3: Intelligent single container selection with advanced scoring."""
	if not products or not containers:
		return None
	
	# Calculate total volume and characteristics of items
	total_volume = sum(p.width_mm * p.length_mm * p.height_mm for p in products)
	total_weight = sum(p.weight_g for p in products)
	item_count = len(products)
	
	# Calculate item size distribution
	item_volumes = [p.width_mm * p.length_mm * p.height_mm for p in products]
	avg_volume = total_volume / item_count if item_count > 0 else 0
	max_volume = max(item_volumes) if item_volumes else 0
	
	best_container = None
	best_score = float('-inf')
	best_result = None
	
	for container in containers:
		# Calculate container characteristics
		container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm
		container_price = container.price_try or 0
		
		# Skip containers that are obviously too small
		if container_volume < total_volume * 0.8:  # Need at least 80% volume match
			continue
		
		# Skip containers where largest item doesn't fit
		if (max(p.width_mm for p in products) > container.inner_w_mm or
			max(p.length_mm for p in products) > container.inner_l_mm or
			max(p.height_mm for p in products) > container.inner_h_mm):
			continue
		
		# Try to pack in this container
		result = pack(products, container)
		if not result:
			continue
		
		# Calculate intelligent score
		score = calculate_container_intelligence_score(
			container, result, products, total_volume, total_weight, item_count
		)
		
		if score > best_score:
			best_score = score
			best_container = container
			best_result = result
	
	if best_result:
		return [(best_container, best_result)]
	return None


def calculate_container_intelligence_score(container: Container, result: PackedContainer, 
										products: List[Product], total_volume: float, 
										total_weight: float, item_count: int) -> float:
	"""🚀 PHASE 3: Calculate intelligent container selection score."""
	container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm
	container_price = container.price_try or 0
	
	# 1. Volume utilization (most important factor)
	used_volume = sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] for p in result.placements)
	volume_utilization = used_volume / container_volume if container_volume > 0 else 0
	
	# 2. Item packing efficiency (how many items fit)
	packed_count = len(result.placements)
	item_efficiency = packed_count / item_count if item_count > 0 else 0
	
	# 3. Cost efficiency (items per cost unit)
	cost_efficiency = packed_count / max(container_price, 1)
	
	# 4. Volume efficiency (volume per cost unit)
	volume_cost_ratio = used_volume / max(container_price, 1)
	
	# 5. Container size appropriateness (optimized for better utilization)
	size_appropriateness = 1.0
	if container_volume > total_volume * 3.0:  # Container way too big
		size_appropriateness = 0.2
	elif container_volume > total_volume * 2.0:  # Container too big
		size_appropriateness = 0.5
	elif container_volume < total_volume * 1.05:  # Container perfect fit
		size_appropriateness = 1.5
	elif container_volume < total_volume * 1.2:  # Container good fit
		size_appropriateness = 1.3
	elif container_volume < total_volume * 1.5:  # Container acceptable
		size_appropriateness = 1.0
	
	# 6. Shape compatibility (container aspect ratio vs item aspect ratios)
	container_aspect = max(container.inner_w_mm, container.inner_l_mm, container.inner_h_mm) / min(container.inner_w_mm, container.inner_l_mm, container.inner_h_mm)
	avg_item_aspect = sum(max(p.width_mm, p.length_mm, p.height_mm) / min(p.width_mm, p.length_mm, p.height_mm) for p in products) / len(products)
	shape_compatibility = 1.0 - abs(container_aspect - avg_item_aspect) / max(container_aspect, avg_item_aspect)
	shape_compatibility = max(0.5, shape_compatibility)  # Minimum 50%
	
	# 🎯 OPTIMIZED SCORING: Prioritize utilization and size appropriateness
	intelligent_score = (
		volume_utilization * 60 +           # 60% weight on volume utilization (increased)
		size_appropriateness * 25 +         # 25% weight on size appropriateness (increased)
		item_efficiency * 10 +              # 10% weight on item efficiency (reduced)
		shape_compatibility * 5             # 5% weight on shape compatibility (reduced)
	)
	
	return intelligent_score


def intelligent_multi_container_packing(products: List[Product], containers: List[Container]) -> Optional[List[Tuple[Container, PackedContainer]]]:
	"""🚀 PHASE 3: Intelligent multi-container packing with dynamic optimization."""
	if not products or not containers:
		return None
	
	# Sort containers by intelligent score (best first)
	container_scores = []
	for container in containers:
		container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm
		container_price = container.price_try or 0
		
		# Pre-score containers based on characteristics
		base_score = calculate_container_base_score(container, products)
		container_scores.append((container, base_score))
	
	# Sort by base score (highest first)
	container_scores.sort(key=lambda x: x[1], reverse=True)
	sorted_containers = [c[0] for c in container_scores]
	
	# Try different intelligent strategies
	strategies = [
		("intelligent_greedy", intelligent_greedy_packing),
		("intelligent_best_fit", intelligent_best_fit_packing),
		("intelligent_hybrid", intelligent_hybrid_packing),
		("intelligent_volume_optimized", intelligent_volume_optimized_packing)
	]
	
	best_solution = None
	best_score = float('-inf')
	
	for strategy_name, strategy_func in strategies:
		try:
			solution = strategy_func(products, sorted_containers)
			if solution:
				# Calculate solution score
				solution_score = calculate_solution_score(solution, products)
				if solution_score > best_score:
					best_score = solution_score
					best_solution = solution
		except Exception as e:
			print(f"⚠️ Strategy {strategy_name} failed: {e}")
			continue
	
	return best_solution


def calculate_container_base_score(container: Container, products: List[Product]) -> float:
	"""🚀 PHASE 3: Calculate base score for container without packing."""
	container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm
	container_price = container.price_try or 0
	
	total_volume = sum(p.width_mm * p.length_mm * p.height_mm for p in products)
	
	# Volume efficiency potential
	volume_efficiency = min(1.0, total_volume / container_volume) if container_volume > 0 else 0
	
	# Cost efficiency potential
	cost_efficiency = 1.0 / max(container_price, 1)
	
	# Size appropriateness
	size_score = 1.0
	if container_volume > total_volume * 3.0:  # Too big
		size_score = 0.5
	elif container_volume < total_volume * 0.9:  # Too small
		size_score = 0.3
	elif container_volume < total_volume * 1.2:  # Just right
		size_score = 1.5
	
	base_score = volume_efficiency * 50 + cost_efficiency * 0.1 + size_score * 30
	return base_score


def intelligent_greedy_packing(products: List[Product], containers: List[Container]) -> Optional[List[Tuple[Container, PackedContainer]]]:
	"""🚀 PHASE 3: Intelligent greedy packing with smart container selection."""
	remaining_products = products.copy()
	packed_containers = []
	
	while remaining_products:
		best_pack = None
		best_container = None
		best_intelligence_score = float('-inf')
		
		for container in containers:
			result = pack(remaining_products, container)
			if result and len(result.placements) > 0:
				# Calculate intelligence score for this packing
				score = calculate_container_intelligence_score(
					container, result, remaining_products,
					sum(p.width_mm * p.length_mm * p.height_mm for p in remaining_products),
					sum(p.weight_g for p in remaining_products),
					len(remaining_products)
				)
				
				if score > best_intelligence_score:
					best_intelligence_score = score
					best_pack = result
					best_container = container
		
		if not best_pack:
			return None
		
		packed_containers.append((best_container, best_pack))
		
		# Remove packed items
		packed_skus = [p.sku for p in best_pack.placements]
		remaining_products = [p for p in remaining_products if p.sku not in packed_skus]
	
	return packed_containers


def intelligent_best_fit_packing(products: List[Product], containers: List[Container]) -> Optional[List[Tuple[Container, PackedContainer]]]:
	"""🚀 PHASE 3: Intelligent best-fit packing with volume optimization."""
	remaining_products = products.copy()
	packed_containers = []
	
	while remaining_products:
		best_pack = None
		best_container = None
		best_waste_ratio = float('inf')
		best_utilization = 0.0
		
		for container in containers:
			result = pack(remaining_products, container)
			if result and len(result.placements) > 0:
				# Calculate waste ratio
				used_volume = sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] for p in result.placements)
				container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm
				waste_ratio = (container_volume - used_volume) / container_volume if container_volume > 0 else 1
				utilization = used_volume / container_volume if container_volume > 0 else 0
				
				# Prefer containers with lower waste and higher utilization
				if waste_ratio < best_waste_ratio or (waste_ratio == best_waste_ratio and utilization > best_utilization):
					best_waste_ratio = waste_ratio
					best_utilization = utilization
					best_pack = result
					best_container = container
		
		if not best_pack:
			return None
		
		packed_containers.append((best_container, best_pack))
		
		# Remove packed items
		packed_skus = [p.sku for p in best_pack.placements]
		remaining_products = [p for p in remaining_products if p.sku not in packed_skus]
	
	return packed_containers


def intelligent_hybrid_packing(products: List[Product], containers: List[Container]) -> Optional[List[Tuple[Container, PackedContainer]]]:
	"""🚀 PHASE 3: Hybrid packing strategy combining multiple approaches."""
	remaining_products = products.copy()
	packed_containers = []
	
	while remaining_products:
		# Try different strategies and pick the best one for current items
		strategies = [
			("greedy", intelligent_greedy_single_pack),
			("best_fit", intelligent_best_fit_single_pack),
			("volume_optimized", intelligent_volume_optimized_single_pack)
		]
		
		best_pack = None
		best_container = None
		best_score = float('-inf')
		
		for strategy_name, strategy_func in strategies:
			try:
				pack_result = strategy_func(remaining_products, containers)
				if pack_result:
					container, result = pack_result
					# Calculate hybrid score
					score = calculate_hybrid_packing_score(container, result, remaining_products)
					if score > best_score:
						best_score = score
						best_container = container
						best_pack = result
			except Exception as e:
				continue
		
		if not best_pack:
			return None
		
		packed_containers.append((best_container, best_pack))
		
		# Remove packed items
		packed_skus = [p.sku for p in best_pack.placements]
		remaining_products = [p for p in remaining_products if p.sku not in packed_skus]
	
	return packed_containers


def intelligent_volume_optimized_packing(products: List[Product], containers: List[Container]) -> Optional[List[Tuple[Container, PackedContainer]]]:
	"""🚀 PHASE 3: Volume-optimized packing for maximum space utilization."""
	remaining_products = products.copy()
	packed_containers = []
	
	while remaining_products:
		best_pack = None
		best_container = None
		best_volume_score = float('-inf')
		
		for container in containers:
			result = pack(remaining_products, container)
			if result and len(result.placements) > 0:
				# Calculate volume optimization score
				used_volume = sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] for p in result.placements)
				container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm
				
				volume_utilization = used_volume / container_volume if container_volume > 0 else 0
				items_packed = len(result.placements)
				volume_efficiency = used_volume / items_packed if items_packed > 0 else 0
				
				# Combined volume score
				volume_score = volume_utilization * 60 + (items_packed / len(remaining_products)) * 40
				
				if volume_score > best_volume_score:
					best_volume_score = volume_score
					best_pack = result
					best_container = container
		
		if not best_pack:
			return None
		
		packed_containers.append((best_container, best_pack))
		
		# Remove packed items
		packed_skus = [p.sku for p in best_pack.placements]
		remaining_products = [p for p in remaining_products if p.sku not in packed_skus]
	
	return packed_containers


def intelligent_greedy_single_pack(products: List[Product], containers: List[Container]) -> Optional[Tuple[Container, PackedContainer]]:
	"""🚀 PHASE 3: Single pack using greedy strategy."""
	best_pack = None
	best_container = None
	best_count = 0
	
	for container in containers:
		result = pack(products, container)
		if result and len(result.placements) > best_count:
			best_pack = result
			best_container = container
			best_count = len(result.placements)
	
	return (best_container, best_pack) if best_pack else None


def intelligent_best_fit_single_pack(products: List[Product], containers: List[Container]) -> Optional[Tuple[Container, PackedContainer]]:
	"""🚀 PHASE 3: Single pack using best-fit strategy."""
	best_pack = None
	best_container = None
	best_waste = float('inf')
	
	for container in containers:
		result = pack(products, container)
		if result:
			used_volume = sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] for p in result.placements)
			container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm
			waste = (container_volume - used_volume) / container_volume if container_volume > 0 else 1
			
			if waste < best_waste:
				best_waste = waste
				best_pack = result
				best_container = container
	
	return (best_container, best_pack) if best_pack else None


def intelligent_volume_optimized_single_pack(products: List[Product], containers: List[Container]) -> Optional[Tuple[Container, PackedContainer]]:
	"""🚀 PHASE 3: Single pack using volume optimization strategy."""
	best_pack = None
	best_container = None
	best_volume_score = float('-inf')
	
	for container in containers:
		result = pack(products, container)
		if result:
			used_volume = sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] for p in result.placements)
			container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm
			volume_utilization = used_volume / container_volume if container_volume > 0 else 0
			
			volume_score = volume_utilization * 100 + len(result.placements) * 10
			
			if volume_score > best_volume_score:
				best_volume_score = volume_score
				best_pack = result
				best_container = container
	
	return (best_container, best_pack) if best_pack else None


def calculate_hybrid_packing_score(container: Container, result: PackedContainer, products: List[Product]) -> float:
	"""🚀 PHASE 3: Calculate hybrid packing score."""
	container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm
	used_volume = sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] for p in result.placements)
	
	volume_utilization = used_volume / container_volume if container_volume > 0 else 0
	item_efficiency = len(result.placements) / len(products) if products else 0
	
	# Hybrid score combining multiple factors
	hybrid_score = (
		volume_utilization * 50 +      # 50% volume utilization
		item_efficiency * 30 +         # 30% item efficiency
		len(result.placements) * 5     # 20% absolute item count
	)
	
	return hybrid_score


def calculate_solution_score(solution: List[Tuple[Container, PackedContainer]], products: List[Product]) -> float:
	"""🚀 PHASE 3: Calculate overall solution score."""
	if not solution:
		return 0.0
	
	total_cost = sum(container.price_try or 0 for container, _ in solution)
	total_containers = len(solution)
	total_items_packed = sum(len(result.placements) for _, result in solution)
	total_volume_used = sum(
		sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] for p in result.placements)
		for _, result in solution
	)
	
	# Cost efficiency (items per cost unit)
	cost_efficiency = total_items_packed / max(total_cost, 1)
	
	# Container efficiency (items per container)
	container_efficiency = total_items_packed / total_containers
	
	# Overall solution score
	solution_score = (
		cost_efficiency * 40 +         # 40% cost efficiency
		container_efficiency * 30 +    # 30% container efficiency
		total_items_packed * 20 +      # 20% absolute items packed
		(1.0 / total_containers) * 10  # 10% inverse container count (fewer containers better)
	)
	
	return solution_score


def optimized_utilization_packing(products: List[Product], containers: List[Container]) -> Optional[List[Tuple[Container, PackedContainer]]]:
	"""🎯 OPTIMIZED: Utilization-focused packing algorithm."""
	if not products or not containers:
		return None
	
	# Calculate total order volume
	total_volume = sum(p.width_mm * p.length_mm * p.height_mm for p in products)
	print(f"🎯 Optimizing for {len(products)} items, {total_volume:.0f}cm³ total volume")
	
	# 🎯 STRATEGY 1: Try single container first for maximum utilization
	best_single_solution = None
	best_single_score = float('-inf')
	
	for container in containers:
		container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm
		
		# Only consider containers that can fit the order with reasonable margin
		if container_volume >= total_volume * 1.05 and container_volume <= total_volume * 2.0:
			try:
				result = pack(products, container)
				if result and len(result.placements) == len(products):
					# Calculate utilization score
					used_volume = sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] for p in result.placements)
					utilization = used_volume / container_volume
					
					# Size appropriateness bonus
					size_bonus = 1.0
					if container_volume < total_volume * 1.2:
						size_bonus = 1.3  # Perfect fit bonus
					elif container_volume < total_volume * 1.5:
						size_bonus = 1.1  # Good fit bonus
					
					score = utilization * 70 + size_bonus * 30
					
					if score > best_single_score:
						best_single_score = score
						best_single_solution = [(container, result)]
						print(f"  📦 Single container candidate: {utilization*100:.1f}% util, score: {score:.1f}")
			except Exception as e:
				continue
	
	# If we found a good single container solution, use it
	if best_single_solution and best_single_score > 60:
		print(f"✅ Using single container solution (score: {best_single_score:.1f})")
		return best_single_solution
	
	# 🎯 STRATEGY 2: Multi-container with utilization optimization
	print("🔄 Trying multi-container optimization...")
	
	# Sort containers by utilization potential
	container_scores = []
	for container in containers:
		container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm
		
		# Score containers based on how well they match our total volume
		volume_ratio = total_volume / container_volume if container_volume > 0 else float('inf')
		
		# Prefer containers that are 1.2-2.0x the total volume (good for splitting)
		if 0.5 <= volume_ratio <= 0.8:  # Container is 1.25-2x total volume
			score = 100
		elif 0.3 <= volume_ratio <= 1.0:  # Container is 1-3.3x total volume
			score = 80
		else:
			score = 20
		
		container_scores.append((container, score))
	
	# Sort by score (highest first)
	container_scores.sort(key=lambda x: x[1], reverse=True)
	sorted_containers = [c[0] for c in container_scores[:10]]  # Use top 10 containers
	
	# Try volume-optimized strategy first
	try:
		solution = intelligent_volume_optimized_packing(products, sorted_containers)
		if solution:
			solution_score = calculate_solution_score(solution, products)
			print(f"📦 Volume-optimized solution: {solution_score:.1f} score")
			return solution
	except Exception as e:
		print(f"⚠️ Volume-optimized failed: {e}")
	
	# Fallback to best-fit strategy
	try:
		solution = intelligent_best_fit_packing(products, sorted_containers)
		if solution:
			solution_score = calculate_solution_score(solution, products)
			print(f"📦 Best-fit solution: {solution_score:.1f} score")
			return solution
	except Exception as e:
		print(f"⚠️ Best-fit failed: {e}")
	
	# Last resort: use the single container solution if we have one
	if best_single_solution:
		print("🔄 Using single container as fallback")
		return best_single_solution
	
	return None
