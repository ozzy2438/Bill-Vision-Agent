# Bill Vision Agent

17 Ekim 2026: proje mevcut [Instabox kutusuna taşındı](docs/INSTABOX.md). Saklanan OCR/model çıktılarıyla 12 toplamın kanıt sorunu giderildi; beş toplam belirsizliği açık bırakıldı. [Değişiklikler, uygulamalı kontrol ve kalan işler](docs/AMOUNT_REVALIDATION_NOTES.md).

Faturayı belge kanıtlarıyla siparişe karşılaştıran, kontrol sonuçlarını gösteren ve insan kararını yerel olarak kaydeden tek kullanıcılı MVP. Fatura okuma ile sipariş kontrolü arasındaki elle veri taşıma işini azaltmayı amaçlar. Base64.ai'ın kapalı mimarisini veya patentlerini uyguladığı iddia edilmez.

**Bu bir sentetik veri demosudur.** FATURA belgeleri gerçek müşteri faturası değildir. Siparişler ve tedarikçiler ayrıca üretilmiş hayali şirket verileridir. Onay ödeme, e-posta, bankacılık veya ERP yazımı yapmaz.

## Başlatma

Gerekenler: Python 3.12, `uv`, Docker Compose, Tesseract 5 ve İngilizce `eng` verisi, Ollama. Bu ortamda 4 CPU kotası ve 32 GiB RAM var; GPU bulunmadı. Qwen model katmanı yaklaşık 4.68 GB; CPU üzerinde çalışır ve hız garantisi verilmez. Modelin indirilmesi ve Ollama'ya aktarılması için geçici ek disk alanı gerekir.

```bash
cd /workspace/Bill-Vision-Agent
# Bu bulut ortamına kurulan Ollama:
export OLLAMA_BIN=/workspace/local-tools/ollama/bin/ollama
# Kendi bilgisayarınızda Ollama PATH üzerindeyse bu export gerekmez.

# İlk kurulum / bağımlılıkları yenileme:
bash scripts/setup.sh

# Sonraki açılışlar; indirilen modelleri yeniden indirmez:
bash scripts/start.sh

# Yalnızca istenen üç gerçek işlev gösterimi:
uv run python -m scripts.run_demos
```

Yerel bilgisayarda arayüz portu **8501**, API **8000**, Ollama **11434**, PostgreSQL **54329**. Tarayıcıda kendi bilgisayarınızın 8501 portunu açın. Bulut onboarding arayüzü localhost önizleme bağlantısı sunmaz; doğrulamalar yerel HTTP istekleriyle yapılır.

Uygulama ve Ollama host üzerinde, yalnızca PostgreSQL Compose içinde çalışır. Linux/macOS'ta host uygulaması veritabanına `127.0.0.1:54329` ile erişir; `db` adı hosttan kullanılmaz. Windows'ta Python/Tesseract/Ollama'yı aynı WSL2 dağıtımında çalıştırın ve Docker Desktop'ın o dağıtımla entegrasyonunu açın. Farklı host/WSL ağlarını otomatik tahmin etmiyoruz. Özel bağlantılar için `.env.example` dosyasını `.env` olarak kopyalayıp URL'leri düzenleyin; varsayılan başlatma betiği yukarıdaki yerel portları kullanır.

PostgreSQL demo bağlantısı yalnızca loopback'e açılır ve yerel `trust` kimlik doğrulaması kullanır. Tek kullanıcı içindir; sunucuları ağa açacak bir üretim kurulumu değildir. Uygulamada kullanıcı kimliği giriş alanıdır, kimlik doğrulama sistemi değildir.

Linux x86-64 için Ollama eksikse `bash scripts/install_ollama_linux.sh` resmî 0.40.3 sürümünü yayımlanmış SHA-256 ile doğrulayarak kurar. Diğer işletim sistemlerinde resmî Ollama kurulumunu kullanın. Tesseract İngilizce verisinin `tesseract --list-langs` çıktısında `eng` olarak göründüğünü kontrol edin.

`setup.sh`, bağımlılıkları `uv sync --frozen` ile kurar; veritabanını ve demo şirketini hazırlar; Docling layout ağırlıklarını, resmî Qwen paketini ve küçük FATURA seçkisini indirir. Qwen, aynı resmî GGUF/model şablonu/lisansıyla Ollama'nın desteklenen `create` komutuyla içe aktarılır. Bu yöntem bulut proxy'siyle çalışır ve Ollama 0.40'ın doğrudan DNS gerektiren yönlendirme kontrolüne takılmaz. TLS ve SHA-256 doğrulaması açıktır. Başlatma betiği Docling/Transformers'ı çevrimdışı moda alır. İndirmelerden sonra uygulama yerel servislerle çalışır.

