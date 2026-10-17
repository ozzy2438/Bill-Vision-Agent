# Tutar kanıtlarının yeniden doğrulanması — 17 Ekim 2026

Çalışma Instabox `box-4b0945` üzerinde tamamlandı. Mevcut 25 FATURA belgesinin OCR/model çıktıları kullanıldı; yeni OCR veya model çıkarımı yapılmadı, etiket JSON'ları kullanılmadı. İlk kaynak kayıtları 27 belge (25 FATURA + iki demo), 69 olaydı; yeniden doğrulama sonunda 27 belge ve 103 olay var. Yeni bir kayıt sistemi kurulmadı.

## Değişen davranış

Modelin atıf yaptığı gerçek OCR parçası aynı satırdaki etiket/tutar parçalarıyla birlikte değerlendirilir. Aday sayı tek bir parçada bulunmalı ve onaylı etiket alanın anlamını açıkça doğrulamalıdır. Başka sayfada veya başka satırda aynı sayıyı arayarak eşleştirme yapılmaz. Kaynak alıntı, sayfa ve kutu gerçek tutar parçasından alınır; modelin ilk iddiası ayrıca ve doğrulanmamış olarak saklanır. Eski çıkarımlardaki etiket/para birimi içeren tek sayısal adaylar ayrıştırılır; bu işlem para birimi veya eksik değer üretmez. Yeni model çıktısının NumericClaim şeması değişmedi.

Politika v1.2.0 içinde EVIDENCE kuralı v1.2.0 oldu; diğer kurallar v1.1.0 ve şirket ipuçları v1.0.0 olarak kaldı. BALANCE DUE / AMOUNT_DUE ipucu listesine toplam eşanlamlısı olarak eklenmedi.

Arayüzde **Tutar kanıtlarını mevcut OCR ile yeniden kontrol et** düğmesi var. Yalnızca belirsiz tutarlar tekrar değerlendirilir; insan düzeltmeleri ve dolu/doğrulanmış alanlar korunur. Gerçek bir değişiklik revizyonu artırır, önceki kararı geçersizleştirir ve mevcut review_events içinde eski/yeni alanları ve kontrol farklarını kaydeder. Aynı işlem yeniden uygulandığında veri değişmediyse yeni revizyon/olay eklenmez.

## Mevcut belgelerde sonuç

| Eksik/belirsiz alan | Önce | Sonra |
|---|---:|---:|
| Toplam | 17 | 5 |
| Ara toplam | 23 | 9 |
| Vergi tutarı | 21 | 15 |

Toplam alanı 20 belgede dolu; bunların biri önceki insan düzeltmesidir. Bu sayılar doğruluk oranı veya onaylanabilir fatura sayısı değildir. 25 belgenin tamamı işlenmiş durumda; 24 inceleme bekliyor, bir önceki yerel ret kararı geçerli. 25 özgün işleme denemesi aynen korundu. Tüm FATURA kayıtlarının kontrol durumu needs_review; gerçek şirket tedarikçi/sipariş kayıtları, açık para birimi veya vergi temeli gibi eksikler devam ediyor. İlk insan düzeltmeli kayıt ve iki eski demo dahil diğer 10 belgeye dokunulmadı. 79 özgün belge/OCR/model dosyasının hash'leri değişmedi.

Kalan toplam belirsizlikleri:

| Belge | Somut neden | Sonraki işlem |
|---|---|---|
| Template15_Instance134.jpg | Model 726.05 adayını 748.50 EUR ara toplam parçasına dayandırıyor. | Belgeden gerçek toplamı doğrulayın; kanıt yoksa açıklama isteyin veya gerekçeyle reddedin. |
| Template33_Instance176.jpg | Aday BALANCE DUE alanında. | Fatura toplamını ödenecek bakiyeden ayrı doğrulayın. |
| Template37_Instance119.jpg | Aday AMOUNT_DUE alanında. | Fatura toplamını ödenecek bakiyeden ayrı doğrulayın. |
| Template38_Instance186.jpg | Aday BALANCE DUE alanında. | Fatura toplamını ve yalnızca $ ile belirtilen para birimini doğrulayın. |
| Template48_Instance159.jpg | Aday BALANCE DUE alanında. | Fatura toplamını ödenecek bakiyeden ayrı doğrulayın. |

[25 belgenin güncel tablosu](FATURA_REVIEW_STATUS.md), [önce/sonra kayıtları](AMOUNT_REVALIDATION_RESULTS.json) ve [alan/kontrol ayrıntıları](FATURA_REVIEW_STATUS.json).

## Kısa uygulamalı doğrulama

Instabox üzerinde gerçek FastAPI ve Streamlit AppTest, veritabanının geçici kopyasıyla kullanıldı. Template6 toplamı düğmeye basıldığında null → 441.17 oldu; gerçek kaynak p1-e38 / 441.17 USD olarak gösterildi. Aynı kayıttaki geçici ret geçersizleşti ve kontrol farkları arayüzde göründü. Eski revizyon isteği 422 ile reddedildi; tekrarlanan işlem yeni revizyon üretmedi. Önceki insan düzeltmesi ve kararı değişmedi. Yanlış sayı, başka sayfa, eksik kutu, tekrar eden tutar ve bilinmeyen kanıt kimliği kesin değer üretmedi. Geçici veritabanı ve test API süreci kaldırıldı. [Gözlem kaydı](amount-revalidation-observations.json).

Ardından aynı uç nokta üzerinden 17 mevcut belgenin belirsiz tutarları güncellendi. Yeni test paketi, yük testi veya benchmark eklenmedi; A/B/C demoları tekrarlanmadı. Yeni bir belgenin baştan OCR/model çıkarımı bu taşımada tekrar denenmedi. Servis hazır olma kontrolü, model dosyalarının doğrulanması ve değişen inceleme akışı doğrulandı.
