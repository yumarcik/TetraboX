from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from typing import List, Optional, Tuple, Dict
from .schemas import PackRequest, PackResponse, Placement, OrderPackRequest, OrderPackResponse, ContainerResult, CreateOrderRequest, UpdateOrderRequest, OrderResponse, OrderListResponse, APIOrderItem
from .models import Product, Container, Order, OrderItem, PackedContainer
from .io import load_products_csv, load_containers_csv, load_orders_csv, save_order_to_csv
from .packer import pack, find_optimal_multi_packing, pack_greedy_max_utilization, pack_best_fit, pack_largest_first_optimized
from .ml_strategy_selector import strategy_predictor
from datetime import datetime
import uuid


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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

* {
  box-sizing: border-box;
}

body { 
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
  margin: 0; 
  display: flex; 
  height: 100vh; 
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;
}

body::before {
  content: '';
  position: absolute;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px);
  background-size: 50px 50px;
  animation: moveBackground 20s linear infinite;
  z-index: 0;
}

@keyframes moveBackground {
  0% { transform: translate(0, 0); }
  100% { transform: translate(50px, 50px); }
}

.sidebar {
  width: 400px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%);
  backdrop-filter: blur(20px);
  border-right: 2px solid rgba(102, 126, 234, 0.1);
  padding: 0;
  box-shadow: 4px 0 32px rgba(0,0,0,0.12);
  overflow-y: auto;
  position: fixed;
  height: 100vh;
  left: 0;
  top: 0;
  z-index: 10;
}

.sidebar-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 30px 25px;
  position: sticky;
  top: 0;
  z-index: 20;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3);
}

.sidebar-content {
  padding: 25px;
}

.sidebar h3 {
  font-size: 26px;
  font-weight: 800;
  color: white;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  letter-spacing: -0.5px;
}

.sidebar-subtitle {
  font-size: 13px;
  color: rgba(255,255,255,0.9);
  font-weight: 500;
  margin-top: 6px;
  letter-spacing: 0.3px;
}

.sidebar h4 {
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
  margin: 0 0 12px 0;
  display: flex;
  align-items: center;
  gap: 8px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.main-content {
  margin-left: 400px;
  padding: 30px;
  width: calc(100% - 400px);
  overflow-y: auto;
  z-index: 1;
}
.sku-panel {
  background: white;
  border: 2px solid rgba(102, 126, 234, 0.1);
  border-radius: 16px;
  padding: 0;
  margin-bottom: 20px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  overflow: hidden;
  transition: all 0.3s ease;
}

.sku-panel:hover {
  box-shadow: 0 8px 30px rgba(102, 126, 234, 0.12);
  transform: translateY(-2px);
}

.sku-list {
  max-height: 420px;
  overflow-y: auto;
  border: none;
  border-radius: 0;
  background: transparent;
}

.sku-list::-webkit-scrollbar {
  width: 10px;
}

.sku-list::-webkit-scrollbar-track {
  background: rgba(241, 245, 249, 0.5);
  border-radius: 5px;
  margin: 4px;
}

.sku-list::-webkit-scrollbar-thumb {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 5px;
  border: 2px solid rgba(255,255,255,0.5);
}

.sku-list::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(135deg, #5568d3 0%, #653a8b 100%);
}

.sku-item {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.5);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  background: white;
}

.sku-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 4px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  transform: scaleY(0);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.sku-item:hover {
  background: linear-gradient(90deg, rgba(102, 126, 234, 0.06) 0%, rgba(255,255,255,0) 100%);
  transform: translateX(4px);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.1);
}

.sku-item:hover::before {
  transform: scaleY(1);
}

.sku-item:last-child {
  border-bottom: none;
}

.sku-code {
  font-weight: 700;
  color: #667eea;
  font-size: 14px;
  letter-spacing: -0.03em;
}

.sku-name {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
  line-height: 1.5;
  font-weight: 500;
}

input, button { 
  padding: 12px 16px; 
  margin: 4px;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  font-family: 'Inter', sans-serif;
  font-size: 14px;
  transition: all 0.3s ease;
}

input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