Dosyalar ve modeller diskte kalır; süreçler yeni görevde yeniden başlatılmalıdır. `.runtime/` servis loglarını ve yalnızca betiğin başlattığı süreçlerin PID'lerini tutar. `storage/`, `models/`, veritabanı volume'u ve etiketler Git'e eklenmez. Yerel dosyaları temizlemek verileri silebilir; betikler mevcut incelemeleri veya demo kayıtlarını sıfırlamaz.

## Örnek kullanım

1. Kenar çubuğunda `A-exact.pdf` örneğini seçip inceleyin. Belge, 2.000 AUD sipariş ve zorunlu kontroller uygunsa durum `ready_for_approval` olur. Yerel onayı ayrıca insan kaydeder.
2. `B-difference.pdf` için 2.200 AUD fatura ile 2.000 AUD siparişin **200 AUD** farkını, `TOTAL` kuralını ve belge alıntısını görün. Durum `needs_review` olmalıdır.
3. A'yı tekrar yükleyin. SHA-256 kontrolü önceki kaydı açar; ikinci iş kaydı oluşturmaz.

Belgeler gerçek PDF okuma, Tesseract OCR ve Ollama çıkarımından geçer. Hazır çıkarım JSON'u yoktur. `docs/demo-observations.json` komutun gerçekten gözlediği son sonucu içerir; çalıştırılamayan aşamalar başarı sayılmaz. Bunlar benchmark veya başarı oranı ölçümü değildir.

PDF, PNG ve JPEG kabul edilir. Varsayılanlar dosya başına **10 MiB**, PDF başına **5 sayfa**, görüntü başına **25 milyon piksel**; şifreli PDF ve çok kareli görüntü kabul edilmez. Sınırlar `.env.example` üzerinden ayarlanabilir. İçerik türü dosya baytlarından doğrulanır; uzantıya güvenilmez.

Yan yana belge önizlemesi ve alanlar gösterilir. Alanın gerçek OCR alıntısı, sayfası ve varsa Docling kutusu açılabilir. PO belgede yoksa kullanıcı sipariş bağlamını seçebilir; `context_po_id` ve `context_source`, `document_po_number` alanından ayrı kalır. Bağlam tedarikçi kimliği doğrulamasının yerini almaz. Alan düzeltmesi eski/yeni değer, gerekçe, aktör ve zamanı kaydeder; kontrolleri yeniden çalıştırır ve önceki revizyonun kararını geçersiz kılar. İnsan düzeltmesindeki eski OCR alıntısı yeni değerin çıkarıldığı iddiası değildir. Sonuçlar JSON/CSV olarak dışa aktarılabilir.

## Mimari ve karar sınırı

Streamlit → FastAPI içindeki tek Python koordinatörü → PostgreSQL / yerel storage / Docling+Tesseract / Ollama.

Sabit sıralı akış: `read_document → extract_invoice → lookup_purchase_order / validate_invoice → get_policy → write_review → insan kararı`. Sınırsız model döngüsü, çoklu agent veya bağımsız kuyruk yoktur. Modelin araç, shell, SQL veya dosya okuma yetkisi yoktur; yalnızca OCR metni, gerçek parça kimlikleri ve onaylı alan etiketi ipuçları verilir. Etiket JSON'ları veya sipariş tutarları çıkarım modeline verilmez. Belge içindeki talimatlar veri sayılır.

Çıkarımda Ollama JSON Schema ve Pydantic doğrulaması kullanılır. Her dolu alanın `evidence_id` değeri, alıntısı ve değerinin alıntıda bulunması ayrıca denetlenir. Kutu ve sayfa modelden alınmaz, gerçek OCR kaydından eklenir. Şema uyumu veya geçerli alıntı içerik doğruluğunu garanti etmez; insan belgeyi görerek incelemelidir. Belirsiz tarih, sayı ve `$` para birimi null/inceleme ile sonuçlanır. Uzun OCR metni sessizce kesilmez; bu MVP'nin bağlam sınırını aşarsa hata gösterilir.

Sipariş otomatik eşleştirmesi açık PO numarası ve kayıttaki tam tedarikçi vergi kimliği/uyumlu yasal adı gerektirir. Benzer ad veya eşit tutar eşleşme sayılmaz. Parametreli SQL kullanılır. Para hesaplamaları **Decimal** ile yapılır ve JSON'da para değerleri metin olarak korunur.

`policy.yaml` sürümlü kuralları, `policy.md` aynı kimliklerin açıklamalarını taşır. Politika maddesi kimlikle doğrudan getirilir; vektör RAG değildir. Durum backend tarafından belirlenir: zorunlu kontrollerin tamamı pass ise `ready_for_approval`; eksik/çelişkili/değerlendirilemeyen zorunlu kontrol veya herhangi bir fail varsa `needs_review`; tekrar sinyalinde `suspected_duplicate`. Satır kontrolü güvenilir ve tam satırlar yoksa `not_evaluated` olur. Güncel inceleme açıklaması doğrudan kontrol bulgularından üretilir; ek model çağrısı yapılmaz. Önceden kaydedilmiş model açıklamaları tarihçede korunur.

## Veri ve lisanslar

