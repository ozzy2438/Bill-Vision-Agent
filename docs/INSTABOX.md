# Instabox üzerinde devam etme

Aktif kutu: `box-4b0945` (makine kimliği `m_agqt2l2axdmvexq6k3wpy67jtm`). Kullanıcı `dev`; proje `/data/workspace/Bill-Vision-Agent`. Çalışma dalı `work`. Kalıcı disk üzerinde kaynak kod, storage, data/fatura, model dosyaları ve PostgreSQL volume'u bulunur. Başlangıçta kutu sağlayıcının no_capacity hatası nedeniyle açılamadı; sonraki resume başarılı oldu. Yeni kutu oluşturulmadı.

Mevcut Instabox oturumunuz olan bilgisayardan, kutu duraklatılmışsa:

```bash
npx instabox@latest resume box-4b0945
npx instabox@latest ssh box-4b0945
```

`sh` yeni kutu oluşturur; bu proje için mevcut kutuya bağlanın.

Kutu içinde, süreçler durmuşsa:

```bash
cd /data/workspace/Bill-Vision-Agent
export OLLAMA_BIN=/opt/billvision-ollama/bin/ollama
bash scripts/start.sh
```

Doğrulanmış hazır olma koşulu: API /health içinde database, ollama_model, docling_artifacts ve ready değerlerinin true olması; Streamlit sağlık isteğinin 200 dönmesi. Yeniden açılışta 25 faturayı tekrar işlemeyin. Arayüz ve API loopback üzerinde 8501 ve 8000 portlarını kullanır; açık/public port yayımlanmadı.

Kendi bilgisayarınızda arayüze erişmek için SSH tüneli (bu oturumu açık tutun):

```bash
npx instabox@latest ssh box-4b0945 -- -L 8501:127.0.0.1:8501
```

Ardından tarayıcıda yerel 8501 portunu açın. Makine boşta kalınca mevcut 30 dakikalık otomatik duraklatma ayarı devreye girebilir; bu ayar değiştirilmedi.

Kurulan bileşenler: Python 3.12.15, uv.lock ile sabitlenmiş Python bağımlılıkları, PostgreSQL 17.6, Tesseract 5.5.0 + İngilizce verisi, aynı Docling Heron revizyonu ve Ollama 0.40.3 üzerinden aynı qwen2.5:7b. Model indirmelerinde TLS ve yayımlanmış checksum doğrulaması kullanıldı. 4 vCPU / 8 GiB bellek var; bu kapasitede yeni çıkarım hızı veya yük kapasitesi ölçülmedi. API anahtarı bu kutuya, depoya veya taşıma paketine kopyalanmadı.

Kurulumu bu kutuda yeniden hazırlamak gerekirse, mevcut kayıtları koruyarak:

```bash
export BILLVISION_OLLAMA_DIR=/opt/billvision-ollama
export OLLAMA_BIN=/opt/billvision-ollama/bin/ollama
bash scripts/install_ollama_linux.sh
bash scripts/setup.sh
```

Model dosyaları ve mevcut FATURA seçkisi yeniden kullanılır. Hazırlık betiği etiket cevaplarını çıkarıma vermez. Mevcut çalışan kutuda bu kurulumu tekrar çalıştırmak gerekmez.

İlk taşıma yedeği `/data/workspace/billvision-transfer`; tutar güncellemesi öncesi PostgreSQL yedeği proje içindeki `.runtime/before-amount-revalidation.dump` dosyasıdır. Güncel inceleme kayıtlarının kaynağı bu Instabox veritabanıdır; eski Codex veritabanı güncel sanılarak üstüne yazılmamalıdır. [Sonuçlar ve kalan eksikler](AMOUNT_REVALIDATION_NOTES.md).
