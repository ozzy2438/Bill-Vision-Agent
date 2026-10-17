# Günlük kullanım arayüzü ve 3B açılış

17 Ekim 2026 (Australia/Melbourne). Mevcut Streamlit + FastAPI uygulaması korunarak arayüz yenilendi.

## Kullanıcı akışı

- **Ana sayfa:** siyah sahnede tam 360° silindir üzerinde 14 belge kartı. Kartlar mevcut kayıtlara bağlıdır; “İncelemeyi aç” gerçek belgeyi açar. Daha az kayıt varsa kalan kartlar açıkça temsili tanıtım olarak işaretlenir. Temsili kartlarda tutar veya doğrulama sonucu uydurulmaz.
- **Fatura yükle:** belirgin tek ana düğme, PDF/görüntü seçimi, isteğe bağlı sipariş bağlamı. İngilizce belge kapsamı, 10 MB / 5 sayfa sınırı görünür. Streamlit yükleme sınırı da 10 MB olarak ayarlandı.
- **İncelemeler:** arama, bekleyen/sonuçlanan filtreleri ve her kaydın yanında doğrudan açma düğmesi. Başlangıçta rastgele bir belge açılmaz.
- **Belge:** sıradaki işlem üstte; fatura görüntüsü yanında “Fatura bilgileri”, “Sipariş”, “Karar”. Alan adları Türkçeleştirildi. Kaynaklar, gerçek konum, kurallar/sürümler ve geçmiş açılabilir bölümlerde korunur.
- **Düzeltme:** gerekçeyle kaydetme mevcut API'yi çağırır. Kontroller ve önceki kararın geçersizliği görünür. O oturumda yapılan düzeltmenin sonucu otomatik açılır; tarihsel farklar ilk açılışı doldurmaz.

## Görsel bileşen

React, TypeScript ve Tailwind CSS yalnızca açılış bileşenindedir. Python bağımlılıkları, OCR/model hattı, şirket kuralları ve veritabanı şeması değişmedi. Derlenmiş bileşen aynı Streamlit sürecinden sunulur; CDN, yeni sunucu veya üretim çalışma bağımlılığı yoktur. [Bileşenin kaynak ve build bilgisi](../frontend/circular-slider/README.md).

Kart halkası gerçek CSS 3D geometrisi kullanır. Sürükleme, dokunmatik kaydırma, momentum, sürtünme, en yakına hizalama, karta tıklayarak öne getirme, önceki/sonraki ve klavye kontrolleri vardır. Otomatik dönüş duraklatılabilir; işletim sisteminin azaltılmış hareket tercihi uygulanır. 12 saniyelik sessiz video kullanıcı isteğiyle açılır; aynı anlatım metin olarak da sunulur.

## Uygulamalı doğrulama

- TypeScript kontrolü ve üretim bundle'ı tamamlandı.
- Chromium'da 14 kartın 3D dönüşü, masaüstü sürükleme/momentum/hizalama, kart seçimi, hover sırasında durma, ok/Home/End ve gerçek touch olaylarıyla yatay kaydırma kontrol edildi.
- 390 px görünümde yatay sayfa taşması yok; azaltılmış harekette otomatik dönüş kapalı.
- Instabox'taki gerçek uygulamada carousel kartı doğru belgeyi açtı; JavaScript veya Streamlit hatası görülmedi.
- İnceleme formları geçici veritabanı kopyasında gerçek API ile çalıştırıldı: düzeltme/kontrol farkı, gerekçesiz reddin engellenmesi, gerekçeli ret, sonraki düzeltmenin eski kararı geçersizleştirmesi, kullanıcı siparişinin belge alanından ayrı kalması ve onay engeli korundu. Kayıtlı tutar kanıtlarını kontrol etme de çalıştı; yeni çıkarım denemesi oluşmadı. Geçici API ve veritabanı kaldırıldı.

Canlı uygulamadaki 27 belgenin alanları ve toplam 103 geçmiş kaydı, değişiklik öncesiyle birebir aynı kaldı.

Yeni 25-fatura çıkarımı, eski üç demo veya yük testi çalıştırılmadı. Gerçek iPhone/Safari ve farklı kullanıcılarla kullanılabilirlik çalışması yapılmadı; ölçülmemiş FPS veya kullanım kolaylığı oranı iddia edilmiyor. Bu değişiklik arayüzü yeniler; önceki rapordaki şirket kaydı ve belirsiz fatura bilgisi eksiklerini kendiliğinden çözmez.

Makine tarafından kaydedilen kontrol sonuçları: [UI_REFRESH_OBSERVATIONS.json](UI_REFRESH_OBSERVATIONS.json).
