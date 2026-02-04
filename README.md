# Resmi Gazete Takip Botu

Türkiye Resmi Gazete'yi günlük takip eden, akıllı filtreleme ile önemli içerikleri e-posta olarak gönderen otomasyon sistemi.

## Özellikler

- **Günlük Otomatik Takip**: Her gün Türkiye saati 09:00'da çalışır
- **Akıllı Filtreleme**: Üniversite yönetmelikleri, ilan bölümleri ve rutin döviz haberlerini filtreler
- **Şık HTML E-posta**: Kategorilere göre gruplandırılmış, tıklanabilir linklerle düzenli format
- **Ücretsiz Altyapı**: GitHub Actions + SendGrid (ayda 100 e-posta ücretsiz)

## Filtrelenen İçerikler

| Tür | Açıklama |
|-----|----------|
| Üniversite/Akademik | Üniversite, fakülte, enstitü, yüksekokul yönetmelikleri |
| İlan Bölümleri | Yargı ilanları, artırma-eksiltme, çeşitli ilanlar |
| Merkez Bankası | Günlük döviz kuru tebliğleri |

## Kurulum

### 1. GitHub Repository Oluşturma

```bash
# Bu klasörü kendi GitHub hesabınıza yükleyin
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/KULLANICI/resmi-gazete-bot.git
git push -u origin main
```

### 2. SendGrid Hesabı

1. [sendgrid.com](https://sendgrid.com) adresine gidin
2. Ücretsiz hesap oluşturun
3. **Settings > API Keys** bölümünden yeni bir API key oluşturun
4. **Settings > Sender Authentication** bölümünden gönderici e-posta adresinizi doğrulayın

### 3. GitHub Secrets Ayarlama

Repository sayfanızda: **Settings > Secrets and variables > Actions**

Şu secrets'ları ekleyin:

| Secret | Açıklama |
|--------|----------|
| `SENDGRID_API_KEY` | SendGrid API anahtarınız |
| `TO_EMAIL` | E-posta alacak adres (örn: av.saimincekas@gmail.com) |
| `FROM_EMAIL` | Gönderen adres (SendGrid'de doğrulanmış olmalı) |

### 4. Workflow'u Aktifleştirme

Repository'de **Actions** sekmesine gidin ve workflow'u aktifleştirin.

## Kullanım

### Otomatik Çalışma

Bot her gün UTC 06:00'da (Türkiye saati 09:00) otomatik olarak çalışır.

### Manuel Tetikleme

1. GitHub repository'de **Actions** sekmesine gidin
2. **Resmi Gazete Günlük Takip** workflow'unu seçin
3. **Run workflow** butonuna tıklayın
4. Test modu için `dry_run: true` seçin

### Lokal Test

```bash
# Bağımlılıkları yükle
pip install -r requirements.txt

# .env dosyası oluştur
cp .env.example .env
# .env dosyasını düzenleyip değerleri girin

# Test modu (e-posta göndermez)
cd src
python main.py --dry-run --verbose

# Gerçek çalıştırma
python main.py --verbose
```

## Proje Yapısı

```
resmi-gazete-bot/
├── src/
│   ├── scraper.py         # Web scraping modülü
│   ├── filter.py          # Akıllı filtreleme mantığı
│   ├── email_sender.py    # SendGrid e-posta gönderimi
│   └── main.py            # Ana çalıştırıcı
├── .github/
│   └── workflows/
│       └── daily.yml      # GitHub Actions workflow
├── requirements.txt       # Python bağımlılıkları
├── .env.example          # Örnek environment dosyası
└── README.md
```

## Filtreleme Özelleştirme

`src/filter.py` dosyasında filtreleme ayarlarını değiştirebilirsiniz:

```python
gazette_filter = GazetteFilter(
    filter_universities=True,      # Üniversite içerikleri
    filter_announcements=True,     # İlan bölümleri
    filter_central_bank=True,      # MB döviz haberleri
    filter_appointments=False      # Atama ilanları
)
```

## E-posta Örneği

```
Konu: Resmi Gazete - 04 Şubat 2026 (Sayı: 33158)

🏛️ YÜRÜTME VE İDARE BÖLÜMÜ
━━━━━━━━━━━━━━━━━━━━━━━━━
• Hâkimler ve Savcılar Kurulu Kararı [PDF]
• Özelleştirme İdaresi Kararı [PDF]

⚖️ YASAMA BÖLÜMÜ
━━━━━━━━━━━━━━━━━━━━━━━━━
• Vergi Kanunu Değişikliği [HTM]

(15 içerik filtrelendi: Üniversite yönetmelikleri, ilan bölümleri)

🔗 Tam Gazete: https://www.resmigazete.gov.tr/
```

## Sorun Giderme

### E-posta gelmiyor

1. GitHub Actions loglarını kontrol edin
2. SendGrid API key'in doğru olduğunu kontrol edin
3. SendGrid hesabınızda gönderici e-postanın doğrulandığını kontrol edin
4. Spam klasörünü kontrol edin

### Scraping hatası

Resmi Gazete web sitesinin yapısı değiştiyse, `src/scraper.py` dosyasını güncellemeniz gerekebilir.

## Lisans

MIT License
