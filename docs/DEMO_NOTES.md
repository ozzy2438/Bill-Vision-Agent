# Üç kısa gösterim — gözlem notu

Çalıştırma: `2026-10-14T02:45:53.440961+11:00` (Australia/Melbourne). Komut: `uv run python -m scripts.run_demos`; çıkış kodu **0**.

| Gösterim | Gerçek gözlem |
|---|---|
| A | Docling + İngilizce Tesseract + yerel qwen2.5:7b, fatura toplamını 2000.00 AUD çıkardı. Sipariş 2000.00 AUD; fark 0.00. `ready_for_approval`; `demo-reviewer` aktörünün `approve` kararı veritabanında mevcut. |
| B | Aynı gerçek hat fatura toplamını 2200.00 AUD çıkardı. Aynı vergi bazındaki sipariş 2000.00 AUD; fark **200.00 AUD**. `TOTAL` kuralı fail, durum `needs_review`; belge kanıtı mevcut. |
| C | A'nın aynı baytları tekrar yüklendi. `duplicate=true`; önceki kayıt döndü ve kayıt sayısı değişmedi (**0 yeni kayıt**). |

A kaydı: `2948f13a-7300-4e99-b5b7-089bd1369627`. B kaydı: `e61672a6-a25c-4625-ac3a-21b54ca2042d`. C'nin döndürdüğü kayıt: `2948f13a-7300-4e99-b5b7-089bd1369627`.

Bu faturalar uygulamanın kendi sentetik PDF'leridir; FATURA'dan geldikleri iddia edilmez. Hazır çıkarım JSON'u veya mock model kullanılmadı. Her iki belgede de OCR çıktısı `storage/<kayıt-id>/ocr.json` içinde, alan kanıtları ve denetimler PostgreSQL'dedir. Sayfa/kutu bilgisi model tarafından üretilmedi.

## Toplam alanlarının gerçek kanıtı

- A: sayfa 1, `p1-e2`, alıntı `Total including tax: 2000.00 AUD`, kaynak `extracted`. Açıklama modu: `model_assisted`.
- B: sayfa 1, `p1-e2`, alıntı `Total including tax: 2200.00 AUD`, kaynak `extracted`. Açıklama modu: `model_assisted`.

## Kurulum gözlemleri ve sınırlar

- PostgreSQL şeması/seed, FastAPI ve Streamlit çalıştı. A'nın arayüzü belge önizlemesi, alanlar, kontrol durumu ve kaydedilmiş insan kararıyla hatasız oluşturuldu.
- `scripts/setup.sh` tekrar çalıştırıldığında mevcut veriler korundu; 122 Python paketi, model checksum'ları ve 25 farklı FATURA şablonu yeniden indirilmeden doğrulandı.
- `scripts/start.sh` eksik servisleri başlattı; tekrar çağrıldığında mevcut servisleri kullandı. Süreçler bağımsız oturumlarda başlatılır.
- İlk ağ denemelerinde model yönlendirme adresleri engelliydi; gerekli alan adlarıyla erişim sağlandı. İlk başlatma denemesinde süreç ömrü sorunu saptanıp düzeltildi. Yukarıdaki sonuçlar bu düzeltmelerden sonraki gerçek başarılı çalıştırmadır.
- 25 FATURA örneği hazırlandı; bunlar için bir çıkarım başarı oranı ölçülmedi. İki arka plan bağımsız iş vakası sayılmadı.
- PDF gösterimleri tamamlandı. PNG/JPEG kabulü uygulamada vardır; ayrı bir görüntü doğruluk/benchmark çalışması yapılmadı.
- Bu üç örnek genel doğruluk, hız, tasarruf veya müşteri başarısı iddiası değildir. Yeni bir bulut görevinde snapshot restorasyonu ayrıca denenmedi; ortam taslağının kaydı yayımlama anlamına gelmez.

Makine tarafından kaydedilen ayrıntılar: [demo-observations.json](demo-observations.json).

Sonraki aşama: mevcut FATURA belgeleri ve değişen inceleme akışının ayrı gözlemleri [REVIEW_FLOW_NOTES.md](REVIEW_FLOW_NOTES.md) ve [25 belge durum tablosunda](FATURA_REVIEW_STATUS.md) bulunur. Yukarıdaki A/B/C sonuçları tarihsel gözlemdir; bu geliştirme sırasında tekrar çalıştırılmadı. Güncel politika v1.1.0 ve şirket ipuçları v1.0.0'dır; eski kayıtların karar ve kaynak geçmişi korunur.
