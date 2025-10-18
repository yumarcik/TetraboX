# 📦 TetraboX Packaging Optimizer

## 🇹🇷 Türkçe

### 📋 Proje Açıklaması

**TetraboX Packaging Optimizer**, lojistik firmaları için geliştirilmiş, **makine öğrenmesi tabanlı** bir kutu yerleştirme sistemidir. Sipariş edilen ürünleri en verimli şekilde kargo kutularına yerleştirerek **maksimum alan kullanımı** ve **minimum maliyet** sağlar.

### ✨ Özellikler

- 🎯 **%80+ Verimlilik Hedefi**: Kutu kullanım oranını maksimize eder
- 💰 **Maliyet Optimizasyonu**: En uygun fiyatlı kutu kombinasyonunu seçer
- 📊 **Multi-Container Packing**: Büyük siparişleri birden fazla kutuya optimal şekilde böler
- 🔄 **3D Rotasyon Desteği**: Ürünleri 6 farklı yönde döndürerek en iyi yerleşimi bulur
- 🌐 **API-First Tasarım**: RESTful API ile kolay entegrasyon
- 🎨 **İnteraktif UI**: 3D görselleştirme ve sipariş yönetimi
- 📈 **Akıllı Algoritma**: Utilization, maliyet ve ürün sayısını dengeleyen scoring sistemi

### 🚀 Kurulum

1. **Python 3.11+** yükleyin
2. Bağımlılıkları kurun:
```bash
pip install -r requirements.txt
```
3. Serveri başlatın:
```bash
python main.py
```
4. Tarayıcıda açın: http://localhost:8000

### 📊 Veri Formatları

#### Products.csv
```csv
sku;category;brand;model;variant;width_cm;length_cm;height_cm;weight_kg;fragile;package_type;hazard_class;extra_package;extra_width_cm;extra_length_cm;extra_price_usd;extra_type
ADID-03A4CF;Shoes;Adidas;Superstar;Red 36;28,1;20,1;13,0;0,744;False;kraft_envelope;Aerosol-2;False;34.3;24.6;18.25;double_carton
```

#### Container.csv
```csv
box_name,width_cm,length_cm,height_cm,price,shipping_company,Available Products,Stok,boxes_id,is_2d_only,volume_cm3,box_type,max_weight_kg
Micro,15.0,15.0,15.0,12.06,Yurtici,,50,1,False,3375.0,Box,5.0
```

#### Orders.csv
```csv
order_id,customer_name,customer_email,order_date,total_items,total_price_try,shipping_company,container_count,utilization_avg,notes
ORD-001,John Doe,john.doe@email.com,2024-01-15 10:30:00,3,125.5,Yurtici,2,0.82,Standard delivery
```

### 🔧 API Endpoints

#### POST `/pack/order` - Sipariş Paketleme
```json
{
  "order_id": "ORD-001",
  "items": [
    {"sku": "SOFT-123", "quantity": 2},
    {"sku": "PHIL-456", "quantity": 1}
  ]
}
```

**Yanıt:**
```json
{
  "success": true,
  "containers": [
    {
      "container_id": "Yurtici-L",
      "container_name": "L",
      "shipping_company": "Yurtici",
      "utilization": 0.82,
      "placements": [...]
    }
  ],
  "total_price": 65.30,
  "total_items": 3
}
```

#### GET `/skus` - Mevcut SKU Listesi
Tüm ürün kodlarını ve detaylarını döner.

#### GET `/orders` - Sipariş Yönetimi
Mevcut siparişleri listeler ve yönetir.

#### POST `/predict-strategy` - ML Strateji Tahmini
Makine öğrenmesi ile optimal paketleme stratejisini tahmin eder.

#### POST `/ml/train` - Model Eğitimi
ML modellerini yeniden eğitir.

#### GET `/ml/status` - ML Model Durumu
Mevcut ML model durumunu ve performansını gösterir.

### 🎯 Algoritma Detayları

#### 3D Bin Packing
- **Largest-First Sorting**: Büyük ürünler önce yerleştirilir
- **6-Way Rotation**: Her ürün 6 farklı yönde denenır
- **Conflict Detection**: Çakışma kontrolü ile güvenli yerleşim
- **Fitness Scoring**: Alt köşe, stabilite ve alan kullanımı optimize edilir

