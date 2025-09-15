from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from typing import List, Optional, Tuple
from .schemas import PackRequest, PackResponse, Placement, OrderPackRequest, OrderPackResponse, ContainerResult
from .models import Product, Container
from .io import load_products_csv, load_containers_csv
from .packer import pack, find_optimal_multi_packing
from .models import Product, Container, PackedContainer


app = FastAPI(title="TetraboX API", version="0.1.0")


def try_aggressive_partial_packing(products: List[Product], containers: List[Container]) -> Optional[List[Tuple[Container, PackedContainer]]]:
	"""
	Optimized partial packing with smart container selection and utilization maximization.
	"""
	# Sort containers by cost efficiency (price per volume)
	def container_efficiency(c):
		volume = c.inner_w_mm * c.inner_l_mm * c.inner_h_mm / 1000.0
		price = c.price_try or 0
		return price / volume if volume > 0 else float('inf')
	
	sorted_containers = sorted(containers, key=container_efficiency)
	
	# Sort products by volume (smallest first for better packing)
	sorted_products = sorted(products, key=lambda p: p.width_mm * p.length_mm * p.height_mm)
	
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
		group_sizes = [min(len(remaining_products), size) for size in [12, 10, 8, 6, 4, 3, 2, 1]]
		
		for group_size in group_sizes:
			test_group = remaining_products[:group_size]
			
			# Try each container type and find the best utilization/cost ratio
			for container in sorted_containers:
				result = pack(test_group, container)
				if result and len(result.placements) > 0:
					# Calculate comprehensive score
					packed_count = len(result.placements)
					total_item_volume = sum(p.size_mm[0] * p.size_mm[1] * p.size_mm[2] for p in result.placements) / 1000.0
					container_volume = container.inner_w_mm * container.inner_l_mm * container.inner_h_mm / 1000.0
					utilization = total_item_volume / container_volume if container_volume > 0 else 0
					
					# Only consider solutions with good utilization (minimum 40%)
					if utilization < 0.4:
						continue
					
					# Score heavily favors utilization (85%) + item count (15%)
					item_ratio = packed_count / group_size
					score = (utilization * 0.85) + (item_ratio * 0.15)
					
					# Strong bonus for high utilization
					if utilization >= 0.8:
						score *= 1.5  # 50% bonus for 80%+ utilization
					elif utilization >= 0.7:
						score *= 1.3  # 30% bonus for 70%+ utilization
					elif utilization >= 0.6:
						score *= 1.2  # 20% bonus for 60%+ utilization
					
					# Penalty for expensive containers unless utilization is very high
					if (container.price_try or 0) > 50 and utilization < 0.75:
						score *= 0.8
					
					if score > best_score:
						best_pack = result
						best_container = container
						best_score = score
			
			# If we found a high-utilization solution, don't try smaller groups
			if best_score > 0.6:  # High threshold for good utilization
				break
		
		if not best_pack:
			# Skip this iteration if we can't pack anything
			if remaining_products:
				remaining_products.pop(0)  # Remove first item to try with others
			continue
		else:
			# Add this container to solution
			packed_containers.append((best_container, best_pack))
			
			# Remove packed items
			packed_skus = [p.sku for p in best_pack.placements]
			for sku in packed_skus:
				for i, product in enumerate(remaining_products):
					if product.sku == sku:
						remaining_products.pop(i)
						break
	
	# Return partial result if we packed at least 5% of items
	packed_item_count = len(products) - len(remaining_products)
	success_threshold = max(1, len(products) * 0.05)
	
	if packed_containers and packed_item_count >= success_threshold:
		return packed_containers
	
	return None


