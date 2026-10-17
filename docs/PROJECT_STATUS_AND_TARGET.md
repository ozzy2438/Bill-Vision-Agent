# Amaç, mevcut durum ve üretime geçiş standardı

Güncelleme — 17 Ekim 2026: Instabox kurulumu ve 17 toplam belirsizliğinin 12’sinin giderilmesi [güncel sonuç notunda](AMOUNT_REVALIDATION_NOTES.md) yer alıyor. Aşağıdaki süre ölçümleri ve önceki durum, ilk işleme çalışmasının tarihsel kaydıdır.


Değerlendirme: 15 Ekim 2026, Australia/Melbourne. Kaynaklar: mevcut kod, README, inceleme kayıtları, FATURA durum raporu ve yerel model logları. Bu çalışma yeni fatura/model çalıştırmaz; mevcut kayıtları inceler. Aşağıdaki hedef mimari henüz uygulanmış değildir.

## Ürün amacı

Faturayı yükleyen kullanıcı için tedarikçi, tarih, tutar, vergi ve sipariş bilgilerini belge kanıtıyla çıkarmak; şirketin onaylı kayıt ve kurallarına göre kontrol etmek; belirsizliği açıklamak; gerekli insan düzeltmesi ve onay/ret kararını izlenebilir biçimde sonuçlandırmak. Amaç elle okuma ve kontrol işini azaltmaktır.

Base64.ai benzeri ticari belge işleme kapasitesine ulaşmak daha geniş bir hedeftir. Bugünkü teslim, tek kullanıcılı ve sentetik verilerle çalışan bir inceleme MVP'sidir. Akışın tamamlanması, çıkarım kalitesinin veya ticari kapasitenin kanıtlandığı anlamına gelmez. Ürün hedefi için sayısal bir tamamlanma yüzdesi hesaplanmadı.

## Yapılanlar ve kullanılan teknikler

| İşlev | Uygulama |
|---|---|
| Arayüz | Streamlit: belge görüntüsü, alan/kanıt, bekleyen işler, sonraki işlem, düzeltme ve karar |
| Uygulama servisi | Python + FastAPI: yükleme, çıkarım koordinasyonu, kural değerlendirme, dışa aktarma |
| Belge okuma | Docling + İngilizce Tesseract OCR; sayfa ve gerçek konum bilgisi |
| Alan çıkarımı | Ollama üzerinde yerel Qwen2.5:7b; JSON Schema ve Pydantic ile çıktı yapısı denetimi |
| Kanıt ve iş kuralları | Alıntı, etiket ve aynı satır bağlamı denetimi; sürümlü YAML politika/şirket ipuçları; Decimal ile tutar karşılaştırma |
| Kayıt ve geçmiş | PostgreSQL; mevcut review_events içinde düzeltme, yeniden kontrol ve yerel karar; dosyalar yerel storage içinde |
| Tekrar koruması | SHA-256 ile aynı dosyayı tekrar işleme almama; doğrulanmış tedarikçi/fatura kimliği kontrolü |
| Çalışma ortamı | Codex ortamındaki tek Linux makinesi; 4 CPU kotası, kurulum kaydına göre 32 GiB RAM, GPU kullanmayan model çalıştırması; PostgreSQL Docker Compose içinde |

Fatura yükleme ve A/B/C gösterimleri önceden tamamlandı. Son aşamada şirket ipuçları, alan anlamını denetleyen kanıtlar, inceleme listesi ve kontrol farkları eklendi. Düzeltme önceki kararı geçersizleştiriyor; yeni karar mevcut geçmişe yazılıyor. Yeni model, fine-tuning, çoklu agent, bulut ölçekleme veya ödeme bağlantısı eklenmedi.

## 25 belge bize ne gösterdi?

25 seçili sentetik FATURA belgesinin her birinde bir işleme denemesi var. 24 kayıt inceleme bekliyor; biri arayüzün uygulamalı kontrolünde gerekçeli ret ile kapatıldı. İşleme hatası yok; 23 belgede alan/kanıt uyarısı var. Bu nedenle HTTP/işlem başarısını kullanılabilir, doğru çıkarımla eşitlemek mümkün değil.