#### Multi-Container Strategy
- **Greedy Max Utilization**: Her kutuyu maksimum doldurmaya odaklanır
- **Largest-First Optimized**: Büyük kutulardan başlayarak verimli dağıtım
- **Best-Fit**: Minimum boşluk bırakacak kutu seçimi
- **Cost Optimization**: En düşük toplam maliyetli strateji seçilir

#### 🤖 Makine Öğrenmesi Strateji Seçici
- **XGBoost/RandomForest**: Ensemble modeller ile strateji tahmini
- **19 Özellik Mühendisliği**: Sipariş karakteristikleri, konteyner ilişkileri, fiyat özellikleri
- **Akıllı Önbellekleme**: Anlık tahminler için hızlı erişim
- **Hafif Ensemble Modeller**: Performans ve doğruluk dengesi
- **Kural Tabanlı Fallback**: ML başarısız olduğunda güvenli geri dönüş

#### 🛡️ Ürün Uyumluluk ve Güvenlik
- **Kategori Bazlı Kurallar**: Elektronik, sıvı, kırılgan, tehlikeli madde kategorileri
- **Güvenli Paketleme**: Uyumsuz ürün kombinasyonlarını engeller
- **Kısıt Kontrolü**: Ağırlık, boyut ve tehlike sınıfı kontrolleri

### 🏗️ Modüler Yapı

```
src/
├── models.py              # Veri modelleri (Product, Container, Placement)
├── schemas.py             # API şemaları (Pydantic)
├── io.py                  # CSV okuma ve normalizasyon
├── packer.py              # 3D packing algoritmaları
├── safe_packer.py         # Güvenli paketleme kuralları
├── compatibility.py       # Ürün uyumluluk kontrolü
├── ml_strategy_selector.py # ML strateji seçici
├── server.py              # FastAPI uygulaması ve UI
├── validate.py            # Veri doğrulama araçları
└── localization.js         # Çoklu dil desteği
```

### 🧪 Test ve Doğrulama

CSV verilerini kontrol edin:
```bash
python -m src.validate --products data/products.csv --containers data/container.csv
```

### 📈 Performans Hedefleri

- **Utilization**: Minimum %80 kutu doluluk oranı
- **Cost Efficiency**: Optimal fiyat/performans dengesi
- **Processing Time**: Saniyeler içinde sonuç
- **Success Rate**: %95+ başarılı paketleme oranı

---

## 🇺🇸 English

### 📋 Project Description

**TetraboX Packaging Optimizer** is a **machine learning-based** box placement system designed for logistics companies. It efficiently places ordered items into cargo boxes to achieve **maximum space utilization** and **minimum cost**.

### ✨ Features

- 🎯 **80%+ Efficiency Target**: Maximizes container utilization rates
- 💰 **Cost Optimization**: Selects the most cost-effective container combinations
- 📊 **Multi-Container Packing**: Optimally splits large orders across multiple containers
- 🔄 **3D Rotation Support**: Rotates items in 6 different orientations for optimal placement
- 🌐 **API-First Design**: Easy integration with RESTful API
- 🎨 **Interactive UI**: 3D visualization and order management
- 📈 **Smart Algorithm**: Scoring system that balances utilization, cost, and item count

### 🚀 Installation

1. Install **Python 3.11+**
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Start the server:
```bash
python main.py
```
4. Open in browser: http://localhost:8000

### 📊 Data Formats

#### Products.csv
```csv
sku;category;brand;model;variant;width_cm;length_cm;height_cm;weight_kg;fragile;package_type;hazard_class;extra_package;extra_width_cm;extra_length_cm;extra_price_usd;extra_type
ADID-03A4CF;Shoes;Adidas;Superstar;Red 36;28,1;20,1;13,0;0,744;False;kraft_envelope;Aerosol-2;False;34.3;24.6;18.25;double_carton
```

#### Container.csv
```csv
box_name,width_cm,length_cm,height_cm,price,shipping_company,Available Products,Stok,boxes_id,is_2d_only,volume_cm3,box_type,max_weight_kg
Micro,15.0,15.0,15.0,12.06,Yurtici,,50,1,False,3375.0,Box,5.0
```

#### Orders.csv
```csv
order_id,customer_name,customer_email,order_date,total_items,total_price_try,shipping_company,container_count,utilization_avg,notes
ORD-001,John Doe,john.doe@email.com,2024-01-15 10:30:00,3,125.5,Yurtici,2,0.82,Standard delivery
```

### 🔧 API Endpoints

#### POST `/pack/order` - Order Packing
```json
{
  "order_id": "ORD-001",
  "items": [
    {"sku": "SOFT-123", "quantity": 2},
    {"sku": "PHIL-456", "quantity": 1}
  ]
}
```

