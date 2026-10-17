"""Render the bundled 12-second silent walkthrough from our actual 3D component.

Developer-only: build frontend/circular-slider first, then use Python with
Playwright, system Chromium and ffmpeg. None is required by the app at runtime.
"""
from pathlib import Path
import subprocess
import tempfile
from playwright.sync_api import sync_playwright

ASSETS = Path(__file__).resolve().parents[1] / 'assets'
SCENES = [
    ('01 / FATURANIZI YÜKLEYİN', 'Bir dosyayla başlayın.', 'PDF veya fotoğrafınızı seçin. Fatura bilgileri bir araya gelsin.'),
    ('02 / GÖZDEN GEÇİRİN', 'Belirsizlikleri görün.', 'Bilgileri belgedeki kaynağıyla karşılaştırın. Gerekiyorsa düzeltin.'),
    ('03 / SONUÇLANDIRIN', 'Son karar sizin.', 'Güncellenen kontrolleri görün. Onayınızı veya ret gerekçenizi kaydedin.'),
]


def main():
    with tempfile.TemporaryDirectory(prefix='billvision-video-') as tmp:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
            page = browser.new_page(viewport={'width':1280,'height':720}, device_scale_factor=1)
            page.set_content((ASSETS / 'circular-slider/index.html').read_text(), wait_until='load')
            page.get_by_role('button',name='Otomatik dönüşü duraklat').click()
            page.add_style_tag(content='''
                .carousel-shell{border:0;border-radius:0;width:1280px;height:720px}
                .hero-heading{padding-top:42px;max-width:1000px}.hero-heading h1{font-size:54px}
                .hero-description{font-size:19px}.hero-kicker{font-size:13px}
                .hero-actions,.selection-row,.slider-controls,.gesture-hint{display:none}
                .slider-stage{height:455px;overflow:visible}.cylinder-camera{top:45%}
                .scene-footnote{position:absolute;bottom:15px;width:100%;font-size:12px;margin:0}
            ''')
            for frame in range(288):
                step = SCENES[min(2, frame // 96)]
                page.evaluate('''({step, angle}) => {
                    document.querySelector('.hero-kicker').textContent = step[0];
                    document.querySelector('h1').textContent = step[1];
                    document.querySelector('.hero-description').textContent = step[2];
                    document.querySelector('.cylinder-ring').style.transform = `rotateY(${angle}deg)`;
                    document.querySelector('.scene-footnote').textContent = 'Bill Vision · Temsili anlatım · Son karar sizde';
                }''', {'step':step,'angle':-frame * .45})
                page.screenshot(path=f'{tmp}/{frame:04d}.png')
            browser.close()
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate','24','-i',f'{tmp}/%04d.png','-c:v','libx264','-preset','slow','-crf','24','-pix_fmt','yuv420p','-movflags','+faststart',str(ASSETS/'bill-vision-intro.mp4')],check=True)
    print('Created 12-second intro:',(ASSETS/'bill-vision-intro.mp4').stat().st_size,'bytes')

if __name__ == '__main__':
    main()