17 toplam alanı eksik/belirsiz olarak tutulmuş. Bunların tamamında model bir aday üretmiş; adaylar şu denetimlerde reddedilmiş:

| Toplam alanını boş bıraktıran kayıtlı neden | Belge |
|---|---:|
| Kanıt kimliği veya OCR içinde doğrulanamayan alıntı | 11 |
| Sayısal biçim | 2 |
| Sayının atıf yapılan metinde bulunmaması | 1 |
| Toplam etiketi ile tutar ilişkisinin belirsizliği | 3 |

Bu, 17 belgenin üzerinde toplam yazmadığı anlamına gelmez. Adayların doğru olup olmadığı bu sayılardan çıkarılamaz; OCR, model çıktısı ve kanıt ilişkisindeki sorunlar ayrıştırılmalıdır. Mevcut toplam değerlerinden biri insan düzeltmesidir; dolu alan sayısı doğruluk oranı değildir.

11 belgede para birimi, 14 belgede tarih, 25 belgede vergi temeli eksik/belirsiz. Şirket veritabanında yalnızca bir sentetik demo tedarikçisi ve bir demo siparişi var. FATURA şirketlerinin bunlarla doğrulanmış ilişkisi yok; 25 belgede de onaylı sipariş eşleşmesi bulunmuyor. Bu iş verisi eksikliği, okuma/çıkarım sorunundan ayrıdır.

## Süre neden uzundu?

Kullanıcının yaklaşık iki saatlik oturum gözlemi, salt belge işleme süresi olarak kaydedilmiş bir ölçüm değildir. Oturumda kod değişiklikleri, hata giderme, servis başlatma, uygulamalı kontrol ve raporlama da yapıldı; bütün oturumu aşamalara ayıran eksiksiz süre kaydı yok.

Mevcut olay kayıtlarından görülenler:

- İlk işleme başlangıcı: 14 Ekim 2026, Melbourne 18:06:24.
- Son belgenin ilk pipeline doğrulama kaydı: aynı gün 18:41:33.
- Bu aralık yaklaşık 35 dakika; geliştirme sırasında verilen aralar da dahil.
- Belge başlangıcından ilk pipeline doğrulamasına kadar kaydedilen süreler toplamı yaklaşık 31,5 dakika; belge başına ortalama yaklaşık 76 saniye, aralık yaklaşık 54–124 saniye.
- Aynı penceredeki model HTTP loglarında 26 çağrı ve toplam yaklaşık 30,3 dakika var. Buna 25 çıkarımın yanı sıra ilk belgenin önceki akıştaki ek açıklama çağrısı da dahil. Güncel akış, kontrol açıklamasını ek model çağrısı olmadan oluşturuyor.

Kodda process_selected dosyaları sırayla gönderiyor; workflow içindeki processing_lock, mevcut tek servis sürecinde aynı anda bir belgeyi işlemeye izin veriyor. Genel amaçlı 7B model 4 CPU iş parçacığıyla, GPU olmadan çıktı üretiyor. OCR ayarı tam sayfa OCR'ı zorunlu kılıyor; metni zaten erişilebilir PDF'ler için bu işten kaçınan ayrı bir yol yok. Bağımsız iş kuyruğu ve paralel belge işçileri yok.

Loglar mevcut durumda model çağrılarının başlıca zaman tüketicisi olduğunu gösteriyor. OCR, veritabanı ve diğer aşamalar için eksiksiz ayrı süre ölçümleri yok. İşleme sırasında uygulama/şema değiştiği için bu gözlemler sabit sürümle yapılmış bir kapasite testi veya geleceğe dönük hız garantisi değildir.

## Yüksek hacmin genel mantığı

Base64.ai'ın iç mimarisi ve gerçek performansı bu çalışma kapsamında doğrulanmadı. Yüksek hacimli belge sistemlerinde genel yaklaşım: hızlı kabul/kayıt, kalıcı iş kuyruğu, yeterli hesaplama kaynağı üzerinde eşzamanlı çalışan belge işçileri, uygun okuma/çıkarım yoluna yönlendirme, şirket kuralları ve gerekli durumlarda insan incelemesidir.