@app.get("/", response_class=HTMLResponse)
def index():
	return """
<!doctype html>
<html>
<head>
<meta charset=\"utf-8\" />
<title>TetraboX Order Packer</title>
<style>
body { 
  font-family: Arial, sans-serif; 
  margin: 0; 
  display: flex; 
  height: 100vh; 
  background: #f5f5f5;
}
.sidebar {
  width: 320px;
  background: white;
  border-right: 2px solid #ddd;
  padding: 15px;
  box-shadow: 2px 0 5px rgba(0,0,0,0.1);
  overflow-y: auto;
  position: fixed;
  height: 100vh;
  left: 0;
  top: 0;
}
.main-content {
  margin-left: 350px;
  padding: 20px;
  width: calc(100% - 350px);
  overflow-y: auto;
}
.sku-panel {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 20px;
}
.sku-list {
  max-height: 350px;
  overflow-y: auto;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: white;
}
.sku-item {
  padding: 10px 12px;
  border-bottom: 1px solid #eee;
  cursor: pointer;
  transition: background 0.2s;
}
.sku-item:hover {
  background: #e3f2fd;
}
.sku-item:last-child {
  border-bottom: none;
}
.sku-code {
  font-weight: bold;
  color: #1976d2;
  font-size: 13px;
}
.sku-name {
  font-size: 11px;
  color: #666;
  margin-top: 2px;
  line-height: 1.3;
}
input, button { 
  padding: 8px; 
  margin: 4px;
  border: 1px solid #ddd;
  border-radius: 4px;
}
button { 
  background: #007bff; 
  color: white; 
  border: none; 
  cursor: pointer; 
  font-weight: bold;
}
button:hover { 
  background: #0056b3; 
}
.search-box {
  width: calc(100% - 20px);
  margin-bottom: 10px;
  padding: 10px;
  font-size: 14px;
}
.order-list {
  background: white; 
  border: 1px solid #ddd; 
  border-radius: 4px; 
  padding: 10px; 
  max-height: 200px; 
  overflow-y: auto;
  font-size: 12px;
}
#log{white-space:pre; background:#f7f7f7; padding:10px; border:1px solid #ddd}
h1, h2, h3, h4 {
  color: #333;
  margin-top: 0;
}

/* Modal Styles */
.modal {
  display: none;
  position: fixed;
  z-index: 1000;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0,0,0,0.5);
  animation: fadeIn 0.3s;
}

.modal-content {
  background-color: white;
  margin: 2% auto;
  border-radius: 12px;
  width: 95%;
  max-width: 1200px;
  max-height: 90vh;
  overflow-y: auto;
  animation: slideIn 0.3s;
  box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 25px;
  border-bottom: 1px solid #ddd;
  background: #f8f9fa;
  border-radius: 12px 12px 0 0;
}

.modal-header h2 {
  margin: 0;
  color: #333;
}

.close {
  font-size: 28px;
  font-weight: bold;
  cursor: pointer;
  color: #999;
  transition: color 0.2s;
}

.close:hover {
  color: #333;
}

.modal-body {
  padding: 20px 25px;
}

.modal-tabs {
  display: flex;
  gap: 5px;
  margin: 20px 0;
  border-bottom: 1px solid #ddd;
}

.tab-button {
  padding: 10px 20px;
  border: none;
  background: #f8f9fa;
  cursor: pointer;
  border-radius: 8px 8px 0 0;
  transition: all 0.2s;
  font-weight: bold;
}

.tab-button.active {
  background: #007bff;
  color: white;
}

.tab-button:hover:not(.active) {
  background: #e9ecef;
}

.tab-content {
  display: none;
  padding: 20px 0;
}

.tab-content.active {
  display: block;
}

.compact-result {
  background: #e8f5e8;
  border: 1px solid #28a745;
  border-radius: 8px;
  padding: 15px;
  margin: 15px 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.result-summary {
  flex: 1;
}

.result-actions {
  display: flex;
  gap: 10px;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideIn {
  from { transform: translateY(-50px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
</style>
</head>
<body>

<div class="sidebar">
  <h3>📦 SKU Browser</h3>
  <div class="sku-panel">
    <input type="text" id="skuSearch" class="search-box" placeholder="🔍 Search SKUs..." onkeyup="filterSkus()">
    <div class="sku-list" id="skuList">
      <div style="padding: 20px; text-align: center; color: #666;">
        Click "Load SKUs" to see available products
      </div>
    </div>
    <button onclick="loadAllSkus()" style="width: calc(100% - 10px);">Load SKUs</button>
  </div>
  
  <h4>🛒 Current Order</h4>
  <div class="order-list">
    <div id="itemList">No items added yet</div>
  </div>
  <button onclick="clearOrder()" style="width: calc(100% - 10px); background: #dc3545;">Clear Order</button>
</div>

<div class="main-content">
<h2>Order Packer</h2>
<div>
	<label>Order ID:</label>
	<input id=\"orderId\" value=\"ORD-1\" />
	<button onclick=\"submitOrder()\" style=\"margin-left: 10px; padding: 10px 20px; font-size: 16px;\">🚀 Pack Order</button>
</div>
<div style="margin: 20px 0; padding: 15px; background: #e8f5e8; border-radius: 8px; border-left: 4px solid #28a745;">
	<strong>📋 Instructions:</strong>
	<ol style="margin: 10px 0;">
		<li>Browse and search SKUs in the left sidebar</li>
		<li>Click on any SKU to add it to your order</li>
		<li>Adjust quantities in the order list</li>
		<li>Click "Pack Order" to see optimal container placement</li>
	</ol>
</div>
</div>
<h3>Packing Result</h3>
<div id=\"compactResult\" style=\"display: none;\"></div>

<!-- Popup Modal -->
<div id=\"resultModal\" class=\"modal\" onclick=\"closeModal(event)\">
  <div class=\"modal-content\" onclick=\"event.stopPropagation()\">
    <div class=\"modal-header\">
      <h2>📦 Packing Details</h2>
      <span class=\"close\" onclick=\"closeModal()\">&times;</span>
    </div>
    <div class=\"modal-body\">
      <div id=\"summary\"></div>
      <div class=\"modal-tabs\">
        <button class=\"tab-button active\" onclick=\"showTab('3d')\">3D View</button>
        <button class=\"tab-button\" onclick=\"showTab('2d')\">2D Views</button>
        <button class=\"tab-button\" onclick=\"showTab('json')\">Raw Data</button>
      </div>
      <div id=\"tab-3d\" class=\"tab-content active\">
        <div id=\"viz3d\" style=\"width: 100%; height: 500px; border:1px solid #ccc\"></div>
      </div>
      <div id=\"tab-2d\" class=\"tab-content\">
        <div style=\"display: flex; gap: 10px; flex-wrap: wrap; justify-content: center;\">
          <div>
            <h4>Top View (XY)</h4>
            <canvas id=\"vizTop\" width=\"300\" height=\"300\" style=\"border:1px solid #ccc\"></canvas>
          </div>
          <div>
            <h4>Front View (XZ)</h4>
            <canvas id=\"vizFront\" width=\"300\" height=\"300\" style=\"border:1px solid #ccc\"></canvas>
          </div>
          <div>
            <h4>Side View (YZ)</h4>
            <canvas id=\"vizSide\" width=\"300\" height=\"300\" style=\"border:1px solid #ccc\"></canvas>
          </div>
        </div>
      </div>
      <div id=\"tab-json\" class=\"tab-content\">
        <pre id=\"log\" style=\"max-height: 400px; overflow-y: auto;\"></pre>
      </div>
    </div>
  </div>
</div>
<script>
const items = [];
const nameCache = {};
let allSkus = [];
async function addItem(){
  const sku = document.getElementById('sku').value.trim();
  const qty = parseInt(document.getElementById('qty').value,10)||1;
  if(!sku){ alert('Enter SKU'); return; }
  if(!nameCache[sku]){
    try{
      const res = await fetch('/skus?q=' + encodeURIComponent(sku));
      const arr = await res.json();
      if(arr && arr.length){
        const r = arr[0];
        nameCache[sku] = (r.brand||'') + ' ' + (r.model||'') + (r.variant?(' ' + r.variant):'');
      } else {
        nameCache[sku] = '';
      }
    }catch(e){ nameCache[sku] = ''; }
  }
  items.push({sku: sku, quantity: qty});
  updateItemList();
}
function updateItemList(){
  const el = document.getElementById('itemList');
  if(items.length === 0){ 
    el.innerHTML = '<div style="color: #666; text-align: center; padding: 10px;">No items added yet</div>'; 
    return; 
  }
  el.innerHTML = items.map((it,i) => {
    const name = nameCache[it.sku] || '';
    return `
      <div style="border-bottom: 1px solid #eee; padding: 8px 0; margin-bottom: 5px;">
        <div style="font-weight: bold; color: #1976d2; font-size: 12px;">${it.sku}</div>
        <div style="font-size: 10px; color: #666; margin: 2px 0; line-height: 1.3;">${name}</div>
        <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 5px;">
          <div>
            <button onclick="changeQuantity(${i}, -1)" style="background: #ffc107; color: #000; padding: 2px 6px; font-size: 11px; border: none; border-radius: 2px;">-</button>
            <span style="margin: 0 8px; font-weight: bold; font-size: 12px;">×${it.quantity}</span>
            <button onclick="changeQuantity(${i}, 1)" style="background: #28a745; color: white; padding: 2px 6px; font-size: 11px; border: none; border-radius: 2px;">+</button>
          </div>
          <button onclick="removeItem(${i})" style="background: #dc3545; color: white; padding: 2px 8px; font-size: 10px; border: none; border-radius: 2px;">✕</button>
        </div>
      </div>
    `;
  }).join('');
}
async function loadAllSkus(){
  try {
    const res = await fetch('/skus?limit=1000');
    if(!res.ok) throw new Error('HTTP ' + res.status);
    allSkus = await res.json();
    // Cache names
    allSkus.forEach(sku => {
      nameCache[sku.sku] = (sku.brand||'') + ' ' + (sku.model||'') + (sku.variant?(' ' + sku.variant):'');
    });
    renderSkuList(allSkus);
  } catch(e) {
    document.getElementById('skuList').innerHTML = '<div style="padding: 20px; color: red; text-align: center;">Error loading SKUs: ' + e.message + '</div>';
  }
}

function renderSkuList(skus){
  const el = document.getElementById('skuList');
  if(!skus || skus.length === 0) {
    el.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">No SKUs found</div>';
    return;
  }
  
  el.innerHTML = skus.slice(0, 100).map(sku => {
    const name = (sku.brand||'') + ' ' + (sku.model||'') + (sku.variant?(' ' + sku.variant):'');
    return `
      <div class="sku-item" onclick="addItemBySku('${sku.sku}')">
        <div class="sku-code">${sku.sku}</div>
        <div class="sku-name">${name}</div>
      </div>
    `;
  }).join('') + (skus.length > 100 ? '<div style="padding: 10px; text-align: center; color: #666; font-size: 11px;">Showing first 100 results. Use search to filter.</div>' : '');
}

function filterSkus(){
  const query = document.getElementById('skuSearch').value.toLowerCase().trim();
  if(!query) {
    renderSkuList(allSkus);
    return;
  }
  
  const filtered = allSkus.filter(sku => {
    const name = ((sku.brand||'') + ' ' + (sku.model||'') + ' ' + (sku.variant||'')).toLowerCase();
    return sku.sku.toLowerCase().includes(query) || name.includes(query);
  });
  
  renderSkuList(filtered);
}

async function addItemBySku(sku, quantity = 1){
  // Get product name if not cached
  if(!nameCache[sku]){
    try{
      const res = await fetch('/skus?q=' + encodeURIComponent(sku));
      const arr = await res.json();
      if(arr && arr.length){
        const r = arr[0];
        nameCache[sku] = (r.brand||'') + ' ' + (r.model||'') + (r.variant?(' ' + r.variant):'');
      } else {
        nameCache[sku] = '';
      }
    }catch(e){ nameCache[sku] = ''; }
  }
  
  // Check if item already exists
  const existing = items.find(item => item.sku === sku);
  if(existing) {
    existing.quantity += quantity;
  } else {
    items.push({sku, quantity});
  }
  updateItemList();
}

function changeQuantity(idx, delta){
  if(items[idx]){
    items[idx].quantity = Math.max(1, items[idx].quantity + delta);
    updateItemList();
  }
}

function removeItem(idx){ 
  items.splice(idx, 1); 
  updateItemList(); 
}

function clearOrder(){
  items.length = 0;
  updateItemList();
}
// Auto-load SKUs on page load
window.addEventListener('DOMContentLoaded', () => {
  updateItemList(); // Initialize empty order display
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
  if(e.key === 'Escape') {
    closeModal();
  }
});
async function submitOrder(){
  const orderId = document.getElementById('orderId').value.trim() || 'ORD-1';
  const body = { order_id: orderId, items: items };
  
  // Show loading state
  const compactEl = document.getElementById('compactResult');
  compactEl.style.display = 'block';
  compactEl.innerHTML = '<div style="text-align: center; color: #666;">🔄 Processing order...</div>';
  
  try {
    const res = await fetch('/pack/order', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    
    if (!res.ok) {
      const errorText = await res.text();
      console.error('Pack order failed:', errorText);
      throw new Error(`HTTP ${res.status}: ${errorText}`);
    }
    
    const j = await res.json();
    
    // Store result globally for modal
    window.packingResult = j;
    
    // Show compact result
    showCompactResult(j);
    
    // Prepare modal content (but don't show yet)
    renderSummary(j);
    document.getElementById('log').textContent = JSON.stringify(j, null, 2);
    
  } catch(error) {
    compactEl.innerHTML = '<div style="color: #dc3545;">❌ Error: ' + error.message + '</div>';
  }
}

function showCompactResult(j) {
  const el = document.getElementById('compactResult');
  if(!j || !j.success) {
    el.innerHTML = `
      <div class="compact-result" style="background: #f8d7da; border-color: #dc3545;">
        <div class="result-summary">
          <strong>❌ No suitable container found</strong><br>
          <small>Unable to pack items even with multiple containers</small>
        </div>
      </div>
    `;
    return;
  }
  
  const isMultiContainer = j.container_count > 1;
  const containerText = isMultiContainer ? 
    `${j.container_count} containers` : 
    `${j.container_name || 'Unknown'} (${j.shipping_company || 'Unknown'})`;
  
  el.innerHTML = `
    <div class="compact-result">
      <div class="result-summary">
        <strong>✅ Packed successfully!</strong>
        ${isMultiContainer ? '<span style="background: #ffc107; color: #000; padding: 2px 6px; border-radius: 3px; font-size: 10px; margin-left: 8px;">MULTI-BOX</span>' : ''}
        <br>
        <small>
          ${containerText} | 
          ${j.total_items || j.placements?.length || 0} items | 
          ${(j.utilization*100).toFixed(1)}% avg utilization | 
          ${j.total_price || j.price_try || 0}₺ total
        </small>
      </div>
      <div class="result-actions">
        <button onclick="openModal()" style="background: #007bff; padding: 8px 16px;">📊 View Details</button>
        <button onclick="openModal(); showTab('3d')" style="background: #28a745; padding: 8px 16px;">🎯 3D View</button>
      </div>
    </div>
  `;
}

function openModal() {
  document.getElementById('resultModal').style.display = 'block';
  // Render visualizations when modal opens
  if(window.packingResult) {
    render3D(window.packingResult);
    render2DViews(window.packingResult);
  }
}

function closeModal(event) {
  if(!event || event.target === document.getElementById('resultModal') || event.target.classList.contains('close')) {
    document.getElementById('resultModal').style.display = 'none';
  }
}

function showTab(tabName) {
  // Hide all tabs
  document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
  document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
  
  // Show selected tab
  document.getElementById('tab-' + tabName).classList.add('active');
  document.querySelector(`[onclick="showTab('${tabName}')"]`).classList.add('active');
  
  // Re-render 3D if switching to 3D tab (for proper sizing)
  if(tabName === '3d' && window.packingResult) {
    setTimeout(() => render3D(window.packingResult), 100);
  }
}

function renderSummary(j){
  const el = document.getElementById('summary');
  if(!j || !j.success){ 
    el.innerHTML = '<div style="padding: 20px; text-align: center; color: #dc3545;">❌ No feasible container found.</div>'; 
    return; 
  }
  
  const isMultiContainer = j.container_count > 1;
  
  if(isMultiContainer) {
    // Multi-container summary
    el.innerHTML = `
      <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <h4 style="margin: 0 0 10px 0; color: #333;">📦 Multi-Container Packing Results</h4>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-bottom: 15px;">
          <div><strong>Total Containers:</strong> ${j.container_count}</div>
          <div><strong>Total Items:</strong> ${j.total_items}</div>
          <div><strong>Total Price:</strong> ${j.total_price.toFixed(2)}₺</div>
          <div><strong>Avg Utilization:</strong> ${(j.utilization*100).toFixed(1)}%</div>
          <div><strong>Total Volume:</strong> ${(j.container_volume_cm3/1000).toFixed(1)}L</div>
          <div><strong>Algorithm:</strong> <span style="color: #e67e22;">Multi-Container Greedy</span></div>
        </div>
        
        <h5 style="margin: 15px 0 10px 0; color: #333;">Container Breakdown:</h5>
        <div style="max-height: 300px; overflow-y: auto;">
          ${j.containers.map((container, idx) => `
            <div style="background: white; border: 1px solid #ddd; border-radius: 6px; padding: 12px; margin-bottom: 8px;">
              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; font-size: 12px;">
                <div><strong>Container ${idx+1}:</strong> ${container.container_name || 'Unknown'}</div>
                <div><strong>Company:</strong> ${container.shipping_company || 'Unknown'}</div>
                <div><strong>Items:</strong> ${container.placements.length}</div>
                <div><strong>Utilization:</strong> ${(container.utilization*100).toFixed(1)}%</div>
                <div><strong>Price:</strong> ${container.price_try || 0}₺</div>
                <div><strong>Volume:</strong> ${(container.container_volume_cm3/1000).toFixed(1)}L</div>
              </div>
            </div>
          `).join('')}
        </div>
        
        <div style="margin-top: 10px; padding: 10px; background: #fff3cd; border-radius: 4px; font-size: 12px;">
          ⚠️ <strong>Multi-Container Note:</strong> Order was split across multiple containers to minimize total cost. 
          Each container uses optimal shelf packing algorithm.
        </div>
      </div>
    `;
  } else {
    // Single container summary (legacy format)
    let maxW=0, maxL=0, maxH=0;
    if(j.placements && j.placements.length > 0) {
      j.placements.forEach(p=>{ 
        maxW=Math.max(maxW, p.position_mm[0]+p.size_mm[0]); 
        maxL=Math.max(maxL, p.position_mm[1]+p.size_mm[1]); 
        maxH=Math.max(maxH, p.position_mm[2]+p.size_mm[2]); 
      });
    }
    
    el.innerHTML = `
      <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <h4 style="margin: 0 0 10px 0; color: #333;">📦 Single Container Packing</h4>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
          <div><strong>Container:</strong> ${j.container_name || 'Unknown'}</div>
          <div><strong>Company:</strong> ${j.shipping_company || 'Unknown'}</div>
          <div><strong>Material:</strong> ${j.container_material || 'Unknown'}</div>
          <div><strong>ID:</strong> ${j.used_container_id || j.box_id}</div>
          <div><strong>Dimensions:</strong> ${maxW}×${maxL}×${maxH}mm</div>
          <div><strong>Items Count:</strong> ${j.placements ? j.placements.length : 0}</div>
          <div><strong>Price:</strong> ${j.price_try || 0}₺</div>
          <div><strong>Utilization:</strong> ${(j.utilization*100).toFixed(1)}%</div>
          <div><strong>Volume:</strong> ${(j.container_volume_cm3/1000).toFixed(1)}L total</div>
          <div><strong>Remaining:</strong> ${(j.remaining_volume_cm3/1000).toFixed(1)}L free</div>
          <div><strong>Algorithm:</strong> <span style="color: #28a745;">Single Container Optimal</span></div>
        </div>
        
        <div style="margin-top: 10px; padding: 10px; background: #e8f5e8; border-radius: 4px; font-size: 12px;">
          ✅ <strong>Optimal Solution:</strong> All items fit in single <strong>${j.container_name || 'Unknown'}</strong> container 
          from <strong>${j.shipping_company || 'Unknown'}</strong>. Most cost-effective option selected.
        </div>
      </div>
    `;
  }
}

function renderViz(j){
  const cvs = document.getElementById('viz');
  const ctx = cvs.getContext('2d');
  ctx.clearRect(0,0,cvs.width,cvs.height);
  if(!j || !j.box_id || !Array.isArray(j.placements)) return;
  // Draw top-down (X=width, Y=length) per layer Z
  const W = j.container_volume_cm3 && j.placements.length ? j.placements.reduce((acc,p)=>Math.max(acc,p.size_mm[0]),0) : 0;
  // Use container dims if available via placements approximation
  let maxW=0, maxL=0, maxZ=0;
  j.placements.forEach(p=>{ maxW=Math.max(maxW, p.position_mm[0]+p.size_mm[0]); maxL=Math.max(maxL, p.position_mm[1]+p.size_mm[1]); maxZ=Math.max(maxZ, p.position_mm[2]+p.size_mm[2]); });
  const scale = Math.min(cvs.width/(maxW||1), cvs.height/(maxL||1));
  // Group by layer using p.position_mm[2]
  const layers = {};
  j.placements.forEach(p=>{
    const z = p.position_mm[2];
    const key = Math.round(z/10)*10; // bin by 10mm
    if(!layers[key]) layers[key]=[];
    layers[key].push(p);
  });
  const keys = Object.keys(layers).map(k=>parseFloat(k)).sort((a,b)=>a-b);
  const margin = 10;
  const panelW = (cvs.width - margin*(keys.length+1)) / Math.max(1, keys.length);
  keys.forEach((k, idx)=>{
    const ox = margin + idx*(panelW+margin);
    const oy = margin;
    // Frame
    ctx.strokeStyle = '#888';
    ctx.strokeRect(ox, oy, panelW, panelW*(maxL/(maxW||1)));
    // Draw items
    layers[k].forEach((p,i)=>{
      const x = p.position_mm[0]*scale;
      const y = p.position_mm[1]*scale;
      const w = p.size_mm[0]*scale;
      const l = p.size_mm[1]*scale;
      ctx.fillStyle = `hsl(${(i*57)%360} 70% 60%)`;
      ctx.fillRect(ox+x, oy+y, w, l);
      ctx.strokeStyle = '#333';
      ctx.strokeRect(ox+x, oy+y, w, l);
    });
    ctx.fillStyle = '#000';
    ctx.fillText('Z~'+k+'mm', ox, oy+10);
  });
}

function render2DViews(j){
  if(!j || !j.box_id || !Array.isArray(j.placements)) {
    ['vizTop', 'vizFront', 'vizSide'].forEach(id => {
      const canvas = document.getElementById(id);
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0,0,canvas.width, canvas.height);
      ctx.fillStyle = '#f0f0f0';
      ctx.fillRect(0,0,canvas.width, canvas.height);
      ctx.fillStyle = '#666';
      ctx.font = '14px Arial';
      ctx.textAlign = 'center';
      ctx.fillText('No data', canvas.width/2, canvas.height/2);
    });
    return;
  }
  
  // Calculate bounds
  let maxW=0, maxL=0, maxH=0;
  j.placements.forEach(p=>{ 
    maxW=Math.max(maxW, p.position_mm[0]+p.size_mm[0]); 
    maxL=Math.max(maxL, p.position_mm[1]+p.size_mm[1]); 
    maxH=Math.max(maxH, p.position_mm[2]+p.size_mm[2]); 
  });
  
  const colorForSku = (sku)=>{ 
    let h=0; 
    for(let i=0;i<sku.length;i++){ 
      h=(h*31 + sku.charCodeAt(i))>>>0; 
    } 
    return `hsl(${h%360},70%,55%)`; 
  };
  
  // Top View (XY plane)
  const renderTopView = () => {
    const canvas = document.getElementById('vizTop');
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0,0,canvas.width, canvas.height);
    ctx.fillStyle = '#f8f8f8';
    ctx.fillRect(0,0,canvas.width, canvas.height);
    
    const margin = 20;
    const scaleX = (canvas.width-2*margin)/maxW;
    const scaleY = (canvas.height-2*margin)/maxL;
    const scale = Math.min(scaleX, scaleY);
    
    // Container outline
    ctx.strokeStyle = '#999';
    ctx.lineWidth = 2;
    ctx.strokeRect(margin, margin, maxW*scale, maxL*scale);
    
    j.placements.forEach(p=>{
      ctx.fillStyle = colorForSku(p.sku);
      const x = margin + p.position_mm[0] * scale;
      const y = margin + p.position_mm[1] * scale;
      const w = p.size_mm[0] * scale;
      const h = p.size_mm[1] * scale;
      ctx.fillRect(x, y, w, h);
      ctx.strokeStyle = '#000';
      ctx.lineWidth = 1;
      ctx.strokeRect(x, y, w, h);
      
      // SKU label
      if(w > 30 && h > 15) {
        ctx.fillStyle = '#000';
        ctx.font = '8px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(p.sku, x + w/2, y + h/2 + 3);
      }
    });
    
    ctx.fillStyle = '#333';
    ctx.font = '12px Arial';
    ctx.textAlign = 'left';
    ctx.fillText(`${maxW}×${maxL}mm`, margin, canvas.height - 5);
  };
  
  // Front View (XZ plane)
  const renderFrontView = () => {
    const canvas = document.getElementById('vizFront');
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0,0,canvas.width, canvas.height);
    ctx.fillStyle = '#f8f8f8';
    ctx.fillRect(0,0,canvas.width, canvas.height);
    
    const margin = 20;
    const scaleX = (canvas.width-2*margin)/maxW;
    const scaleZ = (canvas.height-2*margin)/maxH;
    const scale = Math.min(scaleX, scaleZ);
    
    // Container outline
    ctx.strokeStyle = '#999';
    ctx.lineWidth = 2;
    ctx.strokeRect(margin, margin, maxW*scale, maxH*scale);
    
    j.placements.forEach(p=>{
      ctx.fillStyle = colorForSku(p.sku);
      const x = margin + p.position_mm[0] * scale;
      const z = margin + p.position_mm[2] * scale;
      const w = p.size_mm[0] * scale;
      const h = p.size_mm[2] * scale;
      ctx.fillRect(x, z, w, h);
      ctx.strokeStyle = '#000';
      ctx.lineWidth = 1;
      ctx.strokeRect(x, z, w, h);
      
      // SKU label
      if(w > 30 && h > 15) {
        ctx.fillStyle = '#000';
        ctx.font = '8px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(p.sku, x + w/2, z + h/2 + 3);
      }
    });
    
    ctx.fillStyle = '#333';
    ctx.font = '12px Arial';
    ctx.textAlign = 'left';
    ctx.fillText(`${maxW}×${maxH}mm`, margin, canvas.height - 5);
  };
  
  // Side View (YZ plane)
  const renderSideView = () => {
    const canvas = document.getElementById('vizSide');
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0,0,canvas.width, canvas.height);
    ctx.fillStyle = '#f8f8f8';
    ctx.fillRect(0,0,canvas.width, canvas.height);
    
    const margin = 20;
    const scaleY = (canvas.width-2*margin)/maxL;
    const scaleZ = (canvas.height-2*margin)/maxH;
    const scale = Math.min(scaleY, scaleZ);
    
    // Container outline
    ctx.strokeStyle = '#999';
    ctx.lineWidth = 2;
    ctx.strokeRect(margin, margin, maxL*scale, maxH*scale);
    
    j.placements.forEach(p=>{
      ctx.fillStyle = colorForSku(p.sku);
      const y = margin + p.position_mm[1] * scale;
      const z = margin + p.position_mm[2] * scale;
      const l = p.size_mm[1] * scale;
      const h = p.size_mm[2] * scale;
      ctx.fillRect(y, z, l, h);
      ctx.strokeStyle = '#000';
      ctx.lineWidth = 1;
      ctx.strokeRect(y, z, l, h);
      
      // SKU label
      if(l > 30 && h > 15) {
        ctx.fillStyle = '#000';
        ctx.font = '8px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(p.sku, y + l/2, z + h/2 + 3);
      }
    });
    
    ctx.fillStyle = '#333';
    ctx.font = '12px Arial';
    ctx.textAlign = 'left';
    ctx.fillText(`${maxL}×${maxH}mm`, margin, canvas.height - 5);
  };
  
  renderTopView();
  renderFrontView();
  renderSideView();
}

function render3D(j){
  const el = document.getElementById('viz3d');
  el.innerHTML = '';
  
  if(!j || !j.box_id || !Array.isArray(j.placements) || j.placements.length === 0) {
    el.innerHTML = '<p>No placements to visualize</p>';
    return;
  }
  
  console.log('Starting 3D render with data:', j);
  
  // Interactive 3D visualization with mouse controls
  try {
    const canvas = document.createElement('canvas');
    canvas.width = 800;
    canvas.height = 500;
    canvas.style.border = '1px solid #ccc';
    canvas.style.cursor = 'move';
    el.appendChild(canvas);
    
    const ctx = canvas.getContext('2d');
    
    // Calculate container bounds
    let maxW=0, maxL=0, maxH=0;
    j.placements.forEach(p=>{ 
      maxW=Math.max(maxW, p.position_mm[0]+p.size_mm[0]); 
      maxL=Math.max(maxL, p.position_mm[1]+p.size_mm[1]); 
      maxH=Math.max(maxH, p.position_mm[2]+p.size_mm[2]); 
    });
    
    // 3D view state
    let rotationX = 0.5;
    let rotationY = 0.8;
    let scale = Math.min(300/Math.max(maxW, maxL), 200/maxH) * 0.6;
    let offsetX = canvas.width/2;
    let offsetY = canvas.height/2;
    let isDragging = false;
    let lastMouseX = 0;
    let lastMouseY = 0;
    
    // 3D projection with rotation
    const project3D = (x, y, z) => {
      // Center coordinates
      const cx = x - maxW/2;
      const cy = y - maxL/2;
      const cz = z - maxH/2;
      
      // Apply rotations
      const cosX = Math.cos(rotationX), sinX = Math.sin(rotationX);
      const cosY = Math.cos(rotationY), sinY = Math.sin(rotationY);
      
      // Rotate around X axis
      const y1 = cy * cosX - cz * sinX;
      const z1 = cy * sinX + cz * cosX;
      
      // Rotate around Y axis
      const x2 = cx * cosY + z1 * sinY;
      const z2 = -cx * sinY + z1 * cosY;
      
      // Project to 2D
      const px = x2 * scale + offsetX;
      const py = -y1 * scale + offsetY;
      
      return [px, py, z2];
    };
    
    // Color per SKU
    const colorForSku = (sku) => {
      let h = 0;
      for(let i = 0; i < sku.length; i++){
        h = (h * 31 + sku.charCodeAt(i)) >>> 0;
      }
      return `hsl(${h % 360}, 70%, 55%)`;
    };
    
    // Render function
    const render = () => {
      ctx.fillStyle = '#f0f0f0';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      // Draw title and controls
      ctx.fillStyle = '#333';
      ctx.font = '16px Arial';
      ctx.fillText('3D Visualization - Drag to rotate, Wheel to zoom', 10, 25);
      
      // Collect all faces for z-sorting
      const faces = [];
      
      // Container faces
      const containerCorners = [
        [0,0,0], [maxW,0,0], [maxW,maxL,0], [0,maxL,0],
        [0,0,maxH], [maxW,0,maxH], [maxW,maxL,maxH], [0,maxL,maxH]
      ];
      
      const containerFaces = [
        [0,1,2,3], [4,7,6,5], [0,4,5,1], [2,6,7,3], [0,3,7,4], [1,5,6,2]
      ];
      
      containerFaces.forEach((face, idx) => {
        const corners3d = face.map(i => project3D(...containerCorners[i]));
        const avgZ = corners3d.reduce((sum, p) => sum + p[2], 0) / 4;
        faces.push({
          type: 'container',
          corners: corners3d,
          z: avgZ,
          color: 'rgba(200,200,200,0.1)',
          stroke: '#999'
        });
      });
      
      // Item faces
      j.placements.forEach((p, idx) => {
        const color = colorForSku(p.sku);
        const x = p.position_mm[0];
        const y = p.position_mm[1];
        const z = p.position_mm[2];
        const w = p.size_mm[0];
        const l = p.size_mm[1];
        const h = p.size_mm[2];
        
        const itemCorners = [
          [x,y,z], [x+w,y,z], [x+w,y+l,z], [x,y+l,z],
          [x,y,z+h], [x+w,y,z+h], [x+w,y+l,z+h], [x,y+l,z+h]
        ];
        
        const itemFaces = [
          [0,1,2,3], [4,7,6,5], [0,4,5,1], [2,6,7,3], [0,3,7,4], [1,5,6,2]
        ];
        
        itemFaces.forEach((face, faceIdx) => {
          const corners3d = face.map(i => project3D(...itemCorners[i]));
          const avgZ = corners3d.reduce((sum, p) => sum + p[2], 0) / 4;
          
          // Different opacity for different faces
          const opacity = faceIdx === 1 ? 1.0 : (faceIdx < 2 ? 0.8 : 0.6);
          const faceColor = color.replace('55%', `${Math.round(55 * opacity)}%`);
          
          faces.push({
            type: 'item',
            corners: corners3d,
            z: avgZ,
            color: faceColor,
            stroke: '#000',
            sku: p.sku,
            faceIdx: faceIdx
          });
        });
      });
      
      // Sort faces by z-depth (back to front)
      faces.sort((a, b) => a.z - b.z);
      
      // Draw all faces
      faces.forEach(face => {
        ctx.beginPath();
        ctx.moveTo(face.corners[0][0], face.corners[0][1]);
        for(let i = 1; i < face.corners.length; i++){
          ctx.lineTo(face.corners[i][0], face.corners[i][1]);
        }
        ctx.closePath();
        
        if(face.type === 'container'){
          ctx.strokeStyle = face.stroke;
          ctx.lineWidth = 2;
          ctx.stroke();
        } else {
          ctx.fillStyle = face.color;
          ctx.fill();
          ctx.strokeStyle = face.stroke;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      });
      
      // Draw SKU labels
      j.placements.forEach((p, idx) => {
        const x = p.position_mm[0] + p.size_mm[0]/2;
        const y = p.position_mm[1] + p.size_mm[1]/2;
        const z = p.position_mm[2] + p.size_mm[2] + 10;
        const [lx, ly, lz] = project3D(x, y, z);
        
        if(lz > 0) { // Only draw if in front
          ctx.fillStyle = '#000';
          ctx.font = '10px Arial';
          ctx.textAlign = 'center';
          ctx.fillText(p.sku, lx, ly);
        }
      });
      
    // Add legend
    ctx.textAlign = 'left';
    ctx.font = '12px Arial';
    ctx.fillStyle = '#333';
    ctx.fillText(`${j.shipping_company || 'Unknown'} - ${j.container_name || 'Unknown'} | ${maxW}×${maxL}×${maxH}mm`, 10, canvas.height - 45);
    ctx.fillText(`Items: ${j.placements.length} | Utilization: ${(j.utilization*100).toFixed(1)}% | Price: ${j.price_try || 0}₺`, 10, canvas.height - 30);
    ctx.fillText(`Volume: ${(j.container_volume_cm3/1000).toFixed(1)}L | Remaining: ${(j.remaining_volume_cm3/1000).toFixed(1)}L`, 10, canvas.height - 15);
    };
    
    // Mouse controls
    canvas.addEventListener('mousedown', (e) => {
      isDragging = true;
      lastMouseX = e.clientX;
      lastMouseY = e.clientY;
    });
    
    canvas.addEventListener('mousemove', (e) => {
      if(isDragging){
        const deltaX = e.clientX - lastMouseX;
        const deltaY = e.clientY - lastMouseY;
        
        rotationY += deltaX * 0.01;
        rotationX += deltaY * 0.01;
        
        // Clamp rotation
        rotationX = Math.max(-Math.PI/2, Math.min(Math.PI/2, rotationX));
        
        lastMouseX = e.clientX;
        lastMouseY = e.clientY;
        
        render();
      }
    });
    
    canvas.addEventListener('mouseup', () => {
      isDragging = false;
    });
    
    canvas.addEventListener('mouseleave', () => {
      isDragging = false;
    });
    
    // Zoom with mouse wheel
    canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
      scale *= zoomFactor;
      scale = Math.max(0.1, Math.min(5.0, scale));
      render();
    });
    
    // Initial render
    render();
    
    console.log('Interactive 3D visualization rendered successfully');
    
  } catch (error) {
    console.error('3D render error:', error);
    el.innerHTML = '<p>Error rendering 3D: ' + error.message + '</p>';
  }
}
</script>
</body>
</html>
"""


