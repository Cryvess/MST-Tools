# MSTTools v1.2

**Projenin içini gör. Sorunları bul. Sonuçları paylaş.**

Proje analizi, sistem tanılama ve geliştirici araçlarını renkli bir terminalde birleştirir.
Kaynak kodunu bir sunucuya yüklemeden çalışır.

## Pip ile kurulum

Yayımlanmış sürümü kurmak veya güncellemek için `python -m pip install --upgrade msttool` kullan.
Sonra kendi proje klasöründe `mst` yaz. Kaynak klasörde hazırlanan sürüm PyPI'a henüz yüklenmemişse
onu kurmak için aşağıdaki yerel kurulum komutunu kullan.

## Kurulum

Python 3.9 veya üzeri gerekir. Bu klasörde terminal aç:

```powershell
python -m pip install --upgrade .
python -m msttools
```

Sonra `mst` komutunu veya Windows'ta `Start-MSTTools.cmd` dosyasını kullanabilirsin.
Başka bir projeyi incelemek için `mst -C "C:\Projeler\Uygulamam" dashboard` yaz.

## v1.2 ile gelenler

- Numarayla veya komutla kullanılabilen, filtrelenebilir renkli komut merkezi.
- Dil dağılımı, dosya/satır istatistikleri ve öncelikli bulgular içeren dashboard.
- Python karmaşıklığı, olası gizli anahtarlar ve proje düzeni denetimi.
- Gerçek manifestlerden Python, Node ve Rust bağımlılık listesi.
- SHA-256 anlık görüntülerle eklenen, silinen ve değişen dosyaları karşılaştırma.
- Çevrimdışı HTML ve makine tarafından okunabilir JSON raporları.
- Değerleri göstermeden `.env` anahtar karşılaştırması.
- HTTP süre/başlık, TLS sertifika ve paralel localhost port kontrolü.
- JSON biçimlendirme, JWT çözümleme, Base64 ve UUID araçları.
- Önizlemeli temizleme, otomatik testler ve GitHub Actions yapılandırması.

İşlem sonucu Enter'a basana kadar ekranda kalır; ardından ana menü açılır. Doğrudan komutlar beklemez.

Menüde `?` yardım, `/network` filtre, `q` çıkış. Eski komutlar da kullanılabilir.

## Örnek akış

```powershell
mst dashboard
mst audit
mst snapshot -o .msttools/once.json
# Projende değişiklik yaptıktan sonra:
mst snapshot -o .msttools/sonra.json
mst compare .msttools/once.json .msttools/sonra.json
mst report -o .msttools/rapor.html
```

Raporu tarayıcıda açabilirsin. Aynı dosyaya tekrar kaydetmek için `--force` ekle.
Analiz puanı yalnızca belirtilen kontrolleri yansıtır; güvenlik garantisi değildir.
JWT imzayı doğrulamaz. Bağımlılık listesi güvenlik açığı taraması yapmaz.

Tüm seçenekler için [İngilizce kılavuza](README.md) bak.

## 1.2 yenilikleri

- Menüdeki örnek alan adları kaldırıldı.
- `validate`: JSON/TOML dosyalarının ve Python kodunun sözdizimini kontrol eder.
- `diff`: seçtiğin iki metin dosyasının satır farklarını renkli gösterir.
- `verify`: dosyanın SHA-256, SHA-384 veya SHA-512 değerini beklediğin değerle karşılaştırır.
- JSON biçimlendirme yinelenen anahtarları reddeder; Git durum sayımı düzeltildi.
- TLS testleri geçerli, güvenilmeyen ve süresi dolmuş yerel sertifikalarla gerçek bağlantı kurar.

Bir HTTP/TLS hedefinin erişilememesi, sunucunun veya bağlantının durumuna bağlı olabilir.
Hiçbir araç için tüm ortamlarda yüzde yüz hatasızlık garantisi verilmez.