Belge kabul hızı, bir belgenin sonuçlanma süresi ve saatte tamamlanan belge sayısı ayrı ölçülerdir. Günde 1.000 belge ile aynı anda gelen 1.000 belge aynı kapasite gereksinimi değildir. Paralellik, aynı işlem kodunun farklı belgeler üzerinde çalışan kopyalarıyla sağlanabilir. Model için uygun hızlandırıcı veya çıkarım servisi seçimi ancak kalite, gecikme, maliyet ve veri gereksinimleriyle değerlendirilmelidir.

Sadece CPU çalışan süreç sayısını artırmak mevcut makinede kaynak rekabetine yol açabilir. Hesaplama hızlandırmak da yanlış alan eşleşmelerini kendiliğinden düzeltmez. Bu nedenle kalite, iş verisi ve kapasite ayrı çalışmalar olarak ele alınmalıdır.

## Kabul standardı ve önerilen sıra

1. **Ürün kapsamını ve kabul koşullarını yazılı hale getirmek.** Desteklenen dil/belge türü, zorunlu alanlar, günlük sayfa/belge hacmi, yoğun saat gelişleri, hedef sonuçlanma süresi, belge başına maliyet ve insan incelemesi koşulları belirlenmeli. Yükleme tamamlandı, çıkarım doğrulandı, sipariş eşleşti ve insan kararı kaydedildi ayrı durumlar olmalı. Sayısal hedefler henüz kararlaştırılmadı.
2. **Mevcut çıkarım ve kanıt zincirini düzeltmek.** Özellikle 11 alıntı/kimlik uyuşmazlığı incelenmeli. Modelin alıntıyı yeniden üretmesine bağımlılığı azaltıp gerçek OCR parçası/konumuna dayalı kanıt oluşturma değerlendirilmeli; sayı ve alan anlamı kontrolleri korunmalı. Belgedeki gerçek eksiklik, OCR hatası, model hatası ve doğrulayıcının gereksiz reddi ayrılmalı. Küçük, insan tarafından doğrulanmış kabul örnekleri yeterlidir; kapsamlı benchmark gerekmiyor.
3. **Gerçek şirket bağlamını sağlamak.** Onaylı tedarikçiler, ad eşanlamlıları, siparişler ve vergi/para kuralları gelmeli. Doküman okumanın iyi olması bu kayıtların yerini tutmaz. Kullanıcı sipariş seçimi belge çıkarımından ayrı kalmalı.
4. **Kalitesi kabul edilen akışın kapasitesini geliştirmek.** Aşama süreleri, kuyruk beklemesi ve model süreleri görünür hale getirilmeli; gereksiz OCR/model işi azaltılmalı. Sonrasında kalıcı kuyruk, sınırlı paralel işçiler ve ihtiyaca uygun hesaplama seçilmeli. Hacim hedefi bilinmeden kapasite sözü verilmemeli.
5. **Üretim işletimini tamamlamak.** Kullanıcı/şirket yetkileri ve veri ayrımı, dayanıklı iş durumu, kontrollü yeniden deneme, aynı faturada iki işlem/kararı engelleme, yedekleme, izleme ve gereken iş sistemi giriş/çıkışları tamamlanmalı. Otomatik ödeme bu ürünün mevcut hedefinin parçası değildir.

Tamamlanma ölçütü, her belgenin koşulsuz otomatik onaylanması olamaz. Tanımlanmış kapsamda güvenilir alan ve kontrol sonucu üretmek, belirsiz vakayı doğru gerekçeyle insan incelemesine almak, karar geçmişini korumak ve kararlaştırılan hacim/süre/maliyet koşullarını karşılamak ölçüt olmalıdır. Bugün inceleme iş akışı çalışıyor; çıkarım kalitesi, gerçek şirket bağlamı ve üretim kapasitesi henüz bu hedefi karşılamıyor.

Kaynaklar: [README](../README.md), [25 belge raporu](FATURA_REVIEW_STATUS.md), [ayrıntılı durum verisi](FATURA_REVIEW_STATUS.json), [uygulamalı inceleme kontrolü](REVIEW_FLOW_NOTES.md), `billvision/workflow.py`, `billvision/ocr.py`, `billvision/llm.py`, `scripts/process_selected.py`; PostgreSQL review_events ve yerel Ollama logları.
