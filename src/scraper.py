"""
Resmi Gazete Web Scraper
Türkiye Resmi Gazete'den günlük içerikleri RSS feed üzerinden çeker.
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


@dataclass
class GazetteItem:
    """Resmi Gazete içerik öğesi"""
    title: str
    category: str
    link: str
    item_type: str = "htm"  # htm veya pdf


@dataclass
class GazetteData:
    """Günlük Resmi Gazete verisi"""
    date: str
    issue_number: str
    items: List[GazetteItem]
    url: str


class ResmiGazeteScraper:
    """Resmi Gazete web scraper sınıfı - RSS tabanlı"""

    BASE_URL = "https://www.resmigazete.gov.tr"

    # RSS Feed URL'leri
    RSS_URLS = [
        f"{BASE_URL}/rss/fihrist.xml",
        f"{BASE_URL}/rss/eskifihrist.xml",
    ]

    # Web scraping için yedek URL'ler
    WEB_URLS = [
        f"{BASE_URL}/default.aspx",
        f"{BASE_URL}/",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })

    def fetch_rss(self, max_retries: int = 3) -> Optional[str]:
        """RSS feed'i indir"""
        for rss_url in self.RSS_URLS:
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        delay = (2 ** attempt) + random.uniform(1, 2)
                        print(f"      Retry {attempt + 1}/{max_retries}, {delay:.1f}s bekleniyor...")
                        time.sleep(delay)

                    response = self.session.get(rss_url, timeout=30)
                    response.raise_for_status()
                    response.encoding = 'utf-8'
                    print(f"      RSS başarılı: {rss_url}")
                    return response.text

                except Exception as e:
                    print(f"      RSS hatası ({rss_url}): {type(e).__name__}")
                    continue

        return None

    def fetch_web(self, max_retries: int = 2) -> Optional[str]:
        """Web sayfasını indir (yedek yöntem)"""
        for web_url in self.WEB_URLS:
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        time.sleep(3)

                    response = self.session.get(web_url, timeout=45)
                    response.raise_for_status()
                    response.encoding = 'utf-8'
                    print(f"      Web başarılı: {web_url}")
                    return response.text

                except Exception as e:
                    print(f"      Web hatası ({web_url}): {type(e).__name__}")
                    continue

        return None

    def parse_rss(self, xml_content: str) -> GazetteData:
        """RSS XML içeriğini parse et"""
        items = []
        date_str = datetime.now().strftime('%d %B %Y')
        issue_number = "Bilinmiyor"

        try:
            root = ET.fromstring(xml_content)

            # Channel bilgilerini al
            channel = root.find('channel')
            if channel is not None:
                title_elem = channel.find('title')
                if title_elem is not None and title_elem.text:
                    # "Resmi Gazete - 04 Şubat 2026 - Sayı: 33158" formatı
                    title_text = title_elem.text

                    # Tarih çıkar
                    date_match = re.search(
                        r'(\d{1,2})\s+(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+(\d{4})',
                        title_text, re.IGNORECASE
                    )
                    if date_match:
                        date_str = date_match.group(0)

                    # Sayı çıkar
                    issue_match = re.search(r'Sayı\s*:\s*(\d+)', title_text)
                    if issue_match:
                        issue_number = issue_match.group(1)

            # Item'ları parse et
            current_category = "Genel"

            for item in root.findall('.//item'):
                title_elem = item.find('title')
                link_elem = item.find('link')
                category_elem = item.find('category')

                if title_elem is None or not title_elem.text:
                    continue

                title = title_elem.text.strip()
                link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""

                # Kategori
                if category_elem is not None and category_elem.text:
                    current_category = category_elem.text.strip()

                # Link yoksa veya çok kısa başlıksa atla
                if not link or len(title) < 5:
                    continue

                # Tam URL oluştur
                if not link.startswith('http'):
                    link = f"{self.BASE_URL}/{link.lstrip('/')}"

                item_type = 'pdf' if '.pdf' in link.lower() else 'htm'

                items.append(GazetteItem(
                    title=title,
                    category=current_category,
                    link=link,
                    item_type=item_type
                ))

        except ET.ParseError as e:
            print(f"      RSS parse hatası: {e}")

        return GazetteData(
            date=date_str,
            issue_number=issue_number,
            items=items,
            url=self.BASE_URL
        )

    def parse_web(self, html: str) -> GazetteData:
        """HTML içeriğini parse et (yedek yöntem)"""
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

        # Linkleri çek
        current_category = "Genel"
        category_keywords = [
            'YÜRÜTME VE İDARE BÖLÜMÜ', 'YASAMA BÖLÜMÜ', 'YARGI BÖLÜMÜ',
            'İLÂN BÖLÜMÜ', 'YÖNETMELİKLER', 'TEBLİĞLER', 'CUMHURBAŞKANLIĞI'
        ]

        for element in soup.find_all(['a', 'b', 'strong', 'h2', 'h3']):
            if element.name in ['b', 'strong', 'h2', 'h3']:
                elem_text = element.get_text(strip=True).upper()
                for kw in category_keywords:
                    if kw in elem_text:
                        current_category = element.get_text(strip=True)
                        break
                continue

            if element.name == 'a':
                href = element.get('href', '')
                title = element.get_text(strip=True)

                if not title or len(title) < 5:
                    continue

                if '.pdf' in href.lower() or '.htm' in href.lower():
                    if not href.startswith('http'):
                        href = f"{self.BASE_URL}/{href.lstrip('/')}"

                    item_type = 'pdf' if '.pdf' in href.lower() else 'htm'

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
        """Ana scraping fonksiyonu - önce RSS, sonra web"""

        # Önce RSS dene
        print("      RSS feed deneniyor...")
        rss_content = self.fetch_rss()
        if rss_content:
            data = self.parse_rss(rss_content)
            if data.items:
                return data
            print("      RSS'den içerik alınamadı, web deneniyor...")

        # RSS başarısızsa web dene
        print("      Web scraping deneniyor...")
        web_content = self.fetch_web()
        if web_content:
            return self.parse_web(web_content)

        # Her ikisi de başarısızsa boş döndür
        raise Exception("Ne RSS ne de web erişimi başarılı olmadı")


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
                    title_short = item.title[:60] + "..." if len(item.title) > 60 else item.title
                    print(f"  - {title_short} [{item.item_type.upper()}]")

    except Exception as e:
        print(f"Hata: {e}")


if __name__ == "__main__":
    main()