**Response:**
```json
{
  "success": true,
  "containers": [
    {
      "container_id": "Yurtici-L",
      "container_name": "L",
      "shipping_company": "Yurtici",
      "utilization": 0.82,
      "placements": [...]
    }
  ],
  "total_price": 65.30,
  "total_items": 3
}
```

#### GET `/skus` - Available SKU List
Returns all product codes and details.

#### GET `/orders` - Order Management
Lists and manages existing orders.

#### POST `/predict-strategy` - ML Strategy Prediction
Predicts optimal packing strategy using machine learning.

#### POST `/ml/train` - Model Training
Retrains ML models.

#### GET `/ml/status` - ML Model Status
Shows current ML model status and performance.

### 🎯 Algorithm Details

#### 3D Bin Packing
- **Largest-First Sorting**: Large items are placed first
- **6-Way Rotation**: Each item is tried in 6 different orientations
- **Conflict Detection**: Safe placement with collision control
- **Fitness Scoring**: Optimizes bottom-corner placement, stability, and space usage

#### Multi-Container Strategy
- **Greedy Max Utilization**: Focuses on maximally filling each container
- **Largest-First Optimized**: Efficient distribution starting with large containers
- **Best-Fit**: Selects containers that minimize wasted space
- **Cost Optimization**: Chooses the lowest total cost strategy

#### 🤖 Machine Learning Strategy Selector
- **XGBoost/RandomForest**: Ensemble models for strategy prediction
- **19 Feature Engineering**: Order characteristics, container relationships, price features
- **Smart Caching**: Instant predictions with intelligent caching
- **Lightweight Ensemble Models**: Performance and accuracy balance
- **Rule-based Fallback**: Safe fallback when ML fails

#### 🛡️ Product Compatibility and Safety
- **Category-based Rules**: Electronics, liquids, fragile, hazardous material categories
- **Safe Packing**: Prevents incompatible product combinations
- **Constraint Control**: Weight, size, and hazard class controls

### 🏗️ Modular Architecture

```
src/
├── models.py              # Data models (Product, Container, Placement)
├── schemas.py             # API schemas (Pydantic)
├── io.py                  # CSV reading and normalization
├── packer.py              # 3D packing algorithms
├── safe_packer.py         # Safe packing rules
├── compatibility.py       # Product compatibility checks
├── ml_strategy_selector.py # ML strategy selector
├── server.py              # FastAPI application and UI
├── validate.py            # Data validation tools
└── localization.js         # Multi-language support
```

### 🧪 Testing and Validation

Check CSV data:
```bash
python -m src.validate --products data/products.csv --containers data/container.csv
```

### 📈 Performance Targets

- **Utilization**: Minimum 80% container fill rate
- **Cost Efficiency**: Optimal price/performance balance
- **Processing Time**: Results within seconds
- **Success Rate**: 95%+ successful packing rate

### 🛠️ Technology Stack

- **Backend**: FastAPI, Python 3.11+
- **Data Processing**: Pandas, Pydantic, NumPy
- **Machine Learning**: XGBoost, LightGBM, RandomForest, Scikit-learn
- **Algorithm**: Custom 3D Bin Packing with multi-strategy optimization
- **Advanced Algorithms**: Genetic algorithms, Multi-objective optimization
- **Frontend**: Vanilla JavaScript, HTML5 Canvas
- **Visualization**: Custom 3D isometric rendering
- **Smart Caching**: ML prediction caching for instant responses

### 📚 Usage Examples

#### Simple Order
```bash
curl -X POST http://localhost:8000/pack/order \
  -H "Content-Type: application/json" \
  -d '{"order_id":"TEST-1","items":[{"sku":"SOFT-123","quantity":1}]}'
```

#### Multi-Item Order
```javascript
const order = {
  order_id: "BULK-001",
  items: [
    {sku: "SOFT-123", quantity: 5},
    {sku: "PHIL-456", quantity: 3},
    {sku: "ELEC-789", quantity: 2}
  ]
};
```

### 🔮 Future Roadmap

- 🤖 **Machine Learning Integration**: ML-based placement prediction
- 🔐 **Authentication**: User management and API keys
- 📱 **Mobile App**: Native mobile interface
- 🌍 **Multi-language**: Additional language support
- 📊 **Analytics Dashboard**: Packing performance metrics
- 🚚 **Shipping Integration**: Direct carrier API connections