@app.get("/health")
def health():
	return {"status": "ok"}


@app.post("/pack", response_model=PackResponse)
def pack_endpoint(req: PackRequest) -> PackResponse:
	products = [Product(**p.model_dump()) for p in req.products]
	containers = [Container(**c.model_dump()) for c in req.containers]
	best = None
	best_price = None
	for c in containers:
		res = pack(products, c)
		if res is None:
			continue
		price = c.price_try or 0.0
		if best is None or price < best_price:
			best = (c, res)
			best_price = price
	if best is None:
		return PackResponse(order_id=req.order_id, box_id=None, placements=[], utilization=0.0, price_try=None)
	c, res = best
	placements: List[Placement] = [Placement(sku=it.sku, position_mm=it.position_mm, size_mm=it.size_mm, rotation=it.rotation) for it in res.placements]
	total_item_volume = sum(it.size_mm[0]*it.size_mm[1]*it.size_mm[2] for it in res.placements) / 1000.0
	container_volume = c.inner_w_mm*c.inner_l_mm*c.inner_h_mm / 1000.0
	util = round(min(1.0, total_item_volume / container_volume), 4) if container_volume > 0 else 0.0
	return PackResponse(order_id=req.order_id, box_id=c.box_id, placements=placements, utilization=util, price_try=c.price_try)


