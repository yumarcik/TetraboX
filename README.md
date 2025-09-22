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
cd TetraBoX
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
python -m packing_optimizer --products data/products_final.csv --boxes data/boxes.xlsx
uvicorn api.main:app --reload
```

5. Tarayıcı veya Postman üzerinden API’yi test edin:

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


## Dosya Yapısı
```bash
TetraBoX/
├── api/
│   └── main.py              # FastAPI uygulaması
├── packing_optimizer/
│   └── packing_optimizer.py # Kutu atama fonksiyonları
├── data/
│   ├── products_final.csv
│   └── boxes_final.xlsx
├── requirements.txt
└── README.md
```