```bash
uv run python -m scripts.prepare_demo
uv run python -m scripts.prepare_fatura --count 25
# Ağ erişimi yoksa resmî arşivi yerel dosyadan kullanın:
uv run python -m scripts.prepare_fatura --archive /path/to/FATURA2.zip
```

FATURA kaynağı, boyutu, yazar atfı, farklı arka planların aynı iş vakası oluşu ve etiket ayrımı: [DATA_SOURCES.md](DATA_SOURCES.md). Yazılım/model/veri lisansları: [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md). Tam bağımlılık kilidi: `uv.lock`; veritabanı şeması: `schema.sql`.

İlk indirmeler için PyPI/PyTorch, Docker registry, GitHub release assets, `zenodo.org`, `huggingface.co` ve ağırlık yönlendirme adresleri gerekir. Bu ortamda görülen ek model adresleri `us.aws.cdn.hf.co`, `registry.ollama.ai`, `dd20bb891979d25aebc8bec07b2b3bbc.r2.cloudflarestorage.com` olmuştur. İzinli indirme adresleri ortam taslağına kaydedilir; ağ engeli varsa doğrulama kapatılmaz veya ücretli servise geçilmez.

## Sınırlar

İngilizce, belge başına tek fatura ve tek yerel kullanıcı. Fatura toplamı karşılaştırması ilk sürümün zorunlu kapsamıdır; karmaşık satır tabloları tam çıkarım garantisi taşımaz. Keyfi FATURA tedarikçileri hayali şirket siparişleriyle otomatik olarak ilişkilendirilmez. Üretim kimlik doğrulaması, gerçek ERP/banka entegrasyonu, otomatik ödeme, öğrenme/fine-tuning, ek veri kümeleri veya benchmark paketi yoktur.

## Farklı faturalarla incelemeyi tamamlama

İnceleme listesinde bekleyen/sonuçlanan kayıtları süzün ve **Listeden belge aç** ile kayda gidin. **Şimdi ne yapmalıyım?** bölümü gereken bilgi ve kararı, yanında kural kimliği/sürümünü gösterir. Belirsiz model adayı doğrulanmış değerden ayrıdır; alıntı hatalıysa gerçek kaynak parça yine görülebilir, doğrulanmamış alıntı gösterilmez.

Toplam, vergi ve ara toplam için değer, kaynak etiket, yakın metin, gerçek sayfa/konum ve kullanılan ipucu saklanır. Aynı satırın ayrı OCR parçaları yalnızca mevcut kutular hizalıysa birlikte değerlendirilir; ayrı parçalar ve kutuları korunur. Bir sayının metinde bulunması tek başına alan eşleşmesi değildir. İnsan düzeltmesinde kaynak metin önceki OCR kaynağıdır; yeni değerin modelden geldiği iddia edilmez.

`company_context.yaml` v1.0.0 onaylı adları ve alan etiketi ipuçlarını; `policy.yaml`/`policy.md` v1.2.0 karşılaştırma ve inceleme kurallarını tutar. Mevcut tedarikçi/sipariş kayıtları korunmuştur. Yeni bir tedarikçi için şirket kayıt sorumlusu doğrulanmış vergi kimliği, ad/eşanlamlılar ve gerçek sipariş bilgilerini sağlamalıdır. Dosyalar elle sürümlenir; inceleyen kişinin düzeltmesi genel kurala dönüşmez. FATURA etiketlerinden şirket ilişkisi üretilmez. Para toleransı mevcut 0.01 tutarıdır.

Belgede PO yoksa doğrulanmış tedarikçinin adayları gösterilir ve kullanıcı bağlam seçer. Bir veya birden fazla aday, tek başına otomatik eşleşme yaratmaz. Bağlam seçimi alanı değiştirmez; tedarikçi/PO çelişkisi onayı engeller. Düzeltmeden sonra kontrollerin önce/sonra bulguları mevcut `review_events` içinde kaydedilir; önceki karar geçersizleşir. Çözülemeyen belge gerekçeyle yerel olarak reddedilebilir; başarısız çıkarım da reddedilebilir.

```bash
# Seçilmiş 25 dosyadan yalnızca SHA-256 kaydı olmayanları gerçek akışa ver:
uv run python -m scripts.process_selected
# OCR/model çalıştırmadan mevcut durum raporunu yenile:
uv run python -m scripts.process_selected --report-only
```

Başarısız mevcut kayıt otomatik tekrar işlenmez. Yeniden deneme yalnızca uygulamadaki açık kullanıcı işlemiyle yapılır. Her deneme mevcut olay geçmişindedir. [25 belgenin durum tablosu](docs/FATURA_REVIEW_STATUS.md) ve [alan/kontrol ayrıntıları](docs/FATURA_REVIEW_STATUS.json), uygulamadaki kayıtların raporudur; yeni bir inceleme veya etiket sistemi değildir. Eski A/B/C gösterimleri bu çalışma için tekrar çalıştırılmadı.
