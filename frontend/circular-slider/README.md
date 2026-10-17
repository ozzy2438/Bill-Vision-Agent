# Bill Vision Circular Slider

Streamlit içindeki gerçek fatura kayıtlarına bağlı React + TypeScript bileşeni. Tailwind CSS ve CSS 3D transforms kullanır; Framer Motion veya Swiper yoktur. Tam 360° halka 14 karttan oluşur. Her kart `rotateY((360 / cards.length) * index) translateZ(radius)` ile yerleşir; hem kamera hem halka `preserve-3d` kullanır. Kartın ayrı arka yüzü, arka taraftaki belgelerin aralıklardan görünmesini sağlar.

## Geliştirme

```bash
npm ci --prefix frontend/circular-slider
npm run build --prefix frontend/circular-slider
```

Build, TypeScript kontrolünden sonra `assets/circular-slider/index.html` üretir. Bu dosya tüm React kodunu ve CSS'i içerir ve uygulamayla birlikte sürümlenir. Uygulamayı çalıştırmak için Node, npm, CDN veya ayrı bir web sunucusu gerekmez; mevcut Streamlit süreci bileşeni sunar. Kaynak değişince üretilen dosyayı da commit edin.

## Bileşenler

- `CircularSlider`: geometri, sürükleme, momentum, hizalama, görünürlük ve hareket tercihleri.
- `SliderCard`: gerçek 3D konum, ön/arka yüz, odaklanabilen kart.
- `SliderControls`: önceki/sonraki, sayaç, otomatik dönüşü duraklatma.

`CircularSlider` özellikleri: `cards`, `radius` (330), `rotationSpeed` (3 derece/saniye), `autoRotate` (true), `cardWidth` (132), `cardHeight` (190), `perspective` (1200), `onOpen`. Boyutlar kapsayıcıya göre uyarlanır. Kartların `documentId` alanı varsa açma düğmesi gösterilir. Tutar veya çıkarım sonucu üretilmez; kartlar temsili belge kapaklarıdır.

`main.tsx` Streamlit'in custom-component mesaj sözleşmesini kullanır. Yalnızca üst pencereden gelen render mesajını kabul eder. Bileşen `upload`, `video` veya `open` olayı gönderir; Python tarafı seçilen belge kimliğini mevcut kayıtlarla doğrular ve olay kimliğini bir kez işler.

## Etkileşim ve erişilebilirlik

Fareyle sürükleme ve mobil yatay kaydırma; bırakınca zaman tabanlı sürtünme ve en yakın karta hizalama. Bir karta tıklamak onu öne getirir. Kart veya sahne odaktayken sağ/sol oklar, Home ve End çalışır. Otomatik dönüş, fare sahnedeyken veya klavye odağı sahne içindeyken durur. Kontroller gerçek düğmelerdir; kaydırma tek kullanım yolu değildir.

`prefers-reduced-motion` otomatik dönüşü ve momentumu kapatır; kullanıcının açık seçimi anında uygulanır. Sayfa gizliyken veya sahne ekran dışındayken otomatik dönüş güncellenmez. Kullanıcının ok düğmeleriyle verdiği hizalama komutu, sahne yukarıda kalsa da uygulanır. Dönüş `requestAnimationFrame` içinde DOM transformuna yazılır; her karede React render edilmez. Gerçek FPS cihaz ve tarayıcıya bağlıdır; sabit 60 FPS garantisi verilmez.

## Tanıtım videosu

`assets/bill-vision-intro.mp4`: sessiz, 12 saniyelik temsili yükle–incele–karar anlatımı. Kullanıcı başlatır, yerel dosyadan oynatılır. Eşdeğer metin video altında yer alır.

Görseli yeniden üretmek için geliştirme ortamında Playwright, Chromium ve ffmpeg ile `python3 scripts/render_intro.py` çalıştırılır. Bunlar uygulamanın çalışma bağımlılıkları değildir.
