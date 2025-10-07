# TetraBoX Packing API

TetraBoX, e-ticaret veya lojistik sistemlerindeki ürünleri kutulara otomatik olarak yerleştiren bir Python ve FastAPI tabanlı uygulamadır. Kullanıcılar basket ID vererek hangi kutulara hangi ürünlerin yerleştiğini görebilir.

---

## Özellikler

- **Basket ID bazlı kutu ataması:** Her sepet için ürünleri uygun kutulara otomatik olarak yerleştirir.
- **GET & POST endpointleri:** API üzerinden basket ID sorgulama imkanı.
- **Web form:** Tarayıcı üzerinden basket ID girip sonuçları görebilme.
- **Uygun kutu seçimi:** Sepetteki toplam hacim ve ağırlığa göre en küçük kutuyu seçer.
- **MULTI_BOX_NEEDED:** Eğer sepet bir kutuya sığmazsa ürünleri ayrı kutulara ayırır.

---

## Kurulum

1. Repo'yu klonlayın ve dizine geçin:

```bash
git clone <repository_url>
cd TetraboX-chore-cli-and-logging
```

2. Sanal ortam oluşturun ve aktif edin (opsiyonel ama tavsiye edilir):
```bash
python -m venv tetrabox
source tetrabox/bin/activate   # Mac/Linux
tetrabox\Scripts\activate      # Windows
```

3. Gerekli kütüphaneleri yükleyin:
```bash
pip install -r requirements.txt
```

4. Uygulamayı çalıştırın:
```bash
python -m packing_optimizer --products data/products_final.csv --boxes data/boxes_final.xlsx
```

5. API'yi çalıştırın (opsiyonel, güncelleme gerektirir):
```bash
uvicorn api.main:app --reload
```

6. Tarayıcı veya Postman üzerinden API'yi test edin:

- GET ile tarayıcıdan test:
```bash
http://127.0.0.1:8000/pack?basket_id=2000
```

- POST ile API testi (Postman veya curl):
```bash
curl -X POST "http://127.0.0.1:8000/pack" \
     -H "Content-Type: application/json" \
     -d '{"basket_id": 2000}'
```

- Tarayıcı üzerinden form ile test:
```bash
http://127.0.0.1:8000/pack_form
```

---

## Güncel Bilgiler ve Kullanım

### CLI (Önerilen) Kullanım

`packing_optimizer` paketinin CLI'ı `__main__.py` üzerinden çalışır ve ürün ile kutu dosya yollarını alır. Çalıştırma örneği:

```bash
python -m packing_optimizer --products data/products_final.csv --boxes data/boxes_final.xlsx
```

- Çalışma sonunda çıktı CSV dosyası `packing_optimizer/data/all_baskets_details.csv` konumuna yazılır.
- Loglar standart çıktıya yazılır.

### Girdi Dosyaları

- `products_final.csv` beklenen temel sütunlar (örnek): `product_id, category, brand, model, variant, width_cm, length_cm, height_cm_filled, weight_kg, fragile_flag, package_type, hazard_class, requires_special_handling, extra_width_cm, extra_length_cm, extra_type, quantity, basket_id, customer_id`.
- `boxes_final.xlsx` beklenen temel sütunlar (örnek): `box_name, width_cm, length_cm, height_cm, shipping_company, price, Available Products, Stok`.

Bu sütun adları `packing_optimizer/core.py` içindeki `load_products_data()` ve `load_boxes_data()` fonksiyonlarında kullanılmaktadır.

### Üretilen Çıktılar

- `packing_optimizer/data/all_baskets_details.csv` dosyası her sepet için seçilen kargo firması, kutu sayısı, elektronik/elektronik olmayan kutu sayıları, toplam maliyet ve her kutudaki ürün kimliklerini içerir.

### API Durumu (Deneysel)

- `api/main.py` şu an `assign_boxes_to_baskets` isimli bir fonksiyonu `packing_optimizer.packing_optimizer` içinden import etmeye çalışmaktadır; bu fonksiyon/mevcut modül yapısı repoda bulunmamaktadır. Yeni çekirdek mantık `packing_optimizer/core.py` içerisindedir.
- API'yi çalıştırmadan önce `api/main.py` dosyasının `core.py`'e göre güncellenmesi gerekir. Aksi halde `uvicorn api.main:app --reload` hatayla sonuçlanabilir.
- API'yi kullanmak istiyorsanız, önce CLI ile algoritmayı entegre edecek şekilde `api/main.py`'yi revize edin ya da bizimle iletişime geçin; gerekli düzenlemeleri yapabiliriz.

### Proje Yapısı (Güncel)

```bash
TetraboX-chore-cli-and-logging/
├── api/
│   └── main.py                 # FastAPI uygulaması (güncellenmesi gerekiyor)
├── packing_optimizer/
│   ├── __main__.py             # CLI giriş noktası (argparse: --products, --boxes)
│   ├── core.py                 # Ana optimizasyon ve veri yükleme mantığı
│   ├── ml_train.py, ml_predict.py, ml_helpers.py, ml_dataset.py
│   └── data/
│       └── all_baskets_details.csv  # CLI çıktısı
├── notebooks/
│   ├── boxes_dataset_update.py
│   └── products_dataset_update.py
├── data/                       # Girdi dosyaları (örnek: products_final.csv, boxes_final.xlsx)
├── requirements.txt
└── README.md
```

### Bilinen Gereksinimler

- `requirements.txt`: `fastapi`, `uvicorn`, `pandas`, `openpyxl`
- Kodda `numpy` da kullanılıyor. Ortamınızda yoksa: `pip install numpy`

---

## SSS

- **Neden tek kargo firması tercihi var?** `core.py` içindeki `find_best_shipping_company()` tüm siparişi tek firmayla göndermeye öncelik verir; mümkün değilse `optimize_packaging()` ile karışık (MIXED) stratejisine düşer.
- **Elektronik ürünler neden gruplandırılıyor?** `ElectronicsTogetherPacker` elektronik ürünleri birlikte paketlemeye çalışır, hacim/ağırlık limitleri aşılırsa bölerek birden fazla kutu kullanır.
