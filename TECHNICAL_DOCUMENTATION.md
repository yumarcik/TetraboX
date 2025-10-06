# 🔧 TetraboX: Technical Documentation

## 📋 **Table of Contents**

1. [Architecture Overview](#architecture-overview)
2. [Backend Systems](#backend-systems)
3. [Machine Learning Components](#machine-learning-components)
4. [Frontend Design System](#frontend-design-system)
5. [Packing Algorithms](#packing-algorithms)
6. [Data Models](#data-models)
7. [API Specifications](#api-specifications)
8. [Performance Optimization](#performance-optimization)
9. [Deployment & Infrastructure](#deployment--infrastructure)
10. [Development Guidelines](#development-guidelines)

---

## 🏗️ **Architecture Overview**

### **System Architecture**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend UI   │    │  FastAPI Server │    │  ML Predictor   │
│                 │    │                 │    │                 │
│ • React-like JS │◄──►│ • REST APIs     │◄──►│ • XGBoost       │
│ • 3D Canvas     │    │ • Order Mgmt    │    │ • Strategy AI   │
│ • Premium CSS   │    │ • Packing Logic │    │ • Feature Eng   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       │
         │              ┌─────────────────┐              │
         │              │   Data Layer    │              │
         │              │                 │              │
         └──────────────►│ • CSV Files     │◄─────────────┘
                        │ • Products      │
                        │ • Containers    │
                        │ • Orders        │
                        └─────────────────┘
```

### **Technology Stack**
- **Backend**: Python 3.9+, FastAPI, Uvicorn
- **ML/AI**: XGBoost, Scikit-learn, NumPy, Pandas
- **Frontend**: Vanilla JavaScript, HTML5 Canvas, CSS3
- **Data**: CSV files, Pandas DataFrames
- **Algorithms**: Custom 3D bin packing, heuristic optimization
- **Visualization**: Custom 3D rendering engine, WebGL-like projections

---

## 🖥️ **Backend Systems**

### **FastAPI Application Structure**

#### **Core Components**
```python
src/
├── server.py          # Main FastAPI application
├── models.py          # Data models and classes
├── schemas.py         # Pydantic validation schemas
├── packer.py          # Packing algorithms
├── io.py              # Data I/O operations
└── ml_strategy_selector.py  # ML strategy prediction
```

#### **Key Modules**

**1. Server Module (`server.py`)**
```python
# Main FastAPI app with endpoints:
- GET /                    # Premium UI interface
- POST /pack/order         # ML-enhanced packing
- GET /orders             # Order management
- POST /predict-strategy  # ML strategy prediction
- POST /ml/train          # Model training
- GET /ml/status          # ML model status
```

**2. Models Module (`models.py`)**
```python
@dataclass
class Product:
    sku: str
    width_mm: float
    length_mm: float  
    height_mm: float
    weight_g: float
    fragile: bool = False
    hazmat_class: Optional[str] = None

@dataclass  
class Container:
    box_id: str
    inner_w_mm: float
    inner_l_mm: float
    inner_h_mm: float
    max_weight_g: float
    price_try: Optional[float] = None
    
    @property
    def is_3d_box(self) -> bool:
        return self.container_type == "box" and self.inner_h_mm > 0
```

**3. Packing Module (`packer.py`)**
```python
# Core packing algorithms:
def pack(products, container) -> PackedContainer
def pack_greedy_max_utilization(products, containers)
def pack_best_fit(products, containers)  
def pack_largest_first_optimized(products, containers)
def try_aggressive_partial_packing(products, containers)
```

### **Data Flow Architecture**

```
Order Request → Product Expansion → ML Strategy Selection → Packing Algorithm → Result Optimization → Response
     │               │                      │                    │                  │              │
     ▼               ▼                      ▼                    ▼                  ▼              ▼
┌─────────┐   ┌─────────────┐   ┌─────────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ Order   │   │ Individual  │   │ Feature         │   │ Selected    │   │ Packed      │   │ JSON        │
│ Items   │   │ Products    │   │ Engineering     │   │ Algorithm   │   │ Containers  │   │ Response    │
│ + Qty   │   │ (expanded)  │   │ (19 features)   │   │ Execution   │   │ + Stats     │   │ + 3D Data   │
└─────────┘   └─────────────┘   └─────────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
```

---

## 🤖 **Machine Learning Components**

### **ML Strategy Selector Architecture**

#### **Feature Engineering Pipeline**
```python
# 19 Enhanced Features:
features = {
    # Order Characteristics (7 features)
    'total_items': int,
    'unique_skus': int, 
    'total_volume_cm3': float,
    'total_weight_g': float,
    'avg_item_volume': float,
    'volume_std': float,
    'size_diversity': max_volume / min_volume,
    
    # Container Relationship (4 features) - YOUR ENHANCED FEATURES
    'utilization_potential': total_volume / max_container_volume,
    'weight_ratio': total_weight / max_container_weight,
    'fragility_ratio': fragile_count / total_items,
    'hazmat_flag': bool (0 or 1),
    
    # Price Analysis (3 features)
    'cheapest_container_price': min(prices),
    'avg_viable_container_price': mean(viable_prices),
    'price_spread': (max_price - min_price) / avg_price,
    
    # Advanced Geometric (5 features)
    'aspect_ratio_variance': variance of w/h, l/h, w/l ratios,
    'stackability_score': flat_base_items / total_items,
    'container_fit_count': number of viable containers,
    'min_containers_needed': ceil(utilization_potential),
    'weight_to_volume_ratio': weight / volume density
}
```

#### **Model Architecture**
```python
# XGBoost Classifier Configuration
model = xgb.XGBClassifier(
    n_estimators=100,      # 100 decision trees
    max_depth=6,           # Tree depth for complexity control
    learning_rate=0.1,     # Conservative learning rate
    random_state=42,       # Reproducible results
    eval_metric='mlogloss' # Multi-class log loss
)

# Fallback: RandomForest if XGBoost unavailable
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    class_weight='balanced'  # Handle class imbalance
)
```

#### **Strategy Mapping**
```python
strategies = {
    'greedy': pack_greedy_max_utilization,      # Max utilization per container
    'best_fit': pack_best_fit,                  # Minimize waste, handle fragile
    'large_first': pack_largest_first_optimized, # Complex size distributions  
    'aggressive': try_aggressive_partial_packing # Multi-container fallback
}
```

#### **Rule-Based Fallback Logic**
```python
def rule_based_fallback(features):
    if features['utilization_potential'] > 1.2:
        return 'aggressive', 0.85  # Multi-container needed
    elif features['fragility_ratio'] > 0.3:
        return 'best_fit', 0.80    # Handle fragile items
    elif features['size_diversity'] > 10:
        return 'large_first', 0.75 # Complex sizes
    elif features['weight_ratio'] > 0.8:
        return 'best_fit', 0.78    # Weight constrained
    else:
        return 'greedy', 0.70      # Default efficient packing
```

---

## 🎨 **Frontend Design System**

### **CSS Architecture**

#### **Design Philosophy**
- **Glassmorphism**: Translucent elements with backdrop blur
- **Gradient-First**: Rich color gradients throughout the interface
- **Premium Feel**: High-end SaaS application aesthetics
- **Responsive**: Adapts to different screen sizes
- **Performance**: Optimized animations and transitions

#### **Color Palette**
```css
:root {
  /* Primary Gradients */
  --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  --gradient-success: linear-gradient(135deg, #10b981 0%, #059669 100%);
  --gradient-warning: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  --gradient-danger: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  
  /* Background Gradients */
  --bg-main: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  --bg-card: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  --bg-glass: rgba(255, 255, 255, 0.95);
  
  /* Text Colors */
  --text-primary: #2d3748;
  --text-secondary: #64748b;
  --text-light: #e2e8f0;
}
```

#### **Component System**

**1. Premium Cards**
```css
.premium-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  border: 1px solid rgba(102, 126, 234, 0.1);
  transition: all 0.3s ease;
}

.premium-card:hover {
  box-shadow: 0 8px 30px rgba(0,0,0,0.12);
  transform: translateY(-2px);
}
```

**2. Gradient Buttons**
```css
button {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 10px;
  padding: 12px 16px;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}
```

**3. Glassmorphism Sidebar**
```css
.sidebar {
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(10px);
  border-right: none;
  box-shadow: 4px 0 24px rgba(0,0,0,0.15);
}
```

### **3D Visualization Engine**

#### **Canvas Rendering System**
```javascript
// High-DPI Support
const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
canvas.width = displayWidth * pixelRatio;
canvas.height = displayHeight * pixelRatio;
ctx.scale(pixelRatio, pixelRatio);

// 3D Projection Mathematics
const project3D = (x, y, z) => {
  // Center coordinates
  const cx = x - maxW/2;
  const cy = y - maxL/2; 
  const cz = z - maxH/2;
  
  // Apply rotations (X then Y axis)
  const cosX = Math.cos(rotationX), sinX = Math.sin(rotationX);
  const cosY = Math.cos(rotationY), sinY = Math.sin(rotationY);
  
  // Rotate around X axis
  const y1 = cy * cosX - cz * sinX;
  const z1 = cy * sinX + cz * cosX;
  
  // Rotate around Y axis  
  const x2 = cx * cosY + z1 * sinY;
  const z2 = -cx * sinY + z1 * cosY;
  
  // Project to 2D screen coordinates
  const px = x2 * scale + offsetX;
  const py = -y1 * scale + offsetY;
  
  return [px, py, z2]; // Include Z for depth sorting
};
```

#### **Lighting System**
```javascript
// Dynamic lighting calculation
const calculateLighting = (face, corners) => {
  const lightDir = [0.5, -0.3, 0.8]; // Top-right-front light
  const faceNormals = [
    [0, 0, -1], [0, 0, 1],   // bottom, top
    [0, -1, 0], [0, 1, 0],   // front, back  
    [-1, 0, 0], [1, 0, 0]    // left, right
  ];
  
  const normal = faceNormals[face];
  // Rotate normal with object rotation
  // ... rotation math ...
  
  // Dot product for lighting intensity
  const dot = nx * lightDir[0] + ny * lightDir[1] + nz * lightDir[2];
  return 0.5 + 0.5 * Math.max(0, dot); // Range 0.5 to 1.0
};
```

#### **Performance Optimization**
```javascript
// Intersection Observer for performance
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    isVisible = entry.isIntersecting;
  });
}, { threshold: 0.1 });

// Optimized animation loop
const animate = (currentTime = 0) => {
  if (!isVisible && !autoRotate && !isDragging) {
    animationFrameId = requestAnimationFrame(animate);
    return; // Pause when not visible
  }
  
  const deltaTime = currentTime - lastRenderTime;
  if (deltaTime >= frameInterval) {
    const hasMovement = Math.abs(targetRotationX - rotationX) > 0.001 ||
                       Math.abs(targetRotationY - rotationY) > 0.001 ||
                       autoRotate;
    
    if (hasMovement || isDragging) {
      render();
      lastRenderTime = currentTime;
    }
  }
  
  animationFrameId = requestAnimationFrame(animate);
};
```

---

## 🧮 **Packing Algorithms**

### **Core Algorithm: Advanced 3D Bin Packing**

#### **Algorithm Overview**
```python
def pack(products: List[Product], container: Container) -> PackedContainer:
    """
    Advanced 3D bin packing with intelligent placement strategies
    
    Key Features:
    - Multi-orientation testing (6 rotations per item)
    - Smart candidate position generation
    - Fitness-based placement optimization
    - Conflict detection and resolution
    """
```

#### **Orientation Generation**
```python
def orientations(w, l, h):
    """Generate all unique orientations for an item"""
    perms = [
        (w, l, h, (0,1,2)), (w, h, l, (0,2,1)),  # Width-first
        (l, w, h, (1,0,2)), (l, h, w, (1,2,0)),  # Length-first  
        (h, w, l, (2,0,1)), (h, l, w, (2,1,0)),  # Height-first
    ]
    
    # Remove duplicate orientations (e.g., cube has only 1 unique orientation)
    seen = set()
    for ow, ol, oh, rot in perms:
        key = (ow, ol, oh)
        if key not in seen:
            seen.add(key)
            yield ow, ol, oh, rot
```

#### **Candidate Position Generation**
```python
def generate_candidate_positions(occupied_spaces, container, item_w, item_l, item_h):
    """Generate smart candidate positions for item placement"""
    candidates = [(0, 0, 0)]  # Always try origin
    
    # Generate positions based on existing items
    for x1, y1, z1, x2, y2, z2 in occupied_spaces:
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
    
    # Filter valid positions and sort by preference
    valid_candidates = [
        (x, y, z) for x, y, z in set(candidates)
        if (x >= 0 and y >= 0 and z >= 0 and
            x + item_w <= container.inner_w_mm and
            y + item_l <= container.inner_l_mm and
            z + item_h <= container.inner_h_mm)
    ]
    
    # Sort by preference: lower positions first, then closer to origin
    valid_candidates.sort(key=lambda pos: (pos[2], pos[1], pos[0]))
    return valid_candidates
```

#### **Fitness Function**
```python
def calculate_position_fitness(x, y, z, w, l, h, container):
    """Calculate fitness score for a position (lower is better)"""
    
    # Distance from bottom-left-front corner
    corner_distance = (x**2 + y**2 + z**2) ** 0.5
    
    # Height penalty (prefer lower positions for stability)
    height_penalty = z * 10
    
    # Stability bonus for ground level
    stability_bonus = -100 if z == 0 else 0
    
    # Contact bonus (prefer positions touching existing items)
    # ... additional contact detection logic ...
    
    return corner_distance + height_penalty + stability_bonus
```

### **Strategy Algorithms**

#### **1. Greedy Max Utilization**
```python
def pack_greedy_max_utilization(products, containers):
    """Fill each container to maximum capacity before moving to next"""
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
            
        packed_containers.append((best_container, best_pack))
        
        # Remove packed items from remaining list
        packed_skus = [p.sku for p in best_pack.placements]
        remaining_products = [p for p in remaining_products if p.sku not in packed_skus]
    
    return packed_containers
```

#### **2. Best Fit (Waste Minimization)**
```python
def pack_best_fit(products, containers):
    """Minimize wasted space by choosing optimal container sizes"""
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
                used_volume = sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] 
                                for p in result.placements)
                container_volume = (container.inner_w_mm * 
                                  container.inner_l_mm * 
                                  container.inner_h_mm)
                waste_ratio = ((container_volume - used_volume) / 
                             container_volume if container_volume > 0 else 1)
                
                if waste_ratio < best_waste_ratio:
                    best_pack = result
                    best_container = container
                    best_waste_ratio = waste_ratio
        
        # ... rest of algorithm ...
```

#### **3. Large First Optimized**
```python
def pack_largest_first_optimized(products, containers):
    """Try largest containers first with efficiency optimization"""
    # Sort containers by volume (largest first)
    sorted_containers = sorted(containers, 
                             key=lambda c: c.inner_w_mm * c.inner_l_mm * c.inner_h_mm, 
                             reverse=True)
    
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
        
        # ... rest of algorithm ...
```

#### **4. Aggressive Partial Packing**
```python
def try_aggressive_partial_packing(products, containers):
    """Optimized partial packing for very large orders"""
    
    # Sort containers by cost efficiency (price per volume)
    def container_efficiency(c):
        volume = c.inner_w_mm * c.inner_l_mm * c.inner_h_mm / 1000.0
        price = c.price_try or 0
        return price / volume if volume > 0 else float('inf')
    
    sorted_containers = sorted(containers, key=container_efficiency)
    
    # Sort products by volume (smallest first for better packing)
    sorted_products = sorted(products, 
                           key=lambda p: p.width_mm * p.length_mm * p.height_mm)
    
    remaining_products = sorted_products.copy()
    packed_containers = []
    max_containers = min(10, len(products))
    
    iteration = 0
    while remaining_products and iteration < max_containers:
        iteration += 1
        
        best_pack = None
        best_container = None
        best_score = -1
        
        # Try different group sizes: start with many items, reduce if needed
        group_sizes = [min(len(remaining_products), size) 
                      for size in [12, 10, 8, 6, 4, 3, 2, 1]]
        
        for group_size in group_sizes:
            test_group = remaining_products[:group_size]
            
            for container in sorted_containers:
                result = pack(test_group, container)
                if result and len(result.placements) > 0:
                    # Calculate comprehensive score
                    packed_count = len(result.placements)
                    total_item_volume = sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] 
                                          for p in result.placements) / 1000.0
                    container_volume = (container.inner_w_mm * container.inner_l_mm * 
                                      container.inner_h_mm / 1000.0)
                    utilization = (total_item_volume / container_volume 
                                 if container_volume > 0 else 0)
                    
                    # Only consider solutions with good utilization (minimum 40%)
                    if utilization < 0.4:
                        continue
                    
                    # Score heavily favors utilization (85%) + item count (15%)
                    item_ratio = packed_count / group_size
                    score = (utilization * 0.85) + (item_ratio * 0.15)
                    
                    # Bonuses for high utilization
                    if utilization >= 0.8:
                        score *= 1.5  # 50% bonus for 80%+ utilization
                    elif utilization >= 0.7:
                        score *= 1.3  # 30% bonus for 70%+ utilization
                    elif utilization >= 0.6:
                        score *= 1.2  # 20% bonus for 60%+ utilization
                    
                    if score > best_score:
                        best_pack = result
                        best_container = container
                        best_score = score
            
            # If we found a high-utilization solution, don't try smaller groups
            if best_score > 0.6:
                break
        
        # ... rest of algorithm ...
```

---

## 📊 **Data Models**

### **Core Data Structures**

#### **Product Model**
```python
@dataclass
class Product:
    sku: str                    # Unique product identifier
    width_mm: float            # Width in millimeters
    length_mm: float           # Length in millimeters  
    height_mm: float           # Height in millimeters
    weight_g: float            # Weight in grams
    fragile: bool = False      # Fragility flag for special handling
    packaging_type: Optional[str] = None    # Packaging requirements
    hazmat_class: Optional[str] = None      # Hazardous material classification
    
    @property
    def volume_cm3(self) -> float:
        """Calculate volume in cubic centimeters"""
        return (self.width_mm * self.length_mm * self.height_mm) / 1000.0
    
    @property
    def density_g_cm3(self) -> float:
        """Calculate density in grams per cubic centimeter"""
        volume = self.volume_cm3
        return self.weight_g / volume if volume > 0 else 0
```

#### **Container Model**
```python
@dataclass
class Container:
    box_id: str                # Unique container identifier
    inner_w_mm: float         # Internal width in millimeters
    inner_l_mm: float         # Internal length in millimeters
    inner_h_mm: float         # Internal height in millimeters
    tare_weight_g: float      # Empty container weight
    max_weight_g: float       # Maximum weight capacity
    material: Optional[str] = None           # Container material
    price_try: Optional[float] = None        # Container cost in Turkish Lira
    stock: int = 1                          # Available quantity
    usage_limit: Optional[str] = None        # Usage restrictions
    box_name: Optional[str] = None          # Human-readable name
    shipping_company: Optional[str] = None   # Associated shipping company
    container_type: str = "box"             # Type: "box" or "envelope"
    
    @property
    def is_3d_box(self) -> bool:
        """Check if this container supports 3D packing"""
        return self.container_type == "box" and self.inner_h_mm > 0
    
    @property
    def volume_cm3(self) -> float:
        """Calculate internal volume in cubic centimeters"""
        return (self.inner_w_mm * self.inner_l_mm * self.inner_h_mm) / 1000.0
    
    @property
    def cost_per_cm3(self) -> float:
        """Calculate cost efficiency (price per cubic centimeter)"""
        volume = self.volume_cm3
        price = self.price_try or 0
        return price / volume if volume > 0 else float('inf')
```

#### **Placement Model**
```python
@dataclass
class PlacementItem:
    sku: str                                    # Product SKU
    position_mm: Tuple[float, float, float]     # (x, y, z) position in mm
    size_mm: Tuple[float, float, float]         # (w, l, h) dimensions in mm
    rotation: Tuple[int, int, int]              # Rotation indices (0,1,2)
    
    @property
    def bounds(self) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """Get bounding box coordinates"""
        x, y, z = self.position_mm
        w, l, h = self.size_mm
        return (x, y, z), (x + w, y + l, z + h)
    
    @property
    def center(self) -> Tuple[float, float, float]:
        """Get center point of placed item"""
        x, y, z = self.position_mm
        w, l, h = self.size_mm
        return (x + w/2, y + l/2, z + h/2)
```

#### **Order Models**
```python
@dataclass
class OrderItem:
    sku: str                              # Product SKU
    quantity: int                         # Quantity ordered
    unit_price_try: Optional[float] = None    # Unit price in Turkish Lira
    total_price_try: Optional[float] = None   # Total price for this item
    
    def __post_init__(self):
        """Calculate total price if not provided"""
        if self.total_price_try is None and self.unit_price_try is not None:
            self.total_price_try = self.unit_price_try * self.quantity

@dataclass
class Order:
    order_id: str                         # Unique order identifier
    customer_name: str                    # Customer name
    customer_email: str                   # Customer email
    order_date: datetime                  # Order creation date
    status: str                          # Order status
    items: List[OrderItem]               # List of ordered items
    total_items: int = 0                 # Total item count
    total_price_try: float = 0.0         # Total order value
    shipping_company: Optional[str] = None    # Preferred shipping company
    container_count: int = 0             # Number of containers used
    utilization_avg: float = 0.0         # Average container utilization
    notes: Optional[str] = None          # Additional notes
    
    def __post_init__(self):
        """Calculate totals after initialization"""
        if not self.total_items:
            self.total_items = sum(item.quantity for item in self.items)
        if not self.total_price_try:
            self.total_price_try = sum(item.total_price_try or 0 for item in self.items)
```

### **Response Models (Pydantic)**

#### **Packing Response**
```python
class OrderPackResponse(BaseModel):
    order_id: str
    success: bool
    containers: List[ContainerResult]
    total_price: float
    total_items: int
    container_count: int
    
    # Legacy compatibility fields
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
    
    # Container dimensions for 3D visualization
    inner_w_mm: Optional[float] = None
    inner_l_mm: Optional[float] = None
    inner_h_mm: Optional[float] = None

class ContainerResult(BaseModel):
    container_id: str
    container_name: Optional[str] = None
    shipping_company: Optional[str] = None
    container_material: Optional[str] = None
    container_type: Optional[str] = None
    placements: List[Placement]
    utilization: float
    remaining_volume_cm3: float
    container_volume_cm3: float
    price_try: Optional[float] = None
    
    # Actual container dimensions
    inner_w_mm: Optional[float] = None
    inner_l_mm: Optional[float] = None
    inner_h_mm: Optional[float] = None
```

---

## 🔌 **API Specifications**

### **Core Endpoints**

#### **1. Order Packing (ML-Enhanced)**
```http
POST /pack/order
Content-Type: application/json

{
  "order_id": "ORD-12345",
  "items": [
    {
      "sku": "PROD-001",
      "quantity": 2
    },
    {
      "sku": "PROD-002", 
      "quantity": 1
    }
  ]
}
```

**Response:**
```json
{
  "order_id": "ORD-12345",
  "success": true,
  "container_count": 1,
  "total_items": 3,
  "total_price": 45.50,
  "utilization": 0.847,
  "containers": [
    {
      "container_id": "BOX-001",
      "container_name": "Medium Box",
      "shipping_company": "Aras Kargo",
      "utilization": 0.847,
      "price_try": 45.50,
      "placements": [
        {
          "sku": "PROD-001",
          "position_mm": [0, 0, 0],
          "size_mm": [100, 150, 50],
          "rotation": [0, 1, 2]
        }
      ],
      "inner_w_mm": 300,
      "inner_l_mm": 200,
      "inner_h_mm": 150
    }
  ]
}
```

#### **2. ML Strategy Prediction**
```http
POST /predict-strategy
Content-Type: application/json

{
  "order_id": "ORD-12345",
  "items": [
    {"sku": "PROD-001", "quantity": 5},
    {"sku": "PROD-002", "quantity": 2}
  ]
}
```

**Response:**
```json
{
  "order_id": "ORD-12345",
  "predicted_strategy": "greedy",
  "confidence": 0.847,
  "model_available": true,
  "total_items": 7,
  "unique_skus": 2,
  "features": {
    "total_items": 7.0,
    "utilization_potential": 0.743,
    "weight_ratio": 0.234,
    "fragility_ratio": 0.0,
    "hazmat_flag": 0.0,
    "size_diversity": 2.34
  },
  "feature_importance": {
    "utilization_potential": 0.234,
    "weight_ratio": 0.187,
    "total_items": 0.156,
    "fragility_ratio": 0.123
  },
  "recommendation_reason": "Greedy strategy recommended for efficient single-container packing due to: high utilization potential"
}
```

#### **3. ML Model Training**
```http
POST /ml/train?sample_size=200
```

**Response:**
```json
{
  "success": true,
  "message": "ML model trained successfully",
  "training_samples": 200,
  "feature_count": 19,
  "strategies": ["greedy", "best_fit", "large_first", "aggressive"],
  "feature_importance": {
    "utilization_potential": 0.234,
    "weight_ratio": 0.187,
    "total_items": 0.156,
    "fragility_ratio": 0.123,
    "size_diversity": 0.098
  },
  "model_path": "models/strategy_selector.pkl"
}
```

#### **4. ML Model Status**
```http
GET /ml/status
```

**Response:**
```json
{
  "model_available": true,
  "model_path": "models/strategy_selector.pkl",
  "model_type": "XGBClassifier",
  "feature_count": 19,
  "strategies": ["greedy", "best_fit", "large_first", "aggressive"],
  "feature_names": [
    "total_items", "unique_skus", "total_volume_cm3",
    "utilization_potential", "weight_ratio", "fragility_ratio"
  ],
  "feature_importance": {
    "utilization_potential": 0.234,
    "weight_ratio": 0.187
  }
}
```

### **Order Management Endpoints**

#### **List Orders**
```http
GET /orders?status=pending&limit=50&offset=0
```

#### **Get Specific Order**
```http
GET /orders/{order_id}
```

#### **Create Order**
```http
POST /orders
Content-Type: application/json

{
  "customer_name": "John Doe",
  "customer_email": "john@example.com",
  "items": [
    {
      "sku": "PROD-001",
      "quantity": 2,
      "unit_price_try": 25.00,
      "total_price_try": 50.00
    }
  ],
  "notes": "Fragile items, handle with care"
}
```

#### **Update Order**
```http
PUT /orders/{order_id}
Content-Type: application/json

{
  "status": "processing",
  "notes": "Updated shipping requirements"
}
```

#### **Delete Order**
```http
DELETE /orders/{order_id}
```

---

## ⚡ **Performance Optimization**

### **Backend Performance**

#### **Algorithm Optimization**
```python
# Efficient candidate position generation
def generate_candidate_positions_optimized(occupied_spaces, container, item_dims):
    """Optimized position generation with spatial indexing"""
    
    # Use spatial data structures for faster collision detection
    # Implement octree or similar for large numbers of items
    
    # Pre-filter positions based on container bounds
    # Use geometric heuristics to reduce search space
    
    # Cache frequently used calculations
    pass

# Memory-efficient product expansion
def expand_order_items_efficiently(items, product_by_sku):
    """Memory-efficient expansion of order items"""
    products = []
    for item in items:
        product = product_by_sku[item.sku]
        # Use generator or iterator for large quantities
        for _ in range(item.quantity):
            products.append(product)
    return products
```

#### **Caching Strategy**
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_pack_single_container(product_hash, container_id):
    """Cache packing results for identical product sets"""
    pass

@lru_cache(maxsize=100)
def cached_feature_extraction(product_signature, container_signature):
    """Cache ML feature extraction for similar orders"""
    pass
```

### **Frontend Performance**

#### **3D Rendering Optimization**
```javascript
// Optimized animation loop with frame rate control
const targetFPS = 45; // Balanced quality vs performance
const frameInterval = 1000 / targetFPS;

const animate = (currentTime = 0) => {
  if (!isVisible && !autoRotate && !isDragging) {
    // Pause when not visible
    animationFrameId = requestAnimationFrame(animate);
    return;
  }
  
  const deltaTime = currentTime - lastRenderTime;
  
  if (deltaTime >= frameInterval) {
    // Only render if something changed
    const hasMovement = Math.abs(targetRotationX - rotationX) > 0.001 || 
                       Math.abs(targetRotationY - rotationY) > 0.001 || 
                       autoRotate;
    
    if (hasMovement || isDragging) {
      render();
      lastRenderTime = currentTime;
    }
  }
  
  animationFrameId = requestAnimationFrame(animate);
};

// Intersection Observer for visibility-based optimization
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    isVisible = entry.isIntersecting;
  });
}, { threshold: 0.1 });
```

#### **Canvas Optimization**
```javascript
// High-DPI support with performance balance
const pixelRatio = Math.min(window.devicePixelRatio || 1, 2); // Cap at 2x
canvas.width = displayWidth * pixelRatio;
canvas.height = displayHeight * pixelRatio;
ctx.scale(pixelRatio, pixelRatio);

// Optimized canvas size
const displayWidth = Math.min(containerWidth, 900);
const displayHeight = Math.min(containerHeight, 500);

// Efficient face sorting and culling
faces.sort((a, b) => a.z - b.z); // Back-to-front rendering
// Implement frustum culling for large scenes
```

#### **Memory Management**
```javascript
// Cleanup animation frames
window.addEventListener('beforeunload', () => {
  if(animationFrameId) {
    cancelAnimationFrame(animationFrameId);
  }
});

// Efficient object pooling for large datasets
class ObjectPool {
  constructor(createFn, resetFn) {
    this.createFn = createFn;
    this.resetFn = resetFn;
    this.pool = [];
  }
  
  acquire() {
    return this.pool.pop() || this.createFn();
  }
  
  release(obj) {
    this.resetFn(obj);
    this.pool.push(obj);
  }
}
```

---

## 🚀 **Deployment & Infrastructure**

### **Development Environment**
```bash
# Python environment setup
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Required dependencies
pip install fastapi uvicorn pandas numpy scikit-learn xgboost joblib

# Run development server
python main.py
# or
uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload
```

### **Production Deployment**

#### **Docker Configuration**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create models directory
RUN mkdir -p models

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### **Docker Compose**
```yaml
version: '3.8'

services:
  tetrabox:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./models:/app/models
    environment:
      - PYTHONPATH=/app
    restart: unless-stopped
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - tetrabox
    restart: unless-stopped
```

#### **Production Requirements**
```txt
# requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pandas==2.1.3
numpy==1.24.3
scikit-learn==1.3.2
xgboost==2.0.2
joblib==1.3.2
pydantic==2.5.0
python-multipart==0.0.6
```

### **Performance Monitoring**

#### **Health Check Endpoint**
```python
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "ml_model_available": strategy_predictor.model is not None,
        "features_count": len(strategy_predictor.feature_names)
    }
```

#### **Metrics Collection**
```python
import time
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            print(f"✅ {func.__name__} completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ {func.__name__} failed in {duration:.3f}s: {e}")
            raise
    return wrapper

@app.post("/pack/order")
@monitor_performance
async def pack_order_endpoint(req: OrderPackRequest):
    # ... implementation ...
```

---

## 📋 **Development Guidelines**

### **Code Style & Standards**

#### **Python Code Style**
```python
# Follow PEP 8 with these specific guidelines:

# 1. Type hints for all function parameters and returns
def pack_order(products: List[Product], containers: List[Container]) -> Optional[List[Tuple[Container, PackedContainer]]]:
    pass

# 2. Docstrings for all public functions
def calculate_utilization(placements: List[PlacementItem], container: Container) -> float:
    """
    Calculate container utilization percentage.
    
    Args:
        placements: List of placed items
        container: Container being analyzed
        
    Returns:
        Utilization percentage as float between 0.0 and 1.0
    """
    pass

# 3. Error handling with specific exceptions
try:
    result = pack(products, container)
except ValueError as e:
    raise HTTPException(status_code=400, detail=f"Invalid input: {e}")
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Packing failed: {e}")

# 4. Logging for debugging and monitoring
import logging
logger = logging.getLogger(__name__)

def complex_algorithm():
    logger.info("Starting complex algorithm")
    logger.debug(f"Processing {len(items)} items")
    logger.warning("Performance may be slow for large datasets")
```

#### **JavaScript Code Style**
```javascript
// 1. Use const/let, avoid var
const canvas = document.createElement('canvas');
let rotationX = 0.5;

// 2. Arrow functions for callbacks
const animate = (currentTime = 0) => {
  // Animation logic
};

// 3. Destructuring for cleaner code
const {width, height, depth} = dimensions;
const [x, y, z] = position;

// 4. Template literals for strings
const message = `Processing ${itemCount} items in ${containerName}`;

// 5. Error handling with try-catch
try {
  const result = await fetch('/api/pack');
  const data = await result.json();
} catch (error) {
  console.error('Packing request failed:', error);
  showErrorMessage('Failed to pack order. Please try again.');
}
```

#### **CSS Organization**
```css
/* 1. CSS Custom Properties for consistency */
:root {
  --color-primary: #667eea;
  --color-success: #10b981;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --border-radius: 12px;
}

/* 2. BEM-like naming convention */
.order-card {
  /* Block */
}

.order-card__header {
  /* Element */
}

.order-card--selected {
  /* Modifier */
}

/* 3. Mobile-first responsive design */
.container {
  width: 100%;
  padding: var(--spacing-sm);
}

@media (min-width: 768px) {
  .container {
    padding: var(--spacing-md);
    max-width: 1200px;
  }
}
```

### **Testing Strategy**

#### **Unit Tests**
```python
import pytest
from src.packer import pack, orientations
from src.models import Product, Container

def test_orientations_generation():
    """Test that orientations generates correct rotations"""
    orientations_list = list(orientations(100, 200, 50))
    assert len(orientations_list) <= 6  # Maximum 6 unique orientations
    assert (100, 200, 50, (0, 1, 2)) in orientations_list

def test_pack_single_item():
    """Test packing a single item in a container"""
    product = Product(sku="TEST-001", width_mm=100, length_mm=100, height_mm=50, weight_g=500)
    container = Container(box_id="BOX-001", inner_w_mm=200, inner_l_mm=200, inner_h_mm=100, 
                         tare_weight_g=100, max_weight_g=5000)
    
    result = pack([product], container)
    
    assert result is not None
    assert len(result.placements) == 1
    assert result.placements[0].sku == "TEST-001"

def test_pack_oversized_item():
    """Test that oversized items are rejected"""
    product = Product(sku="BIG-001", width_mm=300, length_mm=300, height_mm=300, weight_g=1000)
    container = Container(box_id="SMALL-001", inner_w_mm=200, inner_l_mm=200, inner_h_mm=100,
                         tare_weight_g=100, max_weight_g=5000)
    
    result = pack([product], container)
    
    assert result is None  # Should fail to pack
```

#### **Integration Tests**
```python
import pytest
from fastapi.testclient import TestClient
from src.server import app

client = TestClient(app)

def test_pack_order_endpoint():
    """Test the complete pack order flow"""
    order_data = {
        "order_id": "TEST-001",
        "items": [
            {"sku": "PROD-001", "quantity": 2},
            {"sku": "PROD-002", "quantity": 1}
        ]
    }
    
    response = client.post("/pack/order", json=order_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["order_id"] == "TEST-001"
    assert len(data["containers"]) > 0

def test_ml_prediction_endpoint():
    """Test ML strategy prediction"""
    order_data = {
        "order_id": "TEST-ML-001",
        "items": [{"sku": "PROD-001", "quantity": 5}]
    }
    
    response = client.post("/predict-strategy", json=order_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "predicted_strategy" in data
    assert data["predicted_strategy"] in ["greedy", "best_fit", "large_first", "aggressive"]
    assert "confidence" in data
```

### **Documentation Standards**

#### **API Documentation**
```python
@app.post("/pack/order", response_model=OrderPackResponse)
def pack_order_endpoint(req: OrderPackRequest) -> OrderPackResponse:
    """
    🤖 Pack an order using ML-enhanced strategy selection
    
    This endpoint uses machine learning to automatically select the optimal
    packing strategy based on order characteristics and container constraints.
    
    **Process:**
    1. Expand order items into individual products
    2. Extract 19 engineered features from the order
    3. Use ML model to predict optimal strategy
    4. Execute the recommended packing algorithm
    5. Return detailed packing results with 3D visualization data
    
    **Strategies:**
    - `greedy`: Maximize utilization per container
    - `best_fit`: Minimize waste, handle fragile items
    - `large_first`: Optimize for complex size distributions
    - `aggressive`: Multi-container partial packing
    
    **Args:**
        req: Order packing request containing order_id and items
        
    **Returns:**
        Detailed packing results including:
        - Container assignments and utilization
        - 3D placement coordinates for visualization
        - Cost analysis and optimization metrics
        - ML prediction confidence and reasoning
        
    **Raises:**
        HTTPException: 400 for invalid SKUs, 500 for packing failures
        
    **Example:**
        ```python
        request = {
            "order_id": "ORD-12345",
            "items": [
                {"sku": "PROD-001", "quantity": 2},
                {"sku": "PROD-002", "quantity": 1}
            ]
        }
        ```
    """
```

#### **Algorithm Documentation**
```python
def pack(products: List[Product], container: Container) -> Optional[PackedContainer]:
    """
    Advanced 3D bin packing algorithm with intelligent placement optimization.
    
    **Algorithm Overview:**
    This implementation uses a sophisticated approach that combines:
    - Multi-orientation testing (up to 6 rotations per item)
    - Smart candidate position generation based on existing placements
    - Fitness-based placement optimization considering stability and efficiency
    - Comprehensive conflict detection and resolution
    
    **Key Features:**
    - **Orientation Optimization**: Tests all valid rotations for each item
    - **Position Intelligence**: Generates candidate positions near existing items
    - **Stability Preference**: Favors lower, more stable placements
    - **Conflict Resolution**: Ensures no overlapping placements
    - **Efficiency Focus**: Maximizes space utilization
    
    **Complexity:**
    - Time: O(n * m * k) where n=items, m=positions, k=orientations
    - Space: O(n) for placement tracking
    
    **Performance:**
    - Typical: <100ms for 10-20 items
    - Large orders: <1s for 50+ items
    - Memory efficient with minimal allocations
    
    **Args:**
        products: List of products to pack (order matters for optimization)
        container: Target container with dimension and weight constraints
        
    **Returns:**
        PackedContainer with placement details, or None if packing fails
        
    **Algorithm Steps:**
    1. Sort products by volume (largest first) for better packing efficiency
    2. For each product:
        a. Test all valid orientations (up to 6 rotations)
        b. Generate candidate positions based on existing placements
        c. Evaluate each position using fitness function
        d. Select best position considering stability and efficiency
        e. Place item and update occupied space tracking
    3. Return complete packing solution or None if any item fails
    
    **Fitness Function:**
    The placement fitness considers:
    - Distance from origin (prefer corner placement)
    - Height penalty (prefer lower positions for stability)
    - Stability bonus (ground-level placement)
    - Contact bonus (adjacent to existing items)
    
    **Example:**
        ```python
        products = [
            Product(sku="A", width_mm=100, length_mm=100, height_mm=50, weight_g=500),
            Product(sku="B", width_mm=150, length_mm=80, height_mm=60, weight_g=300)
        ]
        container = Container(box_id="BOX1", inner_w_mm=300, inner_l_mm=200, 
                            inner_h_mm=150, max_weight_g=5000)
        
        result = pack(products, container)
        if result:
            print(f"Packed {len(result.placements)} items")
            for placement in result.placements:
                print(f"{placement.sku} at {placement.position_mm}")
        ```
    """
```

---

## 🔍 **Debugging & Troubleshooting**

### **Common Issues**

#### **1. ML Model Not Loading**
```python
# Check model file existence
import os
if not os.path.exists("models/strategy_selector.pkl"):
    print("❌ ML model not found. Run POST /ml/train to create model.")

# Check dependencies
try:
    import xgboost
    print("✅ XGBoost available")
except ImportError:
    print("⚠️ XGBoost not available, using RandomForest fallback")
```

#### **2. 3D Rendering Issues**
```javascript
// Debug canvas context
if (!ctx) {
    console.error("❌ Canvas context not available");
    return;
}

// Check canvas dimensions
console.log(`Canvas: ${canvas.width}x${canvas.height}, Display: ${displayWidth}x${displayHeight}`);

// Debug 3D projection
const testPoint = project3D(100, 100, 100);
console.log(`Test projection: [${testPoint[0]}, ${testPoint[1]}, ${testPoint[2]}]`);

// Monitor animation performance
let frameCount = 0;
let lastFPSCheck = Date.now();

const checkFPS = () => {
    frameCount++;
    const now = Date.now();
    if (now - lastFPSCheck >= 1000) {
        console.log(`FPS: ${frameCount}`);
        frameCount = 0;
        lastFPSCheck = now;
    }
};
```

#### **3. Packing Algorithm Failures**
```python
# Debug packing process
def debug_pack(products, container):
    print(f"🔍 Packing {len(products)} products in {container.box_id}")
    print(f"Container: {container.inner_w_mm}x{container.inner_l_mm}x{container.inner_h_mm}mm")
    
    total_volume = sum(p.width_mm * p.length_mm * p.height_mm for p in products) / 1000.0
    container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm / 1000.0
    
    print(f"Volume ratio: {total_volume:.1f}cm³ / {container_volume:.1f}cm³ = {total_volume/container_volume:.2f}")
    
    if total_volume > container_volume:
        print("⚠️ Items exceed container volume")
    
    # Check individual item constraints
    for i, product in enumerate(products):
        fits = (product.width_mm <= container.inner_w_mm and 
                product.length_mm <= container.inner_l_mm and 
                product.height_mm <= container.inner_h_mm)
        print(f"Item {i} ({product.sku}): {product.width_mm}x{product.length_mm}x{product.height_mm}mm - {'✅' if fits else '❌'}")
```

### **Performance Profiling**

#### **Backend Profiling**
```python
import cProfile
import pstats

def profile_packing():
    """Profile packing performance"""
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run packing algorithm
    result = pack(test_products, test_container)
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 functions
```

#### **Frontend Profiling**
```javascript
// Performance monitoring
const performanceMonitor = {
    start: (label) => {
        console.time(label);
        performance.mark(`${label}-start`);
    },
    
    end: (label) => {
        console.timeEnd(label);
        performance.mark(`${label}-end`);
        performance.measure(label, `${label}-start`, `${label}-end`);
    },
    
    getMetrics: () => {
        const measures = performance.getEntriesByType('measure');
        return measures.map(m => ({
            name: m.name,
            duration: m.duration.toFixed(2) + 'ms'
        }));
    }
};

// Usage
performanceMonitor.start('3d-render');
render3D(packingData);
performanceMonitor.end('3d-render');
```

---

This technical documentation provides a comprehensive overview of TetraboX's architecture, implementation details, and development practices. It serves as both a reference for current developers and a guide for future contributors to understand and extend the system effectively.

The combination of advanced algorithms, machine learning intelligence, and premium user experience makes TetraboX a sophisticated platform for 3D container optimization, setting new standards in logistics technology.
