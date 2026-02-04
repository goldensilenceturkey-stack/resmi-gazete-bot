"""
Resmi Gazete Web Scraper
Türkiye Resmi Gazete'den günlük içerikleri proxy üzerinden çeker.
"""

import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import re
import time
import random
from urllib.parse import quote


@dataclass
class GazetteItem:
    """Resmi Gazete içerik öğesi"""
    title: str
    category: str
    link: str
    item_type: str = "htm"


@dataclass
class GazetteData:
    """Günlük Resmi Gazete verisi"""
    date: str
    issue_number: str
    items: List[GazetteItem]
    url: str


class ResmiGazeteScraper:
    """Resmi Gazete web scraper - proxy destekli"""

    BASE_URL = "https://www.resmigazete.gov.tr"
    TARGET_URL = f"{BASE_URL}/default.aspx"

    # Ücretsiz proxy servisleri
    PROXY_SERVICES = [
        lambda url: f"https://api.allorigins.win/raw?url={quote(url, safe='')}",
        lambda url: f"https://api.codetabs.com/v1/proxy?quest={quote(url, safe='')}",
        lambda url: f"https://corsproxy.io/?{quote(url, safe='')}",
    ]

    # Filtrelenecek başlıklar (scraper seviyesinde)
    SKIP_TITLES = [
        'pdf görüntüle', 'htm görüntüle', 'görüntüle', 'yazdır',
        'ana sayfa', 'iletişim', 'arama', 'arşiv', 'önceki sayı',
        'tüm kategoriler', 'zaman aralığı', 'son mükerrer', 'fihrist'
    ]

    # Kategori başlıkları (büyük-küçük harf duyarsız)
    CATEGORY_HEADERS = [
        'YÜRÜTME VE İDARE BÖLÜMÜ',
        'YASAMA BÖLÜMÜ',
        'YARGI BÖLÜMÜ',
        'İLÂN BÖLÜMÜ',
        'İLAN BÖLÜMÜ',
        'MİLLETLERARASI ANDLAŞMALAR',
        'HÂKİMLER VE SAVCILAR KURULU KARARI',
        'HÂKİMLER VE SAVCILAR KURULU',
        'HAKIMLER VE SAVCILAR KURULU',
        'CUMHURBAŞKANLIĞI KARARLARI',
        'CUMHURBAŞKANLIĞI',
        'BAKANLAR KURULU KARARLARI',
        'YÖNETMELİKLER',
        'TEBLİĞLER',
        'GENELGELER',
        'KANUNLAR',
        'KANUN HÜKMÜNDE KARARNAME',
        'ATAMA KARARLARI',
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
        })

    def fetch_via_proxy(self, target_url: str) -> Optional[str]:
        """Proxy servisleri üzerinden içerik çek"""

        for i, proxy_fn in enumerate(self.PROXY_SERVICES):
            proxy_url = proxy_fn(target_url)
            print(f"      Proxy {i + 1}/{len(self.PROXY_SERVICES)} deneniyor...")

            try:
                response = self.session.get(proxy_url, timeout=45)
                response.raise_for_status()

                response.encoding = 'utf-8'
                content = response.text

                # Encoding düzeltme
                try:
                    if 'Ã' in content or 'Ä' in content:
                        content = content.encode('latin-1').decode('utf-8')
                except:
                    pass

                if 'resmi' in content.lower() or 'gazete' in content.lower():
                    print(f"      Proxy {i + 1} başarılı!")
                    return content
                else:
                    print(f"      Proxy {i + 1}: Geçersiz içerik")

            except requests.exceptions.Timeout:
                print(f"      Proxy {i + 1}: Timeout")
            except requests.exceptions.RequestException as e:
                print(f"      Proxy {i + 1}: {type(e).__name__}")

            time.sleep(random.uniform(1, 2))

        return None

    def fetch_direct(self, target_url: str) -> Optional[str]:
        """Direkt bağlantı dene"""
        try:
            response = self.session.get(target_url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            print("      Direkt bağlantı başarılı!")
            return response.text
        except Exception as e:
            print(f"      Direkt bağlantı başarısız: {type(e).__name__}")
            return None

    def _should_skip_title(self, title: str) -> bool:
        """Bu başlık atlanmalı mı?"""
        title_lower = title.lower().strip()

        if len(title_lower) < 5:
            return True

        for skip in self.SKIP_TITLES:
            if skip in title_lower:
                return True

        if not any(c.isalpha() for c in title):
            return True

        return False

    def _normalize_text(self, text: str) -> str:
        """Türkçe karakterleri normalize et"""
        replacements = {
            'İ': 'I', 'Ğ': 'G', 'Ü': 'U', 'Ş': 'S', 'Ö': 'O', 'Ç': 'C',
            'ı': 'I', 'ğ': 'G', 'ü': 'U', 'ş': 'S', 'ö': 'O', 'ç': 'C',
            'Â': 'A', 'â': 'A', 'Î': 'I', 'î': 'I', 'Û': 'U', 'û': 'U',
        }
        result = text.upper()
        for old, new in replacements.items():
            result = result.replace(old, new)
        return result

    def _is_category_header(self, text: str) -> Optional[str]:
        """Metin bir kategori başlığı mı? Eşleşen kategoriyi döndür."""
        text = text.strip()
        if len(text) < 5 or len(text) > 100:
            return None

        text_normalized = self._normalize_text(text)

        for cat in self.CATEGORY_HEADERS:
            cat_normalized = self._normalize_text(cat)
            if cat_normalized in text_normalized:
                return text

        return None

    def parse_html(self, html: str) -> GazetteData:
        """HTML içeriğini parse et"""
        soup = BeautifulSoup(html, 'html.parser')
        items = []

        # Tarih ve sayı bilgisini al
        text = soup.get_text()
        date_str = datetime.now().strftime('%d %B %Y')
        issue_number = "Bilinmiyor"

        date_match = re.search(
            r'(\d{1,2})\s+(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+(\d{4})',
            text, re.IGNORECASE
        )
        if date_match:
            date_str = date_match.group(0)

        issue_match = re.search(r'Sayı\s*:\s*(\d+)', text)
        if issue_match:
            issue_number = issue_match.group(1)

        # HTML'deki tüm text içeriğini satır satır işle
        # ve kategorileri linklerden önce yakala
        current_category = "Genel"

        # Önce tüm bold/underline elementleri bul ve kategorileri belirle
        all_elements = soup.find_all(['b', 'strong', 'u', 'a'])

        # Her element için index tut
        element_categories = {}

        for i, elem in enumerate(all_elements):
            elem_text = elem.get_text(strip=True)

            # Link ise ve PDF/HTM ise ekle
            if elem.name == 'a':
                href = elem.get('href', '')
                title = elem_text

                if self._should_skip_title(title):
                    continue

                href_lower = href.lower()
                if '.pdf' in href_lower or '.htm' in href_lower:
                    if 'default.aspx' in href_lower:
                        continue

                    # Tam URL oluştur
                    if not href.startswith('http'):
                        if href.startswith('/'):
                            href = f"{self.BASE_URL}{href}"
                        else:
                            href = f"{self.BASE_URL}/{href}"

                    item_type = 'pdf' if '.pdf' in href_lower else 'htm'

                    # Her içerik için başlığa göre kategori belirle
                    category = self._get_category_from_title(title)

                    # Duplicate kontrolü
                    if not any(item.link == href for item in items):
                        items.append(GazetteItem(
                            title=title,
                            category=category,
                            link=href,
                            item_type=item_type
                        ))

        return GazetteData(
            date=date_str,
            issue_number=issue_number,
            items=items,
            url=self.BASE_URL
        )

    def _get_category_from_title(self, title: str) -> str:
        """Başlığa göre kategori belirle"""
        title_upper = self._normalize_text(title)

        if 'HAKIM' in title_upper or 'SAVCI' in title_upper:
            return "HÂKİMLER VE SAVCILAR KURULU KARARI"
        elif 'YONETMELIK' in title_upper:
            return "YÖNETMELİKLER"
        elif 'OZELLESTIRME' in title_upper:
            return "TEBLİĞLER"
        elif 'TEBLIG' in title_upper:
            return "TEBLİĞLER"
        elif 'KANUN' in title_upper:
            return "YASAMA BÖLÜMÜ"
        elif 'CUMHURBASKANI' in title_upper or 'CUMHURBASKANLIGI' in title_upper:
            return "CUMHURBAŞKANLIĞI KARARLARI"
        elif 'GENELGE' in title_upper:
            return "GENELGELER"
        elif 'ILAN' in title_upper or 'IHALE' in title_upper:
            return "İLÂN BÖLÜMÜ"
        elif 'YARGI' in title_upper:
            return "İLÂN BÖLÜMÜ"
        elif 'MERKEZ BANKASI' in title_upper or 'DOVIZ' in title_upper:
            return "TEBLİĞLER"
        else:
            return "Diğer"

    def scrape(self) -> GazetteData:
        """Ana scraping fonksiyonu"""

        print("      Direkt bağlantı deneniyor...")
        content = self.fetch_direct(self.TARGET_URL)

        if not content:
            print("      Proxy servisleri deneniyor...")
            content = self.fetch_via_proxy(self.TARGET_URL)

        if not content:
            raise Exception("Hiçbir yöntemle içerik alınamadı")

        return self.parse_html(content)


def main():
    """Test fonksiyonu"""
    scraper = ResmiGazeteScraper()

    try:
        data = scraper.scrape()
        print(f"\nTarih: {data.date}")
        print(f"Sayı: {data.issue_number}")
        print(f"Toplam içerik: {len(data.items)}")

        if data.items:
            print("\nİçerikler (kategorilere göre):")
            categories = {}
            for item in data.items:
                if item.category not in categories:
                    categories[item.category] = []
                categories[item.category].append(item)

            for cat, cat_items in categories.items():
                print(f"\n📁 {cat} ({len(cat_items)} öğe)")
                for item in cat_items[:5]:
                    title_short = item.title[:55] + "..." if len(item.title) > 55 else item.title
                    print(f"   - {title_short} [{item.item_type.upper()}]")
        else:
            print("\nUYARI: Hiç içerik bulunamadı!")

    except Exception as e:
        print(f"Hata: {e}")


if __name__ == "__main__":
    main()
