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
import xml.etree.ElementTree as ET
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

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
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

                # UTF-8 encoding zorla
                response.encoding = 'utf-8'
                content = response.text

                # Encoding düzeltme - mojibake fix
                try:
                    # Eğer yanlış decode edilmişse düzelt
                    if 'Ã' in content or 'Ä' in content:
                        content = content.encode('latin-1').decode('utf-8')
                except:
                    pass

                # İçeriğin gerçekten Resmi Gazete olduğunu kontrol et
                if 'resmi' in content.lower() or 'gazete' in content.lower() or 'sayı' in content.lower():
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
        """Direkt bağlantı dene (lokal test için)"""
        try:
            response = self.session.get(target_url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            print("      Direkt bağlantı başarılı!")
            return response.text
        except Exception as e:
            print(f"      Direkt bağlantı başarısız: {type(e).__name__}")
            return None

    def parse_html(self, html: str) -> GazetteData:
        """HTML içeriğini parse et"""
        soup = BeautifulSoup(html, 'html.parser')
        items = []

        # Tarih ve sayı bilgisini al
        text = soup.get_text()
        date_str = datetime.now().strftime('%d %B %Y')
        issue_number = "Bilinmiyor"

        # Türkçe tarih pattern
        date_match = re.search(
            r'(\d{1,2})\s+(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+(\d{4})',
            text, re.IGNORECASE
        )
        if date_match:
            date_str = date_match.group(0)

        # Sayı pattern
        issue_match = re.search(r'Sayı\s*:\s*(\d+)', text)
        if issue_match:
            issue_number = issue_match.group(1)

        # Kategorileri ve linkleri çek
        current_category = "Genel"
        category_keywords = [
            'YÜRÜTME VE İDARE BÖLÜMÜ', 'YASAMA BÖLÜMÜ', 'YARGI BÖLÜMÜ',
            'İLÂN BÖLÜMÜ', 'MİLLETLERARASI', 'YÖNETMELİKLER', 'TEBLİĞLER',
            'CUMHURBAŞKANLIĞI', 'BAKANLIKLAR', 'GENELGE', 'KANUN',
            'CUMHURBAŞKANLIĞI KARARLARI', 'ATAMA KARARLARI'
        ]

        # Tüm elementleri tara
        for element in soup.find_all(['a', 'b', 'strong', 'h1', 'h2', 'h3', 'td', 'span']):
            elem_text = element.get_text(strip=True)

            # Kategori başlığı kontrolü
            if element.name in ['b', 'strong', 'h1', 'h2', 'h3', 'td', 'span']:
                elem_upper = elem_text.upper()
                for kw in category_keywords:
                    if kw in elem_upper and len(elem_text) < 100:
                        current_category = elem_text
                        break

            # Link kontrolü
            if element.name == 'a':
                href = element.get('href', '')
                title = elem_text

                if not title or len(title) < 5:
                    continue

                # PDF veya HTM linkleri
                href_lower = href.lower()
                if '.pdf' in href_lower or '.htm' in href_lower:
                    # Tam URL oluştur
                    if not href.startswith('http'):
                        if href.startswith('/'):
                            href = f"{self.BASE_URL}{href}"
                        else:
                            href = f"{self.BASE_URL}/{href}"

                    item_type = 'pdf' if '.pdf' in href_lower else 'htm'

                    # Duplicate kontrolü
                    if not any(item.link == href for item in items):
                        items.append(GazetteItem(
                            title=title,
                            category=current_category,
                            link=href,
                            item_type=item_type
                        ))

        return GazetteData(
            date=date_str,
            issue_number=issue_number,
            items=items,
            url=self.BASE_URL
        )

    def scrape(self) -> GazetteData:
        """Ana scraping fonksiyonu"""

        # Önce direkt bağlantı dene (lokal çalışma için)
        print("      Direkt bağlantı deneniyor...")
        content = self.fetch_direct(self.TARGET_URL)

        # Direkt başarısızsa proxy dene
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
            print("\nKategoriler:")
            categories = {}
            for item in data.items:
                if item.category not in categories:
                    categories[item.category] = []
                categories[item.category].append(item)

            for cat, cat_items in categories.items():
                print(f"\n{cat} ({len(cat_items)} öğe)")
                for item in cat_items[:3]:
                    title_short = item.title[:55] + "..." if len(item.title) > 55 else item.title
                    print(f"  - {title_short} [{item.item_type.upper()}]")
        else:
            print("\nUYARI: Hiç içerik bulunamadı!")

    except Exception as e:
        print(f"Hata: {e}")


if __name__ == "__main__":
    main()