@app.post("/pack/order", response_model=OrderPackResponse)
def pack_order_endpoint(req: OrderPackRequest) -> OrderPackResponse:
	# Load master data
	all_products = load_products_csv("data/products.csv")
	product_by_sku = {p.sku: p for p in all_products}
	containers = load_containers_csv("data/container.csv")
	
	# Expand order items into individual product instances
	products: List[Product] = []
	for item in req.items:
		if item.sku not in product_by_sku:
			raise HTTPException(status_code=400, detail=f"Unknown SKU: {item.sku}")
		for _ in range(int(item.quantity)):
			products.append(product_by_sku[item.sku])
	
	# Try optimal multi-container packing
	packing_result = find_optimal_multi_packing(products, containers)
	
	if not packing_result:
		# For very large orders, try partial packing as fallback
		total_volume = sum(p.width_mm * p.length_mm * p.height_mm for p in products) / 1000.0  # cm³
		largest_container = max(containers, key=lambda c: c.inner_w_mm * c.inner_l_mm * c.inner_h_mm) if containers else None
		available_volume = largest_container.inner_w_mm * largest_container.inner_l_mm * largest_container.inner_h_mm / 1000.0 if largest_container else 0
		
		# If order is larger than single container or has many items, try aggressive partial packing
		if total_volume > available_volume or len(products) > 20:
			partial_result = try_aggressive_partial_packing(products, containers)
			if partial_result:
				packing_result = partial_result
			else:
				# Provide helpful error information
				largest_item_dims = max(products, key=lambda p: max(p.width_mm, p.length_mm, p.height_mm))
				error_msg = f"Unable to pack {len(products)} items (total volume: {total_volume:.1f}cm³). "
				if largest_container:
					error_msg += f"Largest available container: {largest_container.box_id} ({available_volume:.1f}cm³ capacity). "
				
				if total_volume > available_volume * 3:  # Very large order
					error_msg += f"This order is exceptionally large ({total_volume/available_volume:.1f}x largest container). Consider splitting into smaller orders. "
				
				error_msg += f"Largest item: {largest_item_dims.sku} ({largest_item_dims.width_mm}x{largest_item_dims.length_mm}x{largest_item_dims.height_mm}mm)"
				
				raise HTTPException(status_code=400, detail=error_msg)
		else:
			# Regular error for normal sized orders
			largest_item_dims = max(products, key=lambda p: max(p.width_mm, p.length_mm, p.height_mm))
			error_msg = f"Unable to pack {len(products)} items (total volume: {total_volume:.1f}cm³). "
			error_msg += f"Largest item: {largest_item_dims.sku} ({largest_item_dims.width_mm}x{largest_item_dims.length_mm}x{largest_item_dims.height_mm}mm)"
			raise HTTPException(status_code=400, detail=error_msg)
	
	# Build response with container results
	container_results = []
	total_price = 0.0
	total_items = 0
	all_placements = []  # For legacy compatibility
	packed_skus = set()  # Track which SKUs were packed
	
	for container, packed_result in packing_result:
		placements = [Placement(sku=it.sku, position_mm=it.position_mm, size_mm=it.size_mm, rotation=it.rotation) for it in packed_result.placements]
		
		# Track packed SKUs
		for placement in placements:
			packed_skus.add(placement.sku)
		
		total_item_volume_cm3 = sum(it.size_mm[0]*it.size_mm[1]*it.size_mm[2] for it in packed_result.placements) / 1000.0
		container_volume_cm3 = (container.inner_w_mm*container.inner_l_mm*container.inner_h_mm) / 1000.0
		util = round(min(1.0, total_item_volume_cm3 / container_volume_cm3), 4) if container_volume_cm3 > 0 else 0.0
		remaining = max(0.0, container_volume_cm3 - total_item_volume_cm3)
		
		container_result = ContainerResult(
			container_id=container.box_id,
			container_name=container.box_name,
			shipping_company=container.shipping_company,
			container_material=container.material,
			container_type=container.container_type,
			placements=placements,
			utilization=util,
			remaining_volume_cm3=remaining,
			container_volume_cm3=container_volume_cm3,
			price_try=container.price_try
		)
		
		container_results.append(container_result)
		total_price += container.price_try or 0.0
		total_items += len(placements)
		all_placements.extend(placements)
	
	# Check if this is partial packing
	original_item_count = sum(item.quantity for item in req.items)
	is_partial = total_items < original_item_count
	
	# For single container, provide legacy compatibility
	first_container = packing_result[0][0]
	first_result = container_results[0] if container_results else None
	
	return OrderPackResponse(
		order_id=req.order_id,
		success=True,
		containers=container_results,
		total_price=total_price,
		total_items=total_items,
		container_count=len(container_results),
		# Legacy fields for backward compatibility (use first container)
		box_id=first_container.box_id if len(packing_result) == 1 else f"MULTI-{len(packing_result)}",
		placements=all_placements,
		utilization=sum(cr.utilization for cr in container_results) / len(container_results) if container_results else 0.0,
		remaining_volume_cm3=sum(cr.remaining_volume_cm3 for cr in container_results),
		container_volume_cm3=sum(cr.container_volume_cm3 for cr in container_results),
		price_try=total_price,
		used_container_id=first_container.box_id if len(packing_result) == 1 else f"MULTI-{len(packing_result)}",
		container_name=first_container.box_name if len(packing_result) == 1 else f"{len(packing_result)} Containers",
		shipping_company=first_container.shipping_company if len(packing_result) == 1 else "Multiple",
		container_material=first_container.material if len(packing_result) == 1 else "Multiple"
	) 


