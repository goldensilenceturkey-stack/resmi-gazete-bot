"""
Resmi Gazete Web Scraper
Türkiye Resmi Gazete'den günlük içerikleri çeker ve parse eder.
"""

import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import re
import time
import random


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
    """Resmi Gazete web scraper sınıfı"""

    BASE_URL = "https://www.resmigazete.gov.tr"
    DEFAULT_URL = f"{BASE_URL}/default.aspx"

    # Alternatif URL'ler
    ALT_URLS = [
        f"{BASE_URL}/default.aspx",
        f"{BASE_URL}/",
        f"{BASE_URL}/eskiler/index.htm",
    ]

    def __init__(self):
        self.session = requests.Session()
        # Daha gerçekçi browser headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })

    def fetch_page(self, url: Optional[str] = None, max_retries: int = 3) -> str:
        """Sayfayı indir - retry mantığı ile"""
        target_url = url or self.DEFAULT_URL
        last_error = None

        for attempt in range(max_retries):
            try:
                # Random delay ekle (bot algılamayı önlemek için)
                if attempt > 0:
                    delay = (2 ** attempt) + random.uniform(1, 3)
                    print(f"      Retry {attempt + 1}/{max_retries}, {delay:.1f}s bekleniyor...")
                    time.sleep(delay)

                response = self.session.get(
                    target_url,
                    timeout=60,  # Timeout artırıldı
                    allow_redirects=True
                )
                response.raise_for_status()
                response.encoding = 'utf-8'
                return response.text

            except requests.exceptions.Timeout as e:
                last_error = e
                print(f"      Timeout hatası (deneme {attempt + 1})")
            except requests.exceptions.ConnectionError as e:
                last_error = e
                print(f"      Bağlantı hatası (deneme {attempt + 1})")
            except requests.exceptions.RequestException as e:
                last_error = e
                print(f"      İstek hatası (deneme {attempt + 1}): {e}")

        # Alternatif URL'leri dene
        print("      Ana URL başarısız, alternatif URL'ler deneniyor...")
        for alt_url in self.ALT_URLS:
            if alt_url == target_url:
                continue
            try:
                time.sleep(random.uniform(2, 4))
                response = self.session.get(alt_url, timeout=60, allow_redirects=True)
                response.raise_for_status()
                response.encoding = 'utf-8'
                print(f"      Alternatif URL başarılı: {alt_url}")
                return response.text
            except Exception as e:
                print(f"      Alternatif URL başarısız: {alt_url}")
                continue

        raise last_error or Exception("Tüm bağlantı denemeleri başarısız")

    def parse_gazette(self, html: str) -> GazetteData:
        """HTML içeriğini parse et"""
        soup = BeautifulSoup(html, 'html.parser')

        # Tarih ve sayı bilgisini al
        date_info = self._extract_date_info(soup)

        # İçerikleri kategorilere göre çek
        items = self._extract_items(soup)

        return GazetteData(
            date=date_info.get('date', datetime.now().strftime('%d %B %Y')),
            issue_number=date_info.get('issue_number', 'Bilinmiyor'),
            items=items,
            url=self.DEFAULT_URL
        )

    def _extract_date_info(self, soup: BeautifulSoup) -> dict:
        """Tarih ve sayı bilgisini çıkar"""
        info = {'date': '', 'issue_number': ''}

        # Sayı bilgisini ara
        # Genellikle "Sayı : 33158" formatında
        text = soup.get_text()

        # Sayı pattern
        issue_match = re.search(r'Sayı\s*:\s*(\d+)', text)
        if issue_match:
            info['issue_number'] = issue_match.group(1)

        # Tarih pattern - Türkçe aylar
        date_patterns = [
            r'(\d{1,2})\s+(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+(\d{4})',
        ]

        for pattern in date_patterns:
            date_match = re.search(pattern, text, re.IGNORECASE)
            if date_match:
                info['date'] = date_match.group(0)
                break

        return info

    def _extract_items(self, soup: BeautifulSoup) -> List[GazetteItem]:
        """Tüm içerik öğelerini çıkar"""
        items = []
        current_category = "Genel"

        # Ana içerik alanını bul
        content_area = soup.find('div', {'id': 'mainContent'}) or soup.find('body')

        if not content_area:
            return items

        # Tüm linkleri tara
        for element in content_area.find_all(['a', 'h2', 'h3', 'b', 'strong']):
            # Kategori başlığı kontrolü
            if element.name in ['h2', 'h3', 'b', 'strong']:
                text = element.get_text(strip=True)
                if self._is_category_header(text):
                    current_category = text
                continue

            # Link kontrolü
            if element.name == 'a':
                href = element.get('href', '')
                title = element.get_text(strip=True)

                # Boş veya çok kısa başlıkları atla
                if not title or len(title) < 5:
                    continue

                # PDF veya HTM linklerini al
                if '.pdf' in href.lower() or '.htm' in href.lower():
                    # Tam URL oluştur
                    if not href.startswith('http'):
                        href = f"{self.BASE_URL}/{href.lstrip('/')}"

                    item_type = 'pdf' if '.pdf' in href.lower() else 'htm'

                    items.append(GazetteItem(
                        title=title,
                        category=current_category,
                        link=href,
                        item_type=item_type
                    ))

        # Alternatif parsing - tablo yapısı için
        if not items:
            items = self._parse_table_structure(soup)

        return items

    def _is_category_header(self, text: str) -> bool:
        """Kategori başlığı mı kontrol et"""
        category_keywords = [
            'YÜRÜTME VE İDARE BÖLÜMÜ',
            'YASAMA BÖLÜMÜ',
            'YARGI BÖLÜMÜ',
            'İLÂN BÖLÜMÜ',
            'MİLLETLERARASI ANDLAŞMALAR',
            'CUMHURBAŞKANLIĞI',
            'BAKANLAR KURULU',
            'YÖNETMELİKLER',
            'TEBLİĞLER',
            'YARGI İLÂNLARI',
            'ARTIRMA, EKSİLTME',
            'ÇEŞİTLİ İLÂNLAR',
        ]

        text_upper = text.upper()
        return any(keyword in text_upper for keyword in category_keywords)

    def _parse_table_structure(self, soup: BeautifulSoup) -> List[GazetteItem]:
        """Tablo yapısındaki içerikleri parse et"""
        items = []
        current_category = "Genel"

        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cells = row.find_all(['td', 'th'])

                for cell in cells:
                    # Kategori kontrolü
                    bold = cell.find(['b', 'strong'])
                    if bold:
                        text = bold.get_text(strip=True)
                        if self._is_category_header(text):
                            current_category = text

                    # Link kontrolü
                    for link in cell.find_all('a'):
                        href = link.get('href', '')
                        title = link.get_text(strip=True)

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

        return items

    def scrape(self, url: Optional[str] = None) -> GazetteData:
        """Ana scraping fonksiyonu"""
        html = self.fetch_page(url)
        return self.parse_gazette(html)


def main():
    """Test fonksiyonu"""
    scraper = ResmiGazeteScraper()

    try:
        data = scraper.scrape()
        print(f"Tarih: {data.date}")
        print(f"Sayı: {data.issue_number}")
        print(f"Toplam içerik: {len(data.items)}")
        print("\nKategoriler:")

        categories = {}
        for item in data.items:
            if item.category not in categories:
                categories[item.category] = []
            categories[item.category].append(item)

        for cat, cat_items in categories.items():
            print(f"\n{cat} ({len(cat_items)} öğe)")
            for item in cat_items[:3]:  # Her kategoriden ilk 3
                print(f"  - {item.title[:60]}... [{item.item_type.upper()}]")

    except Exception as e:
        print(f"Hata: {e}")


if __name__ == "__main__":
    main()
