# Farklı faturalarla inceleme — uygulamalı gözlem

Mevcut kod, README ve DEMO_NOTES incelendi. SHA-256 tekrar kontrolü, kullanıcı PO bağlamı, alan düzeltmesi, yeniden değerlendirme, inceleme geçmişi ve yerel karar zaten vardı; korundu. Eksikler, alan anlamını gözeten tutar kanıtı, sürümlü şirket ipuçları, görünür inceleme listesi ve düzeltme sonrası kontrol farklarıydı.

Yeni yapı `company_context.yaml` v1.0.0 ve mevcut politika dosyaları v1.1.0'dır. İpuçları eksik değer üretmez veya kontrol atlatmaz. Onaylı adlar yalnızca mevcut demo tedarikçisinin doğrulanmış kaydını içerir. Yeni FATURA şirket ilişkileri oluşturulmadı. Model çıktısında tutar, etiket ve para biriminin birleştirilmesi gözlenince sayısal alanların JSON şeması daraltıldı; önce işlenmiş belgeler bu nedenle yeniden OCR/model hattına verilmedi.

2026-10-14 tarihinde Streamlit'in gerçek uygulama çalıştırıcısı (`AppTest`) üzerinden, gerçek API ve PostgreSQL kullanılarak kısa kontrol yapıldı. Ayrı test paketi, mock model veya yeni belge oluşturulmadı. Eski A/B/C gösterimleri tekrarlanmadı.

Kayıt: `c7e524b4-251e-4e96-ac27-77caa83dc940`, `Template2_Instance195.jpg`.

- Belge ve inceleme listesi hatasız açıldı; bekleme nedeni ve gereken işlem gösterildi.
- Yerel ret sonrası, orijinal görüntünün alt sağındaki `TOTAL : 732.39 $` okunarak toplam `732.39` düzeltildi. Para birimi `$` üzerinden uydurulmadı.
- Kaynak `human_corrected` oldu; önceki OCR metni/konumu korundu. REQUIRED bulgusundaki eksik toplam kaldırıldı; EVIDENCE bulgusundaki toplam uyarısı kaldırıldı. Diğer eksikler nedeniyle kontrol durumu `needs_review` kaldı.
- Eski ret kararı geçersizleşti, kayıt tekrar bekleyen listeye geçti; uyarı ve önce/sonra kontrol tablosu görüntülendi.
- Eksik para birimi, vergi temeli ve onaylı şirket/sipariş bağlamı gerekçesiyle yeni yerel ret kaydedildi. İnceleme `closed`, karar `reject` oldu; düzeltmenin kontrol farkları kaybolmadı.
- Bütün adımlar mevcut `review_events` geçmişine yazıldı. OCR/model bu kontrol için yeniden çalıştırılmadı. Arayüzde sıfır uygulama istisnası görüldü.

Ayrıntı: [review-flow-observation.json](review-flow-observation.json). Bu gözlem yalnızca değişen kullanıcı akışını doğrular; çıkarım doğruluğu, kapasite veya tasarruf ölçümü değildir.

25 FATURA belgesinin nihai işleme durumları [FATURA_REVIEW_STATUS.md](FATURA_REVIEW_STATUS.md) içinde, alanlar/adaylar/kaynaklar ve kural sürümleri [FATURA_REVIEW_STATUS.json](FATURA_REVIEW_STATUS.json) içindedir. İlk uygulama düzenlemelerinde saklı OCR/model çıktısına kanıt kontrolleri tekrar uygulandı; bu, ikinci bir çıkarım değildir. İlk başarısız alanlar ve değişikliklerin geçmişi korunmuştur.

Somut sınır: Şirket veritabanında yalnızca sentetik demo tedarikçisi ve siparişi var. Farklı FATURA tedarikçileri için onaylı kimlik/sipariş kaydı olmadan eşleşme veya onay üretilemez. Belgedeki eksik para birimi, belirsiz tarih, eksik vergi temeli ve OCR/model hataları kullanıcı incelemesi ya da tedarikçiden açıklama gerektirir. Çözülemeyen belge yerel gerekçeli ret ile sonuçlandırılabilir.

## Tamamlanan 25 belge

25 seçili SHA-256 kaydının her birinde tam **bir** `processing_started` olayı ve tamamlanmış sonuç doğrulandı. Etiket JSON'ları çıkarımda kullanılmadı. 25 kaydın kontrol durumu `needs_review`; bunlardan biri yukarıdaki uygulamalı kontrolde yerel `reject` kararıyla sonuçlandı, 24'ü karar bekliyor. İşleme hatası 0; alan/kanıt uyarısı bulunan belge 23.

Güncel alan eksikleri: 17 belgede toplam, 11 belgede para birimi, 14 belgede tarih eksik veya belirsiz. Vergi temeli 25 belgede de eksik; onaylı sipariş eşleşmesi 25 belgede de yok. Bunlar mevcut uygulama kayıtlarının durum sayılarıdır; doğruluk yüzdesi değildir. Başarısız alan adayları ve kaynak parçaları saklandı; insan doğrulaması gerekir.

Son kontrol: API bileşenleri hazır, arayüz sağlık isteği HTTP 200. A/B kayıtlarının revizyonları korunmuştur; A'nın önceki onayı ve belgeden gelen PO kaynağı görünür. Python derleme kontrolü ve değişikliklerde boşluk denetimi geçti. Yeni test paketi veya benchmark oluşturulmadı.