button { 
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
  color: white; 
  border: none; 
  cursor: pointer; 
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

button:hover { 
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

button:active {
  transform: translateY(0);
}

.search-box {
  width: calc(100% - 8px);
  margin-bottom: 15px;
  padding: 14px 16px;
  font-size: 14px;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  background: white;
  transition: all 0.3s ease;
}

.search-box:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  outline: none;
}

.order-list {
  background: white; 
  border: 1px solid #e2e8f0; 
  border-radius: 12px; 
  padding: 15px; 
  max-height: 250px; 
  overflow-y: auto;
  font-size: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.order-list::-webkit-scrollbar {
  width: 6px;
}

.order-list::-webkit-scrollbar-track {
  background: #f1f5f9;
}

.order-list::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

#log {
  white-space: pre; 
  background: #1e293b; 
  color: #e2e8f0;
  padding: 20px; 
  border: 1px solid #334155;
  border-radius: 12px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

h1, h2 {
  color: white;
  margin-top: 0;
  font-weight: 700;
  text-shadow: 0 2px 10px rgba(0,0,0,0.2);
}

h3, h4 {
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
  background-color: rgba(0,0,0,0.7);
  backdrop-filter: blur(4px);
  animation: fadeIn 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.modal-content {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  margin: 2% auto;
  border-radius: 20px;
  width: 95%;
  max-width: 1400px;
  max-height: 92vh;
  overflow-y: auto;
  animation: slideIn 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 20px 60px rgba(0,0,0,0.4);
  border: 1px solid rgba(255,255,255,0.3);
}

.modal-content::-webkit-scrollbar {
  width: 10px;
}

.modal-content::-webkit-scrollbar-track {
  background: #f1f5f9;
}

.modal-content::-webkit-scrollbar-thumb {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 5px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 25px 30px;
  border-bottom: 1px solid #e2e8f0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 20px 20px 0 0;
}

.modal-header h2 {
  margin: 0;
  color: white;
  font-weight: 700;
  font-size: 24px;
  text-shadow: 0 2px 10px rgba(0,0,0,0.2);
}

.close {
  font-size: 32px;
  font-weight: 300;
  cursor: pointer;
  color: rgba(255,255,255,0.8);
  transition: all 0.3s ease;
  line-height: 1;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
}

.close:hover {
  color: white;
  background: rgba(255,255,255,0.2);
  transform: rotate(90deg);
}

.modal-body {
  padding: 30px;
}

.modal-tabs {
  display: flex;
  gap: 10px;
  margin: 25px 0;
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 0;
}

.tab-button {
  padding: 12px 24px;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: 10px 10px 0 0;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  font-weight: 600;
  font-size: 14px;
  color: #64748b;
  position: relative;
}

.tab-button::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  transform: scaleX(0);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.tab-button.active {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  color: #5a67d8;
}

.tab-button.active::after {
  transform: scaleX(1);
}

.tab-button:hover:not(.active) {
  background: rgba(102, 126, 234, 0.05);
  color: #5a67d8;
}

.tab-content {
  display: none;
  padding: 20px 0;
}

.tab-content.active {
  display: block;
}

.compact-result {
  background: white;
  border: 2px solid #10b981;
  border-radius: 16px;
  padding: 20px 24px;
  margin: 20px 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.15);
  transition: all 0.3s ease;
}

.compact-result:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(16, 185, 129, 0.2);
}

.result-summary {
  flex: 1;
}

.result-summary strong {
  color: #059669;
  font-size: 16px;
  font-weight: 700;
}

.result-summary small {
  color: #64748b;
  font-size: 13px;
}

.result-actions {
  display: flex;
  gap: 12px;
}

.result-actions button {
  padding: 10px 20px;
  font-size: 14px;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideIn {
  from { 
    transform: translateY(-30px) scale(0.95); 
    opacity: 0; 
  }
  to { 
    transform: translateY(0) scale(1); 
    opacity: 1; 
  }
}

/* Premium Card Styles */
.premium-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  margin-bottom: 20px;
  border: 1px solid rgba(102, 126, 234, 0.1);
  transition: all 0.3s ease;
}

.premium-card:hover {
  box-shadow: 0 8px 30px rgba(0,0,0,0.12);
  transform: translateY(-2px);
}

.header-badge {
  display: inline-block;
  padding: 6px 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  margin-left: 12px;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}
</style>
</head>
<body>

<div class="sidebar">
  <div class="sidebar-header">
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
      <div style="width: 48px; height: 48px; background: rgba(255,255,255,0.2); border-radius: 12px; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(10px); box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
          <circle cx="12" cy="7" r="4"></circle>
          <path d="M3 21v-2a4 4 0 0 1 4-4"></path>
        </svg>
      </div>
      <div>
        <h3>Order Browser</h3>
        <div class="sidebar-subtitle">Browse and select orders</div>
      </div>
    </div>
  </div>
  
  <div class="sidebar-content">
    <div class="sku-panel">
      <div class="sku-list" id="orderList">
        <div style="padding: 50px 20px; text-align: center; color: #64748b;">
          <div style="width: 56px; height: 56px; margin: 0 auto 20px; background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%); border-radius: 16px; display: flex; align-items: center; justify-content: center;">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #667eea;">
              <circle cx="12" cy="12" r="10"></circle>
              <polyline points="12 6 12 12 16 14"></polyline>
            </svg>
          </div>
          <div style="font-weight: 700; margin-bottom: 8px; font-size: 15px; color: #2d3748;">Loading Orders...</div>
          <div style="font-size: 12px; font-weight: 500;">Please wait a moment</div>
        </div>
      </div>
    </div>
    
    <h4>📋 Selected Order Details</h4>
    <div class="order-list" style="background: white; border: 2px solid rgba(102, 126, 234, 0.1); border-radius: 14px; padding: 0; box-shadow: 0 4px 15px rgba(0,0,0,0.08); overflow: hidden;">
      <div id="selectedOrderInfo" style="font-size: 13px; padding: 20px;">
        <div style="text-align: center; padding: 30px 20px; color: #94a3b8;">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="margin: 0 auto 12px; opacity: 0.4;">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="9" y1="9" x2="15" y2="9"></line>
            <line x1="9" y1="15" x2="15" y2="15"></line>
          </svg>
          <div style="font-weight: 600; font-size: 13px; margin-bottom: 4px; color: #64748b;">No Order Selected</div>
          <div style="font-size: 11px; font-weight: 500; color: #94a3b8;">Select an order from the list above</div>
        </div>
      </div>
    </div>
    <button onclick="clearSelection()" style="width: 100%; margin-top: 12px; padding: 12px 20px; background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; border: none; border-radius: 12px; cursor: pointer; font-weight: 600; font-size: 13px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3); transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); display: flex; align-items: center; justify-content: center; gap: 8px;">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="3 6 5 6 21 6"></polyline>
        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
      </svg>
      <span>Clear Selection</span>
    </button>
  </div>
</div>

<div class="main-content">
<div style="margin-bottom: 30px;">
  <h1 style="font-size: 48px; margin-bottom: 8px; display: flex; align-items: center; gap: 15px; font-weight: 800; letter-spacing: -1px;">
    TetraboX
    <span class="header-badge">PRO</span>
  </h1>
  <p style="color: rgba(255,255,255,0.9); font-size: 18px; margin: 0; font-weight: 400; letter-spacing: 0.5px;">
    AI-Powered 3D Container Optimization Platform
  </p>
</div>

<div class="premium-card" id="orderPackingControls" style="display: none; border: 2px solid #10b981;">
	<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
		<div>
			<div style="font-size: 12px; color: #64748b; font-weight: 500; margin-bottom: 4px;">SELECTED ORDER</div>
			<div id="currentOrderId" style="color: #5a67d8; font-weight: 700; font-size: 20px;">-</div>
		</div>
		<button onclick="packSelectedOrder()" style="padding: 14px 28px; font-size: 15px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; border: none; border-radius: 12px; cursor: pointer; font-weight: 700; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);">
			Pack Order
		</button>
	</div>
</div>

<div class="premium-card" style="background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.9) 100%); border: 2px solid rgba(255,255,255,0.5);">
	<div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
		<div style="width: 52px; height: 52px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 14px; display: flex; align-items: center; justify-content: center; box-shadow: 0 6px 16px rgba(102, 126, 234, 0.35);">
			<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
				<polyline points="14 2 14 8 20 8"></polyline>
				<line x1="16" y1="13" x2="8" y2="13"></line>
				<line x1="16" y1="17" x2="8" y2="17"></line>
				<polyline points="10 9 9 9 8 9"></polyline>
			</svg>
		</div>
		<div>
			<h3 style="margin: 0; font-size: 20px; color: #2d3748; font-weight: 700; letter-spacing: -0.5px;">Quick Start Guide</h3>
			<p style="margin: 0; font-size: 14px; color: #64748b; font-weight: 400;">Follow these steps to optimize your packing</p>
		</div>
	</div>
	<ol style="margin: 0; padding-left: 24px; color: #4a5568; line-height: 2; font-size: 14px;">
		<li>Click <strong style="color: #2d3748;">"Load Orders"</strong> in the sidebar to view available orders</li>
		<li>Browse or search for your order by ID, customer name, or status</li>
		<li>Click on any order to select it and view details</li>
		<li>Click <strong style="color: #2d3748;">"Pack Order"</strong> to run the optimization algorithm</li>
		<li>View packing results in 3D, 2D, or raw JSON format</li>
	</ol>
</div>

<div id="resultsSection" style="display: none; margin-top: 30px;">
  <h3 style="color: white; font-size: 28px; margin-bottom: 15px; font-weight: 700; letter-spacing: -0.5px;">Packing Results</h3>
  
  <div id="compactResult" class="premium-card" style="display: none;"></div>
  
  <div class="premium-card">
    <div id="summary"></div>
    
    <div class="modal-tabs">
      <button class="tab-button active" onclick="showTab('3d')">3D View</button>
      <button class="tab-button" onclick="showTab('2d')">2D Views</button>
      <button class="tab-button" onclick="showTab('json')">Raw Data</button>
    </div>
    
    <div id="tab-3d" class="tab-content active">
      <div id="viz3d" style="width: 100%; min-height: 500px;"></div>
    </div>
    
    <div id="tab-2d" class="tab-content">
      <div style="display: flex; gap: 15px; flex-wrap: wrap; justify-content: center; padding: 20px 0;">
        <div class="premium-card" style="margin: 0;">
          <h4 style="color: #2d3748; margin-bottom: 12px;">Top View (XY)</h4>
          <canvas id="vizTop" width="300" height="300" style="border: 2px solid #e2e8f0; border-radius: 8px;"></canvas>
        </div>
        <div class="premium-card" style="margin: 0;">
          <h4 style="color: #2d3748; margin-bottom: 12px;">Front View (XZ)</h4>
          <canvas id="vizFront" width="300" height="300" style="border: 2px solid #e2e8f0; border-radius: 8px;"></canvas>
        </div>
        <div class="premium-card" style="margin: 0;">
          <h4 style="color: #2d3748; margin-bottom: 12px;">Side View (YZ)</h4>
          <canvas id="vizSide" width="300" height="300" style="border: 2px solid #e2e8f0; border-radius: 8px;"></canvas>
        </div>
      </div>
    </div>
    
    <div id="tab-json" class="tab-content">
      <pre id="log" style="max-height: 500px; overflow-y: auto;"></pre>
    </div>
  </div>
</div>
<script>
let allOrders = [];
let selectedOrder = null;
// Order management functions
async function loadAllOrders(){
  const orderListEl = document.getElementById('orderList');
  
  // Show loading state
  orderListEl.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;"><div style="display: inline-block; width: 20px; height: 20px; border: 3px solid #f3f3f3; border-top: 3px solid #007bff; border-radius: 50%; animation: spin 1s linear infinite;"></div><br><br>Loading Orders...</div><style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>';
  
  try {
    console.log('Fetching orders from /orders');
    const res = await fetch('/orders?limit=100');
    console.log('Response status:', res.status);
    
    if(!res.ok) {
      const errorText = await res.text();
      console.error('Server error:', errorText);
      throw new Error('HTTP ' + res.status + ': ' + errorText);
    }
    
    const data = await res.json();
    allOrders = data.orders || [];
    console.log('Loaded orders:', allOrders.length);
    
    if(!allOrders || allOrders.length === 0) {
      orderListEl.innerHTML = '<div style="padding: 20px; text-align: center; color: #f39c12;">⚠️ No orders found in database</div>';
      return;
    }
    
    renderOrderList(allOrders);
    console.log('Orders loaded successfully');
  } catch(e) {
    console.error('Error loading orders:', e);
    orderListEl.innerHTML = '<div style="padding: 20px; color: red; text-align: center;"><strong>❌ Error loading orders</strong><br><small>' + e.message + '</small><br><br><button onclick="loadAllOrders()" style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">🔄 Retry</button></div>';
  }
}

function renderOrderList(orders){
  const el = document.getElementById('orderList');
  if(!orders || orders.length === 0) {
    el.innerHTML = `
      <div style="padding: 50px 20px; text-align: center; color: #94a3b8;">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="margin: 0 auto 16px; opacity: 0.3;">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        <div style="font-weight: 600; font-size: 14px; margin-bottom: 6px; color: #64748b;">No Orders Found</div>
        <div style="font-size: 12px; font-weight: 500;">No orders are available at this time</div>
      </div>
    `;
    return;
  }
  
  const header = `
    <div style="padding: 16px 20px; background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); border-bottom: 2px solid #a7f3d0; display: flex; align-items: center; gap: 12px;">
      <div style="width: 32px; height: 32px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); border-radius: 10px; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
      </div>
      <div style="flex: 1;">
        <div style="font-weight: 700; color: #065f46; font-size: 14px; letter-spacing: -0.2px;">${orders.length} Orders Ready</div>
        <div style="font-size: 11px; color: #047857; font-weight: 500; margin-top: 2px;">Select an order to view details and pack</div>
      </div>
    </div>
  `;
  
  const orderItems = orders.slice(0, 50).map(order => {
    const statusColor = getStatusColor(order.status);
    const orderDate = new Date(order.order_date).toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' });
    return `
      <div class="sku-item" onclick="selectOrder('${order.order_id}')" style="cursor: pointer;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <div class="sku-code" style="font-size: 13px;">${order.order_id}</div>
          <span style="background: ${statusColor}; color: white; padding: 4px 8px; border-radius: 6px; font-size: 10px; font-weight: 700; letter-spacing: 0.3px; box-shadow: 0 2px 6px ${statusColor}40;">${order.status.toUpperCase()}</span>
        </div>
        <div class="sku-name" style="font-size: 13px; font-weight: 600; color: #2d3748; margin-bottom: 4px;">${order.customer_name}</div>
        <div style="font-size: 11px; color: #94a3b8; font-weight: 500; display: flex; gap: 8px; align-items: center;">
          <span>📦 ${order.total_items} items</span>
          <span>•</span>
          <span>💰 ${order.total_price_try}₺</span>
          <span>•</span>
          <span>📅 ${orderDate}</span>
        </div>
      </div>
    `;
  }).join('');
  
  const footer = orders.length > 50 ? `
    <div style="padding: 14px 20px; text-align: center; background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border-top: 2px solid #e2e8f0;">
      <div style="font-size: 11px; font-weight: 600; color: #64748b; margin-bottom: 4px;">Showing first 50 orders</div>
      <div style="font-size: 10px; font-weight: 500; color: #94a3b8;">Total available: ${orders.length} orders</div>
    </div>
  ` : '';
  
  el.innerHTML = header + orderItems + footer;
}

function getStatusColor(status) {
  const colors = {
    'pending': '#ffc107',
    'processing': '#17a2b8',
    'packed': '#28a745',
    'shipped': '#6f42c1',
    'completed': '#28a745',
    'cancelled': '#dc3545'
  };
  return colors[status.toLowerCase()] || '#6c757d';
}

function selectOrder(orderId) {
  selectedOrder = allOrders.find(order => order.order_id === orderId);
  if(!selectedOrder) {
    console.error('Order not found:', orderId);
    return;
  }
  
  console.log('Selected order:', selectedOrder);
  
  // Update UI
  document.getElementById('currentOrderId').textContent = selectedOrder.order_id;
  document.getElementById('orderPackingControls').style.display = 'block';
  
  // Update selected order info
  updateSelectedOrderInfo();
}

function updateSelectedOrderInfo() {
  const el = document.getElementById('selectedOrderInfo');
  if(!selectedOrder) {
    el.innerHTML = `
      <div style="text-align: center; padding: 30px 20px; color: #94a3b8;">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="margin: 0 auto 12px; opacity: 0.4;">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
          <line x1="9" y1="9" x2="15" y2="9"></line>
          <line x1="9" y1="15" x2="15" y2="15"></line>
        </svg>
        <div style="font-weight: 600; font-size: 13px; margin-bottom: 4px; color: #64748b;">No Order Selected</div>
        <div style="font-size: 11px; font-weight: 500; color: #94a3b8;">Select an order from the list above</div>
      </div>
    `;
    return;
  }
  
  const statusColor = getStatusColor(selectedOrder.status);
  const orderDate = new Date(selectedOrder.order_date).toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' });
  
  el.innerHTML = `
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; position: relative; overflow: hidden;">
      <div style="position: absolute; top: -20px; right: -20px; width: 100px; height: 100px; background: rgba(255,255,255,0.1); border-radius: 50%;"></div>
      <div style="position: relative; z-index: 1;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <div style="font-weight: 700; font-size: 16px; color: white; letter-spacing: -0.3px;">${selectedOrder.order_id}</div>
          <span style="background: ${statusColor}; color: white; padding: 5px 10px; border-radius: 8px; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; box-shadow: 0 2px 8px rgba(0,0,0,0.2);">${selectedOrder.status.toUpperCase()}</span>
        </div>
        <div style="color: rgba(255,255,255,0.95); font-size: 13px; font-weight: 600; margin-bottom: 4px;">${selectedOrder.customer_name}</div>
        <div style="color: rgba(255,255,255,0.8); font-size: 11px; font-weight: 500;">${selectedOrder.customer_email}</div>
        <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.2); display: flex; gap: 16px;">
          <div style="flex: 1;">
            <div style="color: rgba(255,255,255,0.7); font-size: 10px; font-weight: 600; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px;">Items</div>
            <div style="color: white; font-size: 18px; font-weight: 700;">${selectedOrder.total_items}</div>
          </div>
          <div style="flex: 1;">
            <div style="color: rgba(255,255,255,0.7); font-size: 10px; font-weight: 600; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px;">Total</div>
            <div style="color: white; font-size: 18px; font-weight: 700;">${selectedOrder.total_price_try}₺</div>
          </div>
          <div style="flex: 1;">
            <div style="color: rgba(255,255,255,0.7); font-size: 10px; font-weight: 600; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px;">Date</div>
            <div style="color: white; font-size: 11px; font-weight: 600;">${orderDate}</div>
          </div>
        </div>
      </div>
    </div>
    <div style="padding: 16px 20px; background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);">
      <div style="font-size: 11px; font-weight: 700; color: #64748b; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px;">Order Items</div>
      <div style="max-height: 120px; overflow-y: auto;">
        ${selectedOrder.items.map(item => `
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f1f5f9;">
            <span style="font-size: 12px; font-weight: 600; color: #475569;">${item.sku}</span>
            <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 3px 8px; border-radius: 6px; font-size: 10px; font-weight: 700;">×${item.quantity}</span>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

function filterOrders(){
  const query = document.getElementById('orderSearch').value.toLowerCase().trim();
  if(!query) {
    renderOrderList(allOrders);
    return;
  }
  
  const filtered = allOrders.filter(order => {
    return order.order_id.toLowerCase().includes(query) || 
           order.customer_name.toLowerCase().includes(query) ||
           order.customer_email.toLowerCase().includes(query) ||
           order.status.toLowerCase().includes(query);
  });
  
  renderOrderList(filtered);
}

function clearSelection() {
  selectedOrder = null;
  document.getElementById('orderPackingControls').style.display = 'none';
  document.getElementById('currentOrderId').textContent = '-';
  updateSelectedOrderInfo();
  
  // Clear any existing results
  document.getElementById('resultsSection').style.display = 'none';
  document.getElementById('compactResult').style.display = 'none';
}

async function packSelectedOrder() {
  if(!selectedOrder) {
    alert('Please select an order first');
    return;
  }
  
  console.log('Packing order:', selectedOrder.order_id);
  
  // Show loading state
  const compactEl = document.getElementById('compactResult');
  compactEl.style.display = 'block';
  compactEl.innerHTML = '<div style="text-align: center; color: #666;">🔄 Packing order ' + selectedOrder.order_id + '...</div>';
  
  try {
    // Convert order to pack request format
    const packRequest = {
      order_id: selectedOrder.order_id,
      items: selectedOrder.items.map(item => ({
        sku: item.sku,
        quantity: item.quantity
      }))
    };
    
    const res = await fetch('/pack/order', { 
      method:'POST', 
      headers:{'Content-Type':'application/json'}, 
      body: JSON.stringify(packRequest)
    });
    
    if (!res.ok) {
      const errorText = await res.text();
      console.error('Pack order failed:', errorText);
      throw new Error(`HTTP ${res.status}: ${errorText}`);
    }
    
    const j = await res.json();
    
    // Store result globally
    window.packingResult = j;
    
    // Show results section
    document.getElementById('resultsSection').style.display = 'block';
    
    // Show compact result
    showCompactResult(j);
    
    // Render all views inline
    renderSummary(j);
    render3D(j);
    render2DViews(j);
    document.getElementById('log').textContent = JSON.stringify(j, null, 2);
    
    // Scroll to results
    setTimeout(() => {
      document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
    
  } catch(error) {
    document.getElementById('resultsSection').style.display = 'block';
    compactEl.innerHTML = '<div style="color: #dc3545; padding: 20px; text-align: center;"><strong>❌ Error:</strong> ' + error.message + '</div>';
  }
}

async function loadAllSkus(){
  const skuListEl = document.getElementById('skuList');
  
  // Show loading state
  skuListEl.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;"><div style="display: inline-block; width: 20px; height: 20px; border: 3px solid #f3f3f3; border-top: 3px solid #007bff; border-radius: 50%; animation: spin 1s linear infinite;"></div><br><br>Loading SKUs...</div><style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>';
  
  try {
    console.log('Fetching SKUs from /skus?limit=1000');
    const res = await fetch('/skus?limit=1000');
    console.log('Response status:', res.status);
    
    if(!res.ok) {
      const errorText = await res.text();
      console.error('Server error:', errorText);
      throw new Error('HTTP ' + res.status + ': ' + errorText);
    }
    
    allSkus = await res.json();
    console.log('Loaded SKUs:', allSkus.length);
    
    if(!allSkus || allSkus.length === 0) {
      skuListEl.innerHTML = '<div style="padding: 20px; text-align: center; color: #f39c12;">⚠️ No SKUs found in database</div>';
      return;
    }
    
    // Cache names
    allSkus.forEach(sku => {
      nameCache[sku.sku] = (sku.brand||'') + ' ' + (sku.model||'') + (sku.variant?(' ' + sku.variant):'');
    });
    
    renderSkuList(allSkus);
    console.log('SKUs loaded successfully');
  } catch(e) {
    console.error('Error loading SKUs:', e);
    skuListEl.innerHTML = '<div style="padding: 20px; color: red; text-align: center;"><strong>❌ Error loading SKUs</strong><br><small>' + e.message + '</small><br><br><button onclick="loadAllSkus()" style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">🔄 Retry</button></div>';
  }
}

function renderSkuList(skus){
  const el = document.getElementById('skuList');
  if(!skus || skus.length === 0) {
    el.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">No SKUs found</div>';
    return;
  }
  
  const header = `<div style="padding: 10px; background: #e8f5e8; border-bottom: 1px solid #c3e6cb; text-align: center; color: #155724; font-size: 12px; font-weight: bold;">✅ ${skus.length} SKUs loaded successfully</div>`;
  
  const skuItems = skus.slice(0, 100).map(sku => {
    const name = (sku.brand||'') + ' ' + (sku.model||'') + (sku.variant?(' ' + sku.variant):'');
    return `
      <div class="sku-item" onclick="addItemBySku('${sku.sku}')">
        <div class="sku-code">${sku.sku}</div>
        <div class="sku-name">${name}</div>
      </div>
    `;
  }).join('');
  
  const footer = skus.length > 100 ? '<div style="padding: 10px; text-align: center; color: #666; font-size: 11px; background: #f8f9fa; border-top: 1px solid #dee2e6;">Showing first 100 results. Use search to filter.</div>' : '';
  
  el.innerHTML = header + skuItems + footer;
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
// Auto-load orders on page load
window.addEventListener('DOMContentLoaded', () => {
  console.log('Page loaded, initializing order system...');
  updateSelectedOrderInfo(); // Initialize empty order display
  
  // Auto-load orders immediately
  console.log('🔄 Auto-loading orders...');
  loadAllOrders();
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
  if(e.key === 'Escape') {
    clearSelection();
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
  el.style.display = 'block';
  
  if(!j || !j.success) {
    el.innerHTML = `
      <div style="background: white; border: 2px solid #ef4444; border-radius: 16px; padding: 32px; box-shadow: 0 4px 20px rgba(239, 68, 68, 0.15); text-align: center;">
        <div style="width: 64px; height: 64px; background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); border-radius: 16px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="15" y1="9" x2="9" y2="15"></line>
            <line x1="9" y1="9" x2="15" y2="15"></line>
          </svg>
        </div>
        <div style="font-size: 22px; font-weight: 700; color: #dc2626; margin-bottom: 8px;">No Suitable Container Found</div>
        <div style="color: #64748b; font-size: 14px;">Unable to pack items even with multiple containers</div>
      </div>
    `;
    return;
  }
  
  const isMultiContainer = j.container_count > 1;
  const containerText = isMultiContainer ? 
    `${j.container_count} containers` : 
    `${j.container_name || 'Unknown'} (${j.shipping_company || 'Unknown'})`;
  
  el.innerHTML = `
    <div style="background: white; border: 2px solid #10b981; border-radius: 16px; padding: 24px; box-shadow: 0 8px 24px rgba(16, 185, 129, 0.15);">
      <div style="display: flex; align-items: center; gap: 20px;">
        <div style="width: 64px; height: 64px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); border-radius: 16px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        </div>
        <div style="flex: 1;">
          <div style="font-size: 24px; font-weight: 800; color: #059669; margin-bottom: 8px; letter-spacing: -0.5px;">
            Packing Complete
            ${isMultiContainer ? '<span style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 5px 14px; border-radius: 14px; font-size: 12px; margin-left: 12px; box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3); font-weight: 700; letter-spacing: 0.5px;">MULTI-BOX</span>' : ''}
          </div>
          <div style="color: #64748b; font-size: 15px; line-height: 1.6; font-weight: 500;">
            <strong style="color: #2d3748;">${containerText}</strong> • 
            <strong style="color: #2d3748;">${j.total_items || j.placements?.length || 0}</strong> items • 
            <strong style="color: #5a67d8;">${(j.utilization*100).toFixed(1)}%</strong> utilization • 
            <strong style="color: #059669;">${(j.total_price || j.price_try || 0).toFixed(2)}₺</strong>
          </div>
        </div>
      </div>
    </div>
  `;
}

// Modal functions removed - now using inline display

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
  
  // Scroll to results section
  setTimeout(() => {
    document.getElementById('tab-' + tabName).scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, 150);
}

function renderSummary(j){
  const el = document.getElementById('summary');
  if(!j || !j.success){ 
    el.innerHTML = '<div style="padding: 20px; text-align: center; color: #dc3545;">❌ No feasible container found.</div>'; 
    return; 
  }
  
  const isMultiContainer = j.container_count > 1;
  
  if(isMultiContainer) {
    // Premium multi-container summary
    el.innerHTML = `
      <div style="margin-bottom: 30px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 24px; border-radius: 16px; box-shadow: 0 8px 24px rgba(102, 126, 234, 0.25); margin-bottom: 24px;">
          <h3 style="margin: 0 0 20px 0; color: white; font-size: 28px; font-weight: 800; display: flex; align-items: center; gap: 12px; letter-spacing: -0.5px;">
            Multi-Container Packing
            <span style="background: rgba(255,255,255,0.25); padding: 6px 14px; border-radius: 20px; font-size: 14px; font-weight: 700; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">${j.container_count} Boxes</span>
          </h3>
          
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
            <div style="background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); padding: 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2);">
              <div style="color: rgba(255,255,255,0.8); font-size: 12px; font-weight: 500; margin-bottom: 4px;">TOTAL CONTAINERS</div>
              <div style="color: white; font-size: 32px; font-weight: 700;">${j.container_count}</div>
            </div>
            <div style="background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); padding: 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2);">
              <div style="color: rgba(255,255,255,0.8); font-size: 12px; font-weight: 500; margin-bottom: 4px;">TOTAL ITEMS</div>
              <div style="color: white; font-size: 32px; font-weight: 700;">${j.total_items}</div>
            </div>
            <div style="background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); padding: 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2);">
              <div style="color: rgba(255,255,255,0.8); font-size: 12px; font-weight: 500; margin-bottom: 4px;">TOTAL PRICE</div>
              <div style="color: white; font-size: 32px; font-weight: 700;">${j.total_price.toFixed(2)}₺</div>
            </div>
            <div style="background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); padding: 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2);">
              <div style="color: rgba(255,255,255,0.8); font-size: 12px; font-weight: 500; margin-bottom: 4px;">AVG UTILIZATION</div>
              <div style="color: white; font-size: 32px; font-weight: 700;">${(j.utilization*100).toFixed(1)}%</div>
            </div>
            <div style="background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); padding: 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2);">
              <div style="color: rgba(255,255,255,0.8); font-size: 12px; font-weight: 500; margin-bottom: 4px;">TOTAL VOLUME</div>
              <div style="color: white; font-size: 32px; font-weight: 700;">${(j.container_volume_cm3/1000).toFixed(1)}L</div>
            </div>
            <div style="background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); padding: 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2);">
              <div style="color: rgba(255,255,255,0.8); font-size: 12px; font-weight: 500; margin-bottom: 4px;">ALGORITHM</div>
              <div style="color: #fbbf24; font-size: 16px; font-weight: 700;">Greedy Max</div>
            </div>
          </div>
        </div>
        
        <div style="background: white; padding: 24px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
          <h4 style="margin: 0 0 20px 0; color: #2d3748; font-size: 22px; font-weight: 700; display: flex; align-items: center; gap: 10px; letter-spacing: -0.5px;">
            Container Breakdown
            <span style="background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%); padding: 5px 13px; border-radius: 20px; font-size: 13px; color: #64748b; font-weight: 600;">${j.containers.length} containers</span>
          </h4>
          
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px;">
            ${j.containers.map((container, idx) => {
              const utilization = container.utilization * 100;
              const utilizationColor = utilization >= 80 ? '#10b981' : utilization >= 60 ? '#f59e0b' : '#ef4444';
              return `
                <div style="background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%); border: 2px solid #e2e8f0; border-radius: 12px; padding: 18px; transition: all 0.3s ease; position: relative; overflow: hidden;">
                  <div style="position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, ${utilizationColor} ${utilization}%, #e5e7eb ${utilization}%);"></div>
                  
                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                      <div style="width: 32px; height: 32px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 14px;">${idx+1}</div>
                      <div>
                        <div style="font-weight: 700; color: #2d3748; font-size: 15px;">${container.container_name || 'Unknown'}</div>
                        <div style="font-size: 12px; color: #64748b;">${container.shipping_company || 'Unknown'}</div>
                      </div>
                    </div>
                    <div style="background: ${utilizationColor}; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 700;">
                      ${utilization.toFixed(1)}%
                    </div>
                  </div>
                  
                  <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 12px;">
                    <div style="background: #f8fafc; padding: 10px; border-radius: 8px;">
                      <div style="color: #64748b; font-size: 11px; font-weight: 500; margin-bottom: 2px;">ITEMS</div>
                      <div style="color: #2d3748; font-size: 18px; font-weight: 700;">${container.placements.length}</div>
                    </div>
                    <div style="background: #f8fafc; padding: 10px; border-radius: 8px;">
                      <div style="color: #64748b; font-size: 11px; font-weight: 500; margin-bottom: 2px;">PRICE</div>
                      <div style="color: #059669; font-size: 18px; font-weight: 700;">${(container.price_try || 0).toFixed(2)}₺</div>
                    </div>
                    <div style="background: #f8fafc; padding: 10px; border-radius: 8px;">
                      <div style="color: #64748b; font-size: 11px; font-weight: 500; margin-bottom: 2px;">VOLUME</div>
                      <div style="color: #2d3748; font-size: 18px; font-weight: 700;">${(container.container_volume_cm3/1000).toFixed(1)}L</div>
                    </div>
                    <div style="background: #f8fafc; padding: 10px; border-radius: 8px;">
                      <div style="color: #64748b; font-size: 11px; font-weight: 500; margin-bottom: 2px;">REMAINING</div>
                      <div style="color: #64748b; font-size: 18px; font-weight: 700;">${(container.remaining_volume_cm3/1000).toFixed(1)}L</div>
                    </div>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
          
          <div style="margin-top: 20px; padding: 20px; background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-radius: 12px; border-left: 5px solid #f59e0b; font-size: 14px; line-height: 1.7;">
            <strong style="color: #92400e; font-size: 15px; display: block; margin-bottom: 8px;">Optimization Strategy</strong>
            <div style="color: #78350f;">
              Order was intelligently split across <strong>${j.container_count} containers</strong> using our <strong>Greedy Max Utilization</strong> algorithm to minimize total cost while maximizing space efficiency.
            </div>
          </div>
        </div>
      </div>
    `;
  } else {
    // Premium single container summary
    let maxW=0, maxL=0, maxH=0;
    if(j.placements && j.placements.length > 0) {
      j.placements.forEach(p=>{ 
        maxW=Math.max(maxW, p.position_mm[0]+p.size_mm[0]); 
        maxL=Math.max(maxL, p.position_mm[1]+p.size_mm[1]); 
        maxH=Math.max(maxH, p.position_mm[2]+p.size_mm[2]); 
      });
    }
    
    const utilization = j.utilization * 100;
    const utilizationColor = utilization >= 80 ? '#10b981' : utilization >= 60 ? '#f59e0b' : '#ef4444';
    
    el.innerHTML = `
      <div style="margin-bottom: 30px;">
        <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 24px; border-radius: 16px; box-shadow: 0 8px 24px rgba(16, 185, 129, 0.25); margin-bottom: 24px;">
          <h3 style="margin: 0 0 20px 0; color: white; font-size: 28px; font-weight: 800; display: flex; align-items: center; gap: 12px; letter-spacing: -0.5px;">
            Single Container Solution
            <span style="background: rgba(255,255,255,0.25); padding: 6px 14px; border-radius: 20px; font-size: 14px; font-weight: 700; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">Optimal</span>
          </h3>
          
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px;">
            <div style="background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); padding: 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2);">
              <div style="color: rgba(255,255,255,0.8); font-size: 12px; font-weight: 500; margin-bottom: 4px;">CONTAINER</div>
              <div style="color: white; font-size: 18px; font-weight: 700;">${j.container_name || 'Unknown'}</div>
              <div style="color: rgba(255,255,255,0.7); font-size: 12px; margin-top: 2px;">${j.shipping_company || 'Unknown'}</div>
            </div>
            <div style="background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); padding: 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2);">
              <div style="color: rgba(255,255,255,0.8); font-size: 12px; font-weight: 500; margin-bottom: 4px;">ITEMS</div>
              <div style="color: white; font-size: 32px; font-weight: 700;">${j.placements ? j.placements.length : 0}</div>
            </div>
            <div style="background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); padding: 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2);">
              <div style="color: rgba(255,255,255,0.8); font-size: 12px; font-weight: 500; margin-bottom: 4px;">UTILIZATION</div>
              <div style="color: white; font-size: 32px; font-weight: 700;">${utilization.toFixed(1)}%</div>
            </div>
            <div style="background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); padding: 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2);">
              <div style="color: rgba(255,255,255,0.8); font-size: 12px; font-weight: 500; margin-bottom: 4px;">PRICE</div>
              <div style="color: white; font-size: 32px; font-weight: 700;">${(j.price_try || 0).toFixed(2)}₺</div>
            </div>
            <div style="background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); padding: 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2);">
              <div style="color: rgba(255,255,255,0.8); font-size: 12px; font-weight: 500; margin-bottom: 4px;">VOLUME</div>
              <div style="color: white; font-size: 20px; font-weight: 700;">${(j.container_volume_cm3/1000).toFixed(1)}L / ${(j.remaining_volume_cm3/1000).toFixed(1)}L free</div>
            </div>
            <div style="background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); padding: 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2);">
              <div style="color: rgba(255,255,255,0.8); font-size: 12px; font-weight: 500; margin-bottom: 4px;">DIMENSIONS</div>
              <div style="color: white; font-size: 16px; font-weight: 700;">${maxW}×${maxL}×${maxH}mm</div>
            </div>
          </div>
        </div>
        
        <div style="padding: 20px; background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); border-radius: 12px; border-left: 5px solid #10b981; font-size: 14px; line-height: 1.7;">
          <strong style="color: #065f46; font-size: 16px; display: block; margin-bottom: 8px;">Perfect Single-Container Solution</strong>
          <div style="color: #047857;">
            All <strong>${j.placements ? j.placements.length : 0} items</strong> fit perfectly in a single <strong>${j.container_name || 'Unknown'}</strong> container from <strong>${j.shipping_company || 'Unknown'}</strong>. This is the most cost-effective solution with <strong>${utilization.toFixed(1)}% utilization</strong>.
          </div>
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

function renderMultiContainer2D(j) {
  console.log('Rendering multi-container 2D views');
  
  // Replace 2D tab content with multi-container views
  const tab2d = document.getElementById('tab-2d');
  tab2d.innerHTML = '';
  
  // Add header
  const header = document.createElement('div');
  header.style.padding = '20px';
  header.style.textAlign = 'center';
  header.style.color = '#2d3748';
  header.style.fontWeight = 'bold';
  header.style.fontSize = '18px';
  header.innerHTML = `📐 2D Views - ${j.containers.length} Containers`;
  tab2d.appendChild(header);
  
  // Create grid for all containers
  const containersDiv = document.createElement('div');
  containersDiv.style.display = 'flex';
  containersDiv.style.flexDirection = 'column';
  containersDiv.style.gap = '30px';
  containersDiv.style.padding = '20px';
  tab2d.appendChild(containersDiv);
  
  // Render 2D views for each container
  j.containers.forEach((container, index) => {
    const containerCard = document.createElement('div');
    containerCard.className = 'premium-card';
    containerCard.style.border = '2px solid #667eea';
    
    const containerHeader = document.createElement('div');
    containerHeader.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
    containerHeader.style.color = 'white';
    containerHeader.style.padding = '12px 16px';
    containerHeader.style.borderRadius = '12px';
    containerHeader.style.marginBottom = '20px';
    containerHeader.style.fontWeight = '700';
    containerHeader.innerHTML = `Container ${index + 1}: ${container.container_name || 'Unknown'} - ${container.placements.length} items`;
    containerCard.appendChild(containerHeader);
    
    // Create 2D canvas container
    const canvasContainer = document.createElement('div');
    canvasContainer.style.display = 'flex';
    canvasContainer.style.gap = '15px';
    canvasContainer.style.flexWrap = 'wrap';
    canvasContainer.style.justifyContent = 'center';
    
    // Create three canvases for this container
    ['Top', 'Front', 'Side'].forEach(viewName => {
      const canvasDiv = document.createElement('div');
      canvasDiv.style.textAlign = 'center';
      
      const label = document.createElement('h4');
      label.style.color = '#2d3748';
      label.style.marginBottom = '10px';
      label.textContent = `${viewName} View`;
      canvasDiv.appendChild(label);
      
      const canvas = document.createElement('canvas');
      canvas.width = 280;
      canvas.height = 280;
      canvas.style.border = '2px solid #e2e8f0';
      canvas.style.borderRadius = '8px';
      canvas.id = `viz${viewName}_${index}`;
      canvasDiv.appendChild(canvas);
      
      canvasContainer.appendChild(canvasDiv);
    });
    
    containerCard.appendChild(canvasContainer);
    containersDiv.appendChild(containerCard);
    
    // Render the views
    const containerData = {
      placements: container.placements,
      inner_w_mm: container.inner_w_mm,
      inner_l_mm: container.inner_l_mm,
      inner_h_mm: container.inner_h_mm,
      success: true
    };
    
    renderSingle2DViews(containerData, `vizTop_${index}`, `vizFront_${index}`, `vizSide_${index}`);
  });
}

function render2DViews(j){
  if(!j || !j.success) {
    ['vizTop', 'vizFront', 'vizSide'].forEach(id => {
      const canvas = document.getElementById(id);
      if(canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0,0,canvas.width, canvas.height);
        ctx.fillStyle = '#f0f0f0';
        ctx.fillRect(0,0,canvas.width, canvas.height);
        ctx.fillStyle = '#666';
        ctx.font = '14px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('No data', canvas.width/2, canvas.height/2);
      }
    });
    return;
  }
  
  // Handle multi-container results
  if(j.container_count > 1 && j.containers) {
    renderMultiContainer2D(j);
    return;
  }
  
  // Handle single container
  if(!Array.isArray(j.placements)) {
    return;
  }
  
  renderSingle2DViews(j, 'vizTop', 'vizFront', 'vizSide');
}

function renderSingle2DViews(j, topId, frontId, sideId) {
  
  // Use actual container dimensions
  let maxW, maxL, maxH;
  
  if(j.inner_w_mm && j.inner_l_mm && j.inner_h_mm) {
    // Use exact container dimensions from the database
    maxW = j.inner_w_mm;
    maxL = j.inner_l_mm;
    maxH = j.inner_h_mm;
    console.log(`2D Views using actual container dimensions: ${maxW}×${maxL}×${maxH}mm`);
  } else {
    // Fallback: calculate from placements
    maxW = 0;
    maxL = 0; 
    maxH = 0;
    j.placements.forEach(p=>{ 
      maxW = Math.max(maxW, p.position_mm[0]+p.size_mm[0]); 
      maxL = Math.max(maxL, p.position_mm[1]+p.size_mm[1]); 
      maxH = Math.max(maxH, p.position_mm[2]+p.size_mm[2]); 
    });
    console.log(`2D Views using calculated dimensions: ${maxW}×${maxL}×${maxH}mm`);
  }
  
  const colorForSku = (sku)=>{ 
    let h=0; 
    for(let i=0;i<sku.length;i++){ 
      h=(h*31 + sku.charCodeAt(i))>>>0; 
    } 
    return `hsl(${h%360},70%,55%)`; 
  };
  
  // Top View (XY plane)
  const renderTopView = () => {
    const canvas = document.getElementById(topId);
    if(!canvas) return;
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
    const canvas = document.getElementById(frontId);
    if(!canvas) return;
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
    const canvas = document.getElementById(sideId);
    if(!canvas) return;
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
  
  if(!j || !j.success) {
    el.innerHTML = '<p>No packing result to visualize</p>';
    return;
  }
  
  console.log('Starting 3D render with data:', j);
  
  // Handle multi-container results
  if(j.container_count > 1 && j.containers) {
    renderMultiContainer3D(j, el);
    return;
  }
  
  // Handle single container (legacy format)
  if(!j.box_id || !Array.isArray(j.placements) || j.placements.length === 0) {
    el.innerHTML = '<p>No placements to visualize</p>';
    return;
  }
  
  renderSingleContainer3D(j, el);
}

function renderMultiContainer3D(j, el) {
  console.log('Rendering multi-container 3D view:', j.containers.length, 'containers');
  
  // Create premium header with gradient and stats
  const header = document.createElement('div');
  header.style.padding = '30px';
  header.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
  header.style.color = 'white';
  header.style.borderRadius = '16px 16px 0 0';
  header.style.boxShadow = '0 4px 20px rgba(102, 126, 234, 0.3)';
  header.innerHTML = `
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
      <div style="display: flex; align-items: center; gap: 15px;">
        <div style="width: 56px; height: 56px; background: rgba(255,255,255,0.2); border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 28px; backdrop-filter: blur(10px); box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
          📦
        </div>
        <div>
          <div style="font-size: 28px; font-weight: 800; letter-spacing: -0.5px; margin-bottom: 4px;">
            Multi-Container Solution
          </div>
          <div style="font-size: 14px; opacity: 0.9; font-weight: 500;">
            Optimized packing across ${j.containers.length} containers
          </div>
        </div>
      </div>
      <div style="text-align: right;">
        <div style="background: rgba(255,255,255,0.25); padding: 8px 18px; border-radius: 20px; font-size: 24px; font-weight: 700; backdrop-filter: blur(10px); box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
          ${j.containers.length} Boxes
        </div>
      </div>
    </div>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px;">
      <div style="background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); padding: 14px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2);">
        <div style="font-size: 11px; font-weight: 600; opacity: 0.8; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px;">Total Items</div>
        <div style="font-size: 26px; font-weight: 700;">${j.total_items}</div>
      </div>
      <div style="background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); padding: 14px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2);">
        <div style="font-size: 11px; font-weight: 600; opacity: 0.8; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px;">Avg Utilization</div>
        <div style="font-size: 26px; font-weight: 700;">${(j.utilization*100).toFixed(1)}%</div>
      </div>
      <div style="background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); padding: 14px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2);">
        <div style="font-size: 11px; font-weight: 600; opacity: 0.8; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px;">Total Price</div>
        <div style="font-size: 26px; font-weight: 700;">${j.total_price.toFixed(2)}₺</div>
      </div>
    </div>
  `;
  el.appendChild(header);
  
  // Create container for all 3D views
  const containersDiv = document.createElement('div');
  containersDiv.style.display = 'flex';
  containersDiv.style.flexDirection = 'column';
  containersDiv.style.gap = '24px';
  containersDiv.style.padding = '24px';
  containersDiv.style.background = 'linear-gradient(135deg, #f8fafc 0%, #ffffff 100%)';
  containersDiv.style.borderRadius = '0 0 16px 16px';
  el.appendChild(containersDiv);
  
  // Render each container
  j.containers.forEach((container, index) => {
    const containerDiv = document.createElement('div');
    containerDiv.style.border = '2px solid rgba(102, 126, 234, 0.2)';
    containerDiv.style.borderRadius = '16px';
    containerDiv.style.overflow = 'hidden';
    containerDiv.style.background = 'white';
    containerDiv.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.08)';
    containerDiv.style.transition = 'all 0.3s ease';
    
    // Add hover effect
    containerDiv.addEventListener('mouseenter', () => {
      containerDiv.style.transform = 'translateY(-2px)';
      containerDiv.style.boxShadow = '0 8px 30px rgba(102, 126, 234, 0.15)';
    });
    containerDiv.addEventListener('mouseleave', () => {
      containerDiv.style.transform = 'translateY(0)';
      containerDiv.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.08)';
    });
    
    // Container header with premium design
    const containerHeader = document.createElement('div');
    const utilization = container.utilization * 100;
    const utilizationColor = utilization >= 80 ? '#10b981' : utilization >= 60 ? '#f59e0b' : '#ef4444';
    
    containerHeader.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
    containerHeader.style.color = 'white';
    containerHeader.style.padding = '20px 24px';
    containerHeader.style.position = 'relative';
    containerHeader.style.overflow = 'hidden';
    
    containerHeader.innerHTML = `
      <div style="position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, ${utilizationColor} ${utilization}%, rgba(255,255,255,0.2) ${utilization}%);"></div>
      <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 4px;">
        <div style="display: flex; align-items: center; gap: 16px;">
          <div style="width: 48px; height: 48px; background: rgba(255,255,255,0.2); border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 22px; font-weight: 700; backdrop-filter: blur(10px); box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            ${index + 1}
          </div>
          <div>
            <div style="font-size: 20px; font-weight: 700; letter-spacing: -0.3px; margin-bottom: 4px;">
              ${container.container_name || 'Unknown'}
            </div>
            <div style="font-size: 13px; opacity: 0.9; font-weight: 500;">
              ${container.shipping_company || 'Unknown'} • ${container.placements.length} items
            </div>
          </div>
        </div>
        <div style="text-align: right;">
          <div style="background: ${utilizationColor}; padding: 8px 16px; border-radius: 20px; font-size: 18px; font-weight: 700; box-shadow: 0 2px 10px rgba(0,0,0,0.15); margin-bottom: 4px;">
            ${utilization.toFixed(1)}%
          </div>
          <div style="font-size: 13px; opacity: 0.9; font-weight: 600;">
            ${(container.price_try || 0).toFixed(2)}₺
          </div>
        </div>
      </div>
    `;
    containerDiv.appendChild(containerHeader);
    
    // 3D view for this container - better quality size
    const viz3dDiv = document.createElement('div');
    viz3dDiv.style.width = '100%';
    viz3dDiv.style.height = '450px';
    viz3dDiv.id = `viz3d_${index}`;
    containerDiv.appendChild(viz3dDiv);
    
    containersDiv.appendChild(containerDiv);
    
    // Render this container's 3D view with minimal delay
    setTimeout(() => {
      const containerData = {
        box_id: container.container_id,
        container_name: container.container_name,
        shipping_company: container.shipping_company,
        placements: container.placements,
        utilization: container.utilization,
        container_volume_cm3: container.container_volume_cm3,
        remaining_volume_cm3: container.remaining_volume_cm3,
        price_try: container.price_try,
        inner_w_mm: container.inner_w_mm,
        inner_l_mm: container.inner_l_mm,
        inner_h_mm: container.inner_h_mm,
        success: true
      };
      renderSingleContainer3D(containerData, viz3dDiv);
    }, 50 * index);
  });
}

function renderSingleContainer3D(j, el) {
  console.log('Rendering single container 3D view');
  
  // Interactive 3D visualization with mouse controls
  try {
    // Create container for canvas and controls
    const container = document.createElement('div');
    container.style.position = 'relative';
    container.style.width = '100%';
    container.style.height = el.style.height || '600px';
    container.style.background = 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)';
    container.style.borderRadius = '12px';
    container.style.boxShadow = '0 8px 32px rgba(0,0,0,0.3)';
    container.style.overflow = 'hidden';
    el.appendChild(container);
    
    const canvas = document.createElement('canvas');
    // Better balance between performance and quality with high-DPI support
    const containerWidth = container.clientWidth || 800;
    const containerHeight = parseInt(el.style.height) || 600;
    const pixelRatio = Math.min(window.devicePixelRatio || 1, 2); // Cap at 2x for performance
    
    const displayWidth = Math.min(containerWidth, 900);
    const displayHeight = Math.min(containerHeight, 500);
    
    canvas.width = displayWidth * pixelRatio;
    canvas.height = displayHeight * pixelRatio;
    canvas.style.width = displayWidth + 'px';
    canvas.style.height = displayHeight + 'px';
    canvas.style.cursor = 'grab';
    canvas.style.display = 'block';
    container.appendChild(canvas);
    
    // Get canvas context and scale for high-DPI displays
    const ctx = canvas.getContext('2d');
    ctx.scale(pixelRatio, pixelRatio);
    
    // Add premium control panel
    const controlPanel = document.createElement('div');
    controlPanel.style.position = 'absolute';
    controlPanel.style.top = '20px';
    controlPanel.style.right = '20px';
    controlPanel.style.background = 'linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(248,250,252,0.98) 100%)';
    controlPanel.style.backdropFilter = 'blur(20px)';
    controlPanel.style.padding = '20px';
    controlPanel.style.borderRadius = '16px';
    controlPanel.style.boxShadow = '0 8px 32px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.08)';
    controlPanel.style.border = '1px solid rgba(102, 126, 234, 0.1)';
    controlPanel.style.fontFamily = 'Inter, -apple-system, BlinkMacSystemFont, sans-serif';
    controlPanel.style.fontSize = '13px';
    controlPanel.style.minWidth = '200px';
    controlPanel.style.transition = 'all 0.3s ease';
    container.appendChild(controlPanel);
    
    // Use actual container dimensions from the API response
    let maxW, maxL, maxH;
    
    if(j.inner_w_mm && j.inner_l_mm && j.inner_h_mm) {
      // Use exact container dimensions from the database
      maxW = j.inner_w_mm;
      maxL = j.inner_l_mm;
      maxH = j.inner_h_mm;
      console.log(`Using actual container dimensions: ${maxW}×${maxL}×${maxH}mm`);
    } else {
      // Fallback: calculate from placements (old method)
      maxW = 0;
      maxL = 0; 
      maxH = 0;
      j.placements.forEach(p=>{ 
        maxW = Math.max(maxW, p.position_mm[0]+p.size_mm[0]); 
        maxL = Math.max(maxL, p.position_mm[1]+p.size_mm[1]); 
        maxH = Math.max(maxH, p.position_mm[2]+p.size_mm[2]); 
      });
      console.log(`Using calculated dimensions from placements: ${maxW}×${maxL}×${maxH}mm`);
    }
    
    // 3D view state with smooth animation - improved zoom and performance
    let rotationX = 0.5;
    let rotationY = 0.8;
    let targetRotationX = 0.5;
    let targetRotationY = 0.8;
    let scale = Math.min(300/Math.max(maxW, maxL), 200/maxH) * 1.2; // Increased zoom from 0.6 to 1.2
    let targetScale = scale;
    // Use display dimensions for offset, not canvas dimensions
    let offsetX = displayWidth/2;
    let offsetY = displayHeight/2;
    let isDragging = false;
    let lastMouseX = 0;
    let lastMouseY = 0;
    let autoRotate = false;
    let animationTime = 0;
    let isVisible = true; // Start as visible
    
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
    
    // Enhanced color with lighting
    const colorForSku = (sku, lightIntensity = 1.0) => {
      let h = 0;
      for(let i = 0; i < sku.length; i++){
        h = (h * 31 + sku.charCodeAt(i)) >>> 0;
      }
      const saturation = 75;
      const baseLightness = 50;
      const lightness = Math.min(90, Math.max(20, baseLightness * lightIntensity));
      return `hsl(${h % 360}, ${saturation}%, ${lightness}%)`;
    };
    
    // Calculate lighting based on face normal
    const calculateLighting = (face, corners) => {
      // Simple lighting from top-right-front
      const lightDir = [0.5, -0.3, 0.8];
      const normalize = (v) => {
        const len = Math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2]);
        return len > 0 ? [v[0]/len, v[1]/len, v[2]/len] : [0,0,0];
      };
      
      // Calculate face normal (simplified)
      const faceNormals = [
        [0, 0, -1],  // bottom
        [0, 0, 1],   // top
        [0, -1, 0],  // front
        [0, 1, 0],   // back
        [-1, 0, 0],  // left
        [1, 0, 0]    // right
      ];
      
      const normal = faceNormals[face] || [0, 0, 1];
      
      // Rotate normal with same rotation as object
      const cosX = Math.cos(rotationX), sinX = Math.sin(rotationX);
      const cosY = Math.cos(rotationY), sinY = Math.sin(rotationY);
      
      const ny = normal[1] * cosX - normal[2] * sinX;
      const nz = normal[1] * sinX + normal[2] * cosX;
      const nx = normal[0] * cosY + nz * sinY;
      
      // Dot product for lighting
      const dot = nx * lightDir[0] + ny * lightDir[1] + nz * lightDir[2];
      return 0.5 + 0.5 * Math.max(0, dot); // Range 0.5 to 1.0
    };
    
    // Instance-specific controls using unique IDs
    const instanceId = 'view_' + Math.random().toString(36).substr(2, 9);
    const resetBtnId = 'resetBtn_' + instanceId;
    const autoRotateBtnId = 'autoRotateBtn_' + instanceId;
    
    // Update control panel with unique IDs - premium design
    controlPanel.innerHTML = `
      <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 18px;">
        <div style="width: 36px; height: 36px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.25);">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M12 1v6m0 6v6m-5.2-5.2l4.2 4.2m4.2-4.2l-4.2 4.2"></path>
          </svg>
        </div>
        <div>
          <div style="font-weight: 700; color: #1e293b; font-size: 15px; letter-spacing: -0.2px;">Controls</div>
          <div style="font-size: 11px; color: #64748b; font-weight: 500; margin-top: 2px;">3D Interaction</div>
        </div>
      </div>
      
      <div style="margin: 0; display: flex; flex-direction: column; gap: 10px; margin-bottom: 18px;">
        <button id="${resetBtnId}" style="width: 100%; padding: 12px 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: 600; font-size: 13px; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3); transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); display: flex; align-items: center; justify-content: center; gap: 8px;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 4 23 10 17 10"></polyline>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
          </svg>
          <span>Reset View</span>
        </button>
        <button id="${autoRotateBtnId}" style="width: 100%; padding: 12px 16px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: 600; font-size: 13px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3); transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); display: flex; align-items: center; justify-content: center; gap: 8px;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"></path>
          </svg>
          <span>Auto Rotate</span>
        </button>
      </div>
      
      <div style="background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); padding: 14px; border-radius: 10px; border: 1px solid #e2e8f0;">
        <div style="font-size: 11px; font-weight: 600; color: #64748b; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px;">Shortcuts</div>
        <div style="color: #475569; font-size: 12px; line-height: 1.8; font-weight: 500;">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
            <div style="min-width: 60px; padding: 4px 8px; background: white; border-radius: 6px; font-weight: 600; font-size: 11px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">Drag</div>
            <div style="color: #64748b;">Rotate view</div>
          </div>
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
            <div style="min-width: 60px; padding: 4px 8px; background: white; border-radius: 6px; font-weight: 600; font-size: 11px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">Scroll</div>
            <div style="color: #64748b;">Zoom in/out</div>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <div style="min-width: 60px; padding: 4px 8px; background: white; border-radius: 6px; font-weight: 600; font-size: 11px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">Click</div>
            <div style="color: #64748b;">Item details</div>
          </div>
        </div>
      </div>
    `;
    
    // Attach event listeners to instance-specific buttons
    document.getElementById(resetBtnId).addEventListener('click', () => {
      targetRotationX = 0.5;
      targetRotationY = 0.8;
      targetScale = Math.min(300/Math.max(maxW, maxL), 200/maxH) * 1.2;
    });
    
    document.getElementById(autoRotateBtnId).addEventListener('click', () => {
      autoRotate = !autoRotate;
      const btn = document.getElementById(autoRotateBtnId);
      if(autoRotate) {
        btn.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
        btn.style.boxShadow = '0 4px 12px rgba(239, 68, 68, 0.3)';
        btn.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <rect x="9" y="9" width="6" height="6"></rect>
          </svg>
          <span>Stop Rotation</span>
        `;
      } else {
        btn.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
        btn.style.boxShadow = '0 4px 12px rgba(16, 185, 129, 0.3)';
        btn.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"></path>
          </svg>
          <span>Auto Rotate</span>
        `;
      }
    });
    
    // Add hover effects to buttons
    const addButtonHoverEffect = (btnId) => {
      const btn = document.getElementById(btnId);
      btn.addEventListener('mouseenter', () => {
        btn.style.transform = 'translateY(-2px)';
        btn.style.boxShadow = '0 4px 12px rgba(0,0,0,0.2)';
      });
      btn.addEventListener('mouseleave', () => {
        btn.style.transform = 'translateY(0)';
      });
    };
    
    addButtonHoverEffect(resetBtnId);
    addButtonHoverEffect(autoRotateBtnId);
    
    // Render function with smooth animations
    const render = () => {
      // Smooth animation interpolation
      if (autoRotate) {
        targetRotationY += 0.01;
        animationTime += 0.016;
      }
      
      // Smooth camera movement - faster interpolation for better performance
      rotationX += (targetRotationX - rotationX) * 0.25;
      rotationY += (targetRotationY - rotationY) * 0.25;
      scale += (targetScale - scale) * 0.25;
      
      // Clear with gradient background
      const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
      gradient.addColorStop(0, '#1a1a2e');
      gradient.addColorStop(0.5, '#16213e');
      gradient.addColorStop(1, '#0f3460');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      // Add grid background
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
      ctx.lineWidth = 1;
      const gridSize = 30;
      for (let x = 0; x < canvas.width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
      }
      for (let y = 0; y < canvas.height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
      }
      
      // Premium title with gradient effect
      ctx.save();
      
      // Create gradient for title text
      const titleGradient = ctx.createLinearGradient(20, 0, 400, 0);
      titleGradient.addColorStop(0, '#ffffff');
      titleGradient.addColorStop(1, '#e0e7ff');
      
      // Title shadow
      ctx.shadowColor = 'rgba(0, 0, 0, 0.4)';
      ctx.shadowBlur = 8;
      ctx.shadowOffsetY = 2;
      
      // Main title
      ctx.fillStyle = titleGradient;
      ctx.font = '700 18px Inter, Arial';
      ctx.letterSpacing = '0.5px';
      ctx.fillText('3D CONTAINER VIEW', 20, 32);
      
      // Subtitle with container info
      ctx.shadowBlur = 4;
      ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
      ctx.font = '400 12px Inter, Arial';
      ctx.fillText(`${j.container_name || 'Container'} | ${j.shipping_company || ''}`.trim(), 20, 50);
      
      ctx.restore();
      
      // Collect all faces for z-sorting
      const faces = [];
      
      // Container faces - using exact container dimensions
      const containerCorners = [
        [0,0,0], [maxW,0,0], [maxW,maxL,0], [0,maxL,0],
        [0,0,maxH], [maxW,0,maxH], [maxW,maxL,maxH], [0,maxL,maxH]
      ];
      
      console.log(`Drawing container wireframe: ${maxW}×${maxL}×${maxH}mm`);
      
      const containerFaces = [
        [0,1,2,3], [4,7,6,5], [0,4,5,1], [2,6,7,3], [0,3,7,4], [1,5,6,2]
      ];
      
      containerFaces.forEach((face, idx) => {
        const corners3d = face.map(i => project3D(...containerCorners[i]));
        const avgZ = corners3d.reduce((sum, p) => sum + p[2], 0) / 4;
        const lighting = calculateLighting(idx, corners3d);
        faces.push({
          type: 'container',
          corners: corners3d,
          z: avgZ,
          color: `rgba(100, 150, 255, ${0.05 + lighting * 0.1})`,
          stroke: `rgba(100, 200, 255, ${0.3 + lighting * 0.3})`
        });
      });
      
      // Item faces with lighting
      j.placements.forEach((p, idx) => {
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
          
          // Calculate lighting for this face
          const lighting = calculateLighting(faceIdx, corners3d);
          const color = colorForSku(p.sku, lighting);
          
          faces.push({
            type: 'item',
            corners: corners3d,
            z: avgZ,
            color: color,
            stroke: 'rgba(0, 0, 0, 0.4)',
            sku: p.sku,
            faceIdx: faceIdx,
            lighting: lighting
          });
        });
      });
      
      // Sort faces by z-depth (back to front)
      faces.sort((a, b) => a.z - b.z);
      
      // Draw all faces with enhanced shadows and highlights
      faces.forEach(face => {
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(face.corners[0][0], face.corners[0][1]);
        for(let i = 1; i < face.corners.length; i++){
          ctx.lineTo(face.corners[i][0], face.corners[i][1]);
        }
        ctx.closePath();
        
        if(face.type === 'container'){
          // Container with glow effect
          ctx.strokeStyle = face.stroke;
          ctx.lineWidth = 2.5;
          ctx.shadowColor = face.stroke;
          ctx.shadowBlur = 8;
          ctx.stroke();
        } else {
          // Items with shadow and highlight
          ctx.shadowColor = 'rgba(0, 0, 0, 0.3)';
          ctx.shadowBlur = 8;
          ctx.shadowOffsetX = 2;
          ctx.shadowOffsetY = 2;
          ctx.fillStyle = face.color;
          ctx.fill();
          
          // Add subtle highlight on top
          if(face.lighting > 0.8) {
            ctx.shadowBlur = 0;
            ctx.shadowOffsetX = 0;
            ctx.shadowOffsetY = 0;
            ctx.fillStyle = 'rgba(255, 255, 255, 0.15)';
            ctx.fill();
          }
          
          ctx.strokeStyle = face.stroke;
          ctx.lineWidth = 1.5;
          ctx.shadowBlur = 0;
          ctx.shadowOffsetX = 0;
          ctx.shadowOffsetY = 0;
          ctx.stroke();
        }
        ctx.restore();
      });
      
      // Draw SKU labels with enhanced styling
      ctx.save();
      j.placements.forEach((p, idx) => {
        const x = p.position_mm[0] + p.size_mm[0]/2;
        const y = p.position_mm[1] + p.size_mm[1]/2;
        const z = p.position_mm[2] + p.size_mm[2] + 5;
        const [lx, ly, lz] = project3D(x, y, z);
        
        if(lz > 0 && p.size_mm[0] * scale > 30) { // Only draw if in front and item is large enough
          // Label background
          ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
          ctx.font = 'bold 11px Arial';
          ctx.textAlign = 'center';
          const textWidth = ctx.measureText(p.sku).width;
          ctx.fillRect(lx - textWidth/2 - 4, ly - 14, textWidth + 8, 18);
          
          // Label text with shadow
          ctx.shadowColor = 'rgba(0, 0, 0, 0.8)';
          ctx.shadowBlur = 3;
          ctx.fillStyle = '#ffffff';
          ctx.fillText(p.sku, lx, ly);
        }
      });
      ctx.restore();
      
      // Premium stats panel
      ctx.save();
      
      // Stats background with rounded corners effect
      const panelX = 15;
      const panelY = canvas.height - 100;
      const panelWidth = canvas.width - 30;
      const panelHeight = 85;
      const panelRadius = 12;
      
      ctx.shadowColor = 'rgba(0, 0, 0, 0.3)';
      ctx.shadowBlur = 15;
      ctx.shadowOffsetY = 5;
      
      // Draw rounded rectangle background
      ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
      ctx.beginPath();
      ctx.roundRect(panelX, panelY, panelWidth, panelHeight, panelRadius);
      ctx.fill();
      
      ctx.shadowBlur = 0;
      ctx.shadowOffsetY = 0;
      ctx.textAlign = 'left';
      
      // Container name header
      ctx.font = '600 15px Inter, Arial';
      const headerGradient = ctx.createLinearGradient(25, 0, 400, 0);
      headerGradient.addColorStop(0, '#60a5fa');
      headerGradient.addColorStop(1, '#a78bfa');
      ctx.fillStyle = headerGradient;
      ctx.fillText(`${j.shipping_company || 'Container'} ${j.container_name || ''}`.trim(), 25, canvas.height - 73);
      
      // Stats line 1
      ctx.font = '400 12px Inter, Arial';
      ctx.fillStyle = '#e5e7eb';
      ctx.fillText(`Dimensions: ${maxW}×${maxL}×${maxH}mm`, 25, canvas.height - 53);
      
      // Stats line 2
      ctx.fillText(`Items: ${j.placements.length} | Utilization: ${(j.utilization*100).toFixed(1)}%`, 25, canvas.height - 38);
      
      // Utilization bar
      const barX = 25;
      const barY = canvas.height - 25;
      const barWidth = 200;
      const barHeight = 10;
      
      ctx.fillStyle = 'rgba(255, 255, 255, 0.2)';
      ctx.fillRect(barX, barY, barWidth, barHeight);
      
      const utilPercent = Math.min(1, j.utilization);
      const barGradient = ctx.createLinearGradient(barX, 0, barX + barWidth, 0);
      barGradient.addColorStop(0, '#4fc3f7');
      barGradient.addColorStop(0.5, '#29b6f6');
      barGradient.addColorStop(1, '#03a9f4');
      ctx.fillStyle = barGradient;
      ctx.fillRect(barX, barY, barWidth * utilPercent, barHeight);
      
      ctx.fillStyle = '#e5e7eb';
      ctx.font = '400 11px Inter, Arial';
      ctx.fillText(`Price: ${(j.price_try || 0).toFixed(2)}₺ • Volume: ${(j.container_volume_cm3/1000).toFixed(1)}L`, barX + barWidth + 15, barY + 8);
      
      ctx.restore();
    };
    
    // Mouse controls with smooth interaction
    canvas.addEventListener('mousedown', (e) => {
      isDragging = true;
      canvas.style.cursor = 'grabbing';
      lastMouseX = e.clientX;
      lastMouseY = e.clientY;
    });
    
    canvas.addEventListener('mousemove', (e) => {
      if(isDragging){
        const deltaX = e.clientX - lastMouseX;
        const deltaY = e.clientY - lastMouseY;
        
        targetRotationY += deltaX * 0.01;
        targetRotationX += deltaY * 0.01;
        
        // Clamp rotation
        targetRotationX = Math.max(-Math.PI/2, Math.min(Math.PI/2, targetRotationX));
        
        lastMouseX = e.clientX;
        lastMouseY = e.clientY;
      }
    });
    
    canvas.addEventListener('mouseup', () => {
      isDragging = false;
      canvas.style.cursor = 'grab';
    });
    
    canvas.addEventListener('mouseleave', () => {
      isDragging = false;
      canvas.style.cursor = 'grab';
    });
    
    // Smooth zoom with mouse wheel
    canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
      targetScale *= zoomFactor;
      targetScale = Math.max(0.1, Math.min(5.0, targetScale));
    });
    
    // Optimized animation loop - render immediately then optimize
    let animationFrameId;
    let lastRenderTime = 0;
    const targetFPS = 45; // Balanced FPS for good quality and performance
    const frameInterval = 1000 / targetFPS;
    
    const animate = (currentTime = 0) => {
      if (!isVisible && !autoRotate && !isDragging) {
        // Pause animation when not visible and not interacting
        animationFrameId = requestAnimationFrame(animate);
        return;
      }
      
      const deltaTime = currentTime - lastRenderTime;
      
      if (deltaTime >= frameInterval) {
        // Only render if something has changed or auto-rotate is on
        const hasMovement = Math.abs(targetRotationX - rotationX) > 0.001 || 
                           Math.abs(targetRotationY - rotationY) > 0.001 || 
                           Math.abs(targetScale - scale) > 0.001 || 
                           autoRotate;
        
        if (hasMovement || isDragging) {
          render();
          lastRenderTime = currentTime;
        }
      }
      
      animationFrameId = requestAnimationFrame(animate);
    };
    
    // Intersection Observer for performance optimization (non-blocking)
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        isVisible = entry.isIntersecting;
      });
    }, { threshold: 0.1 });
    
    observer.observe(container);
    
    // Initial render and start animation immediately
    render();
    animate();
    
    // Cleanup on modal close
    window.addEventListener('beforeunload', () => {
      if(animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
    });
    
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
	
	# 🤖 ML-ENHANCED STRATEGY SELECTION
	try:
		# Get ML prediction for best strategy
		predicted_strategy, confidence, features = strategy_predictor.predict_strategy(products, containers)
		print(f"🤖 ML Prediction: {predicted_strategy} (confidence: {confidence:.2f})")
		
		# Try the ML-recommended strategy first
		packing_result = None
		if predicted_strategy == 'greedy':
			packing_result = pack_greedy_max_utilization(products, containers)
		elif predicted_strategy == 'best_fit':
			packing_result = pack_best_fit(products, containers)
		elif predicted_strategy == 'large_first':
			packing_result = pack_largest_first_optimized(products, containers)
		elif predicted_strategy == 'aggressive':
			packing_result = try_aggressive_partial_packing(products, containers)
		
		# If ML strategy fails or confidence is low, fallback to optimal multi-packing
		if not packing_result or confidence < 0.5:
			print(f"🔄 ML strategy failed or low confidence ({confidence:.2f} < 0.5), falling back to optimal multi-packing")
			packing_result = find_optimal_multi_packing(products, containers)
			
	except Exception as e:
		print(f"⚠️ ML prediction failed: {e}, using default strategy")
		# Fallback to original logic
		packing_result = find_optimal_multi_packing(products, containers)
	
	if not packing_result:
		# Calculate order characteristics
		total_volume = sum(p.width_mm * p.length_mm * p.height_mm for p in products) / 1000.0  # cm³
		largest_container = max(containers, key=lambda c: c.inner_w_mm * c.inner_l_mm * c.inner_h_mm) if containers else None
		available_volume = largest_container.inner_w_mm * largest_container.inner_l_mm * largest_container.inner_h_mm / 1000.0 if largest_container else 0
		utilization_ratio = total_volume / available_volume if available_volume > 0 else float('inf')
		
		# Try aggressive partial packing as last resort for:
		# 1. Orders larger than single container
		# 2. Orders with many items (>10)
		# 3. Orders with high utilization (>70%) that failed regular packing
		should_try_aggressive = (
			total_volume > available_volume or 
			len(products) > 10 or 
			utilization_ratio > 0.7
		)
		
		if should_try_aggressive:
			print(f"🔄 Trying aggressive partial packing (items: {len(products)}, volume: {total_volume:.1f}cm³, util: {utilization_ratio*100:.1f}%)")
			partial_result = try_aggressive_partial_packing(products, containers)
			if partial_result:
				packing_result = partial_result
			else:
				# Provide helpful error information
				largest_item_dims = max(products, key=lambda p: max(p.width_mm, p.length_mm, p.height_mm))
				error_msg = f"Unable to pack {len(products)} items (total volume: {total_volume:.1f}cm³, theoretical utilization: {utilization_ratio*100:.1f}%). "
				if largest_container:
					error_msg += f"Largest available container: {largest_container.box_id} ({available_volume:.1f}cm³ capacity). "
				
				if total_volume > available_volume * 3:  # Very large order
					error_msg += f"This order is exceptionally large ({total_volume/available_volume:.1f}x largest container). Consider splitting into smaller orders. "
				
				error_msg += f"Largest item: {largest_item_dims.sku} ({largest_item_dims.width_mm}x{largest_item_dims.length_mm}x{largest_item_dims.height_mm}mm)"
				
				raise HTTPException(status_code=400, detail=error_msg)
		else:
			# Regular error for small orders that truly can't pack
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
		
		# Add actual container dimensions to the result
		container_result.inner_w_mm = container.inner_w_mm
		container_result.inner_l_mm = container.inner_l_mm
		container_result.inner_h_mm = container.inner_h_mm
		
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
	
	# Create response with container dimensions for single container compatibility
	response = OrderPackResponse(
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
	
	# Add container dimensions for single container (for 3D visualization compatibility)
	if len(packing_result) == 1:
		response.inner_w_mm = first_container.inner_w_mm
		response.inner_l_mm = first_container.inner_l_mm
		response.inner_h_mm = first_container.inner_h_mm
	
	return response 


@app.get("/containers")
def list_containers(limit: int = 100):
    """List all available containers with their dimensions"""
    try:
        containers = load_containers_csv("data/container.csv")
        
        container_list = []
        for container in containers[:limit]:
            container_list.append({
                "box_id": container.box_id,
                "box_name": container.box_name,
                "shipping_company": container.shipping_company,
                "inner_w_mm": container.inner_w_mm,
                "inner_l_mm": container.inner_l_mm,
                "inner_h_mm": container.inner_h_mm,
                "max_weight_g": container.max_weight_g,
                "price_try": container.price_try,
                "material": container.material,
                "container_type": container.container_type
            })
        
        return container_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading containers: {str(e)}")


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


# Order Management Endpoints
@app.get("/orders", response_model=OrderListResponse)
def list_orders(status: Optional[str] = None, limit: int = 50, offset: int = 0):
    """List all orders with optional filtering"""
    try:
        orders = load_orders_csv("data/orders.csv", "data/order_items.csv")
        
        # Filter by status if provided
        if status:
            orders = [order for order in orders if order.status.lower() == status.lower()]
        
        # Apply pagination
        total_count = len(orders)
        orders = orders[offset:offset + limit]
        
        # Convert to API format
        api_orders = []
        for order in orders:
            api_items = [APIOrderItem(
                sku=item.sku,
                quantity=item.quantity,
                unit_price_try=item.unit_price_try,
                total_price_try=item.total_price_try
            ) for item in order.items]
            
            api_orders.append(OrderResponse(
                order_id=order.order_id,
                customer_name=order.customer_name,
                customer_email=order.customer_email,
                order_date=order.order_date,
                status=order.status,
                items=api_items,
                total_items=order.total_items,
                total_price_try=order.total_price_try,
                shipping_company=order.shipping_company,
                container_count=order.container_count,
                utilization_avg=order.utilization_avg,
                notes=order.notes
            ))
        
        return OrderListResponse(orders=api_orders, total_count=total_count)
    
    except FileNotFoundError:
        return OrderListResponse(orders=[], total_count=0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading orders: {str(e)}")


@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: str):
    """Get a specific order by ID"""
    try:
        orders = load_orders_csv("data/orders.csv", "data/order_items.csv")
        order = next((o for o in orders if o.order_id == order_id), None)
        
        if not order:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        
        api_items = [APIOrderItem(
            sku=item.sku,
            quantity=item.quantity,
            unit_price_try=item.unit_price_try,
            total_price_try=item.total_price_try
        ) for item in order.items]
        
        return OrderResponse(
            order_id=order.order_id,
            customer_name=order.customer_name,
            customer_email=order.customer_email,
            order_date=order.order_date,
            status=order.status,
            items=api_items,
            total_items=order.total_items,
            total_price_try=order.total_price_try,
            shipping_company=order.shipping_company,
            container_count=order.container_count,
            utilization_avg=order.utilization_avg,
            notes=order.notes
        )
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Orders database not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading order: {str(e)}")


@app.post("/orders", response_model=OrderResponse)
def create_order(request: CreateOrderRequest):
    """Create a new order"""
    try:
        # Generate unique order ID
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        # Convert API items to domain items
        items = [OrderItem(
            sku=item.sku,
            quantity=item.quantity,
            unit_price_try=item.unit_price_try,
            total_price_try=item.total_price_try
        ) for item in request.items]
        
        # Create order
        order = Order(
            order_id=order_id,
            customer_name=request.customer_name,
            customer_email=request.customer_email,
            order_date=datetime.now(),
            status="pending",
            items=items,
            notes=request.notes
        )
        
        # Save to CSV
        save_order_to_csv(order, "data/orders.csv", "data/order_items.csv")
        
        # Return API response
        api_items = [APIOrderItem(
            sku=item.sku,
            quantity=item.quantity,
            unit_price_try=item.unit_price_try,
            total_price_try=item.total_price_try
        ) for item in order.items]
        
        return OrderResponse(
            order_id=order.order_id,
            customer_name=order.customer_name,
            customer_email=order.customer_email,
            order_date=order.order_date,
            status=order.status,
            items=api_items,
            total_items=order.total_items,
            total_price_try=order.total_price_try,
            shipping_company=order.shipping_company,
            container_count=order.container_count,
            utilization_avg=order.utilization_avg,
            notes=order.notes
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating order: {str(e)}")


@app.put("/orders/{order_id}", response_model=OrderResponse)
def update_order(order_id: str, request: UpdateOrderRequest):
    """Update an existing order"""
    try:
        # Load existing orders
        orders = load_orders_csv("data/orders.csv", "data/order_items.csv")
        order = next((o for o in orders if o.order_id == order_id), None)
        
        if not order:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        
        # Update fields if provided
        if request.customer_name is not None:
            order.customer_name = request.customer_name
        if request.customer_email is not None:
            order.customer_email = request.customer_email
        if request.status is not None:
            order.status = request.status
        if request.notes is not None:
            order.notes = request.notes
        if request.items is not None:
            order.items = [OrderItem(
                sku=item.sku,
                quantity=item.quantity,
                unit_price_try=item.unit_price_try,
                total_price_try=item.total_price_try
            ) for item in request.items]
            # Recalculate totals
            order.total_items = sum(item.quantity for item in order.items)
            order.total_price_try = sum(item.total_price_try or 0 for item in order.items)
        
        # Save updated order
        save_order_to_csv(order, "data/orders.csv", "data/order_items.csv")
        
        # Return API response
        api_items = [APIOrderItem(
            sku=item.sku,
            quantity=item.quantity,
            unit_price_try=item.unit_price_try,
            total_price_try=item.total_price_try
        ) for item in order.items]
        
        return OrderResponse(
            order_id=order.order_id,
            customer_name=order.customer_name,
            customer_email=order.customer_email,
            order_date=order.order_date,
            status=order.status,
            items=api_items,
            total_items=order.total_items,
            total_price_try=order.total_price_try,
            shipping_company=order.shipping_company,
            container_count=order.container_count,
            utilization_avg=order.utilization_avg,
            notes=order.notes
        )
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Orders database not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating order: {str(e)}")


@app.delete("/orders/{order_id}")
def delete_order(order_id: str):
	"""Delete an order"""
	try:
		# Load existing orders
		orders = load_orders_csv("data/orders.csv", "data/order_items.csv")
		order = next((o for o in orders if o.order_id == order_id), None)
		
		if not order:
			raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
		
		# Remove from list and save
		orders = [o for o in orders if o.order_id != order_id]
		
		# Save all remaining orders
		import pandas as pd
		from pathlib import Path
		
		# Prepare data for saving
		orders_data = []
		items_data = []
		
		for order in orders:
			orders_data.append({
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
			})
			
			for item in order.items:
				items_data.append({
					'order_id': order.order_id,
					'sku': item.sku,
					'quantity': item.quantity,
					'unit_price_try': item.unit_price_try,
					'total_price_try': item.total_price_try
				})
		
		# Save to CSV
		orders_df = pd.DataFrame(orders_data)
		items_df = pd.DataFrame(items_data)
		
		orders_df.to_csv("data/orders.csv", index=False)
		items_df.to_csv("data/order_items.csv", index=False)
		
		return {"message": f"Order {order_id} deleted successfully"}
	
	except FileNotFoundError:
		raise HTTPException(status_code=404, detail="Orders database not found")
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Error deleting order: {str(e)}")


# 🤖 ML STRATEGY PREDICTION ENDPOINTS

@app.post("/predict-strategy")
def predict_packing_strategy(req: OrderPackRequest):
	"""
	🤖 Predict the optimal packing strategy for an order using ML
	
	Returns the recommended strategy, confidence score, and feature analysis
	"""
	try:
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
		
		# Get ML prediction
		predicted_strategy, confidence, features = strategy_predictor.predict_strategy(products, containers)
		
		# Get feature importance if model is available
		feature_importance = strategy_predictor.get_feature_importance()
		
		# Ensure all numeric values are JSON-serializable
		safe_features = {}
		for k, v in features.items():
			if isinstance(v, (int, float)):
				safe_features[k] = round(float(v), 3)
			else:
				safe_features[k] = v
		
		safe_feature_importance = {}
		for k, v in feature_importance.items():
			safe_feature_importance[k] = round(float(v), 3)
		
		return {
			"order_id": req.order_id,
			"predicted_strategy": predicted_strategy,
			"confidence": round(float(confidence), 3),
			"features": safe_features,
			"feature_importance": safe_feature_importance,
			"model_available": strategy_predictor.model is not None,
			"total_items": len(products),
			"unique_skus": len(set(p.sku for p in products)),
			"recommendation_reason": _get_strategy_explanation(predicted_strategy, features)
		}
		
	except Exception as e:
		import traceback
		print(f"❌ Predict strategy error: {e}")
		traceback.print_exc()
		raise HTTPException(status_code=500, detail=f"Strategy prediction failed: {str(e)}")


@app.post("/ml/train")
def train_ml_model(sample_size: int = 100):
	"""
	🎯 Train the ML strategy selector model using simulated data
	
	This endpoint generates training data and trains the XGBoost model
	"""
	try:
		# Load master data
		all_products = load_products_csv("data/products.csv")
		containers = load_containers_csv("data/container.csv")
		
		# Generate sample orders for training
		import random
		random.seed(42)
		
		sample_orders = []
		for i in range(sample_size):
			# Create random order with 1-20 items
			order_size = random.randint(1, 20)
			order_products = random.choices(all_products, k=order_size)
			sample_orders.append(order_products)
		
		# Generate training data
		print(f"🔄 Generating training data from {sample_size} sample orders...")
		training_data = strategy_predictor.generate_training_data(sample_orders, containers)
		
		# Train model
		print("🤖 Training ML model...")
		success = strategy_predictor.train_model(training_data)
		
		if success:
			# Get feature importance
			feature_importance = strategy_predictor.get_feature_importance()
			
			return {
				"success": True,
				"message": "ML model trained successfully",
				"training_samples": len(training_data),
				"feature_count": len(strategy_predictor.feature_names),
				"strategies": strategy_predictor.strategies,
				"feature_importance": {k: round(v, 3) for k, v in feature_importance.items()},
				"model_path": strategy_predictor.model_path
			}
		else:
			return {
				"success": False,
				"message": "Model training failed",
				"training_samples": len(training_data)
			}
			
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")


@app.get("/ml/status")
def get_ml_status():
	"""
	📊 Get ML model status and feature importance
	"""
	try:
		feature_importance = strategy_predictor.get_feature_importance()
		
		# Ensure all numeric values are JSON-serializable
		safe_feature_importance = {}
		for k, v in feature_importance.items():
			safe_feature_importance[k] = round(float(v), 3)
		
		return {
			"model_available": strategy_predictor.model is not None,
			"model_path": strategy_predictor.model_path,
			"feature_count": len(strategy_predictor.feature_names),
			"strategies": strategy_predictor.strategies,
			"feature_names": strategy_predictor.feature_names,
			"feature_importance": safe_feature_importance,
			"model_type": type(strategy_predictor.model).__name__ if strategy_predictor.model else None
		}
		
	except Exception as e:
		import traceback
		print(f"❌ ML status error: {e}")
		traceback.print_exc()
		raise HTTPException(status_code=500, detail=f"ML status check failed: {str(e)}")


def _get_strategy_explanation(strategy: str, features: Dict[str, float]) -> str:
	"""Generate human-readable explanation for strategy recommendation"""
	
	explanations = {
		'greedy': "Greedy strategy recommended for efficient single-container packing",
		'best_fit': "Best-fit strategy recommended to minimize waste and handle fragile items",
		'large_first': "Large-first strategy recommended for complex size distributions",
		'aggressive': "Aggressive multi-container strategy recommended for large orders"
	}
	
	base_explanation = explanations.get(strategy, "Strategy selected based on ML analysis")
	
	# Add specific reasons based on features
	reasons = []
	
	if features.get('utilization_potential', 0) > 1.2:
		reasons.append("high volume requires multiple containers")
	elif features.get('utilization_potential', 0) > 0.9:
		reasons.append("high utilization potential")
	
	if features.get('fragility_ratio', 0) > 0.3:
		reasons.append("high fragility ratio requires careful packing")
	
	if features.get('weight_ratio', 0) > 0.8:
		reasons.append("weight constraints are significant")
	
	if features.get('size_diversity', 0) > 10:
		reasons.append("high size diversity needs specialized handling")
	
	if features.get('hazmat_flag', 0) > 0:
		reasons.append("hazardous materials require special handling")
	
	if reasons:
		return f"{base_explanation} due to: {', '.join(reasons)}"
	
	return base_explanation