@app.get("/skus")
def list_skus(q: str | None = None, limit: int = 20):
    # CSV-only reader; güvenli JSON için NaN/None → '' coerces
    import csv, hashlib
    path = "data/products.csv"
    encodings = ("utf-8-sig", "utf-8", "cp1254")
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc, errors="ignore") as f:
                head = f.read(4096)
                f.seek(0)
                try:
                    delim = csv.Sniffer().sniff(head).delimiter
                except Exception:
                    delim = ';'
                reader = csv.DictReader(f, delimiter=delim)
                out = []
                for r in reader:
                    brand = (r.get('brand') or '').strip()
                    model = (r.get('model') or '').strip()
                    variant = (r.get('variant') or '').strip()
                    sku = (r.get('sku') or '').strip()
                    if not sku:
                        key = (brand+'|'+model+'|'+variant).encode('utf-8', errors='ignore')
                        h = hashlib.sha1(key).hexdigest()[:6].upper()
                        prefix = brand.upper().replace(' ', '-')[:4]
                        sku = (prefix+'-'+h) if prefix else h
                    row = {
                        'sku': sku,
                        'brand': brand,
                        'model': model,
                        'variant': variant
                    }
                    out.append(row)
                if q:
                    qL = str(q).lower()
                    out = [r for r in out
                           if (qL in r['sku'].lower()
                               or qL in r['brand'].lower()
                               or qL in r['model'].lower()
                               or qL in r['variant'].lower())]
                # JSON-safe: her şey string, NaN yok
                return out[:max(1, min(int(limit), 100))]
        except Exception:
            continue
    return []
