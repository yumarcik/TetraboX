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
sku,brand,model,variant,width_mm,length_mm,height_mm,weight_g
SOFT-123,SoftBrand,Model1,Variant1,230,192,57,450
```

#### Container.csv
```csv
box_id,box_name,shipping_company,inner_w_mm,inner_l_mm,inner_h_mm,max_weight_g,price_try
1,Micro,Yurtici,180,120,50,2000,15.50
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

### 🏗️ Modüler Yapı

```
src/
├── models.py      # Veri modelleri (Product, Container, Placement)
├── schemas.py     # API şemaları (Pydantic)
├── io.py          # CSV okuma ve normalizasyon
├── packer.py      # 3D packing algoritmaları
├── server.py      # FastAPI uygulaması ve UI
└── validate.py    # Veri doğrulama araçları
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
sku,brand,model,variant,width_mm,length_mm,height_mm,weight_g
SOFT-123,SoftBrand,Model1,Variant1,230,192,57,450
```

#### Container.csv
```csv
box_id,box_name,shipping_company,inner_w_mm,inner_l_mm,inner_h_mm,max_weight_g,price_try
1,Micro,Yurtici,180,120,50,2000,15.50
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

### 🏗️ Modular Architecture

```
src/
├── models.py      # Data models (Product, Container, Placement)
├── schemas.py     # API schemas (Pydantic)
├── io.py          # CSV reading and normalization
├── packer.py      # 3D packing algorithms
├── server.py      # FastAPI application and UI
└── validate.py    # Data validation tools
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
- **Data Processing**: Pandas, Pydantic
- **Algorithm**: Custom 3D Bin Packing with multi-strategy optimization
- **Frontend**: Vanilla JavaScript, HTML5 Canvas
- **Visualization**: Custom 3D isometric rendering

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

---

### 📞 Support

For questions or issues:
- 📧 Email: support@tetrabox.com
- 📖 Documentation: http://localhost:8000/docs
- 🐛 Issues: GitHub Issues

### 📄 License

MIT License - see LICENSE file for details.