"""
Resmi Gazete İçerik Filtresi
İstenmeyen içerikleri akıllı regex pattern'ler ile filtreler.
"""

import re
from dataclasses import dataclass
from typing import List, Tuple
from scraper import GazetteItem


@dataclass
class FilterResult:
    """Filtreleme sonucu"""
    kept_items: List[GazetteItem]
    filtered_items: List[GazetteItem]
    filter_summary: dict


class GazetteFilter:
    """Resmi Gazete içerik filtresi"""

    # Üniversite/Fakülte ile ilgili içerikler
    UNIVERSITY_PATTERN = re.compile(
        r'üniversite|fakülte|enstitü|yüksekokul|rektör|dekan|akademik|öğretim üyesi|doçent|profesör',
        re.IGNORECASE
    )

    # Merkez Bankası döviz/kur haberleri
    CENTRAL_BANK_PATTERN = re.compile(
        r'merkez bankası|döviz kur|devlet iç borçlanma',
        re.IGNORECASE
    )

    # Filtrelenecek kategoriler (tam veya kısmi eşleşme)
    FILTERED_CATEGORY_PATTERNS = [
        r'YARGI\s*İL[AÂ]N',
        r'ARTIRMA.*EKSİLTME',
        r'ÇEŞİTLİ\s*İL[AÂ]N',
        r'İL[AÂ]N\s*BÖLÜMÜ',
    ]

    # Filtrelenecek başlık pattern'leri
    FILTERED_TITLE_PATTERNS = [
        r'^a\s*-\s*Yargı',
        r'^b\s*-\s*Artırma',
        r'^c\s*-\s*Çeşitli',
        r'Yargı\s*İl[aâ]nları',
        r'Artırma.*Eksiltme.*İl[aâ]n',
        r'Çeşitli\s*İl[aâ]nlar',
        r'Merkez\s*Bankası.*Döviz',
        r'Devlet\s*İç\s*Borçlanma',
    ]

    def __init__(self, filter_universities: bool = True,
                 filter_announcements: bool = True,
                 filter_central_bank: bool = True):
        """
        Filtre yapılandırması

        Args:
            filter_universities: Üniversite içeriklerini filtrele
            filter_announcements: İlan bölümlerini filtrele
            filter_central_bank: Merkez Bankası döviz haberlerini filtrele
        """
        self.filter_universities = filter_universities
        self.filter_announcements = filter_announcements
        self.filter_central_bank = filter_central_bank

        # Compiled patterns
        self.category_patterns = [re.compile(p, re.IGNORECASE) for p in self.FILTERED_CATEGORY_PATTERNS]
        self.title_patterns = [re.compile(p, re.IGNORECASE) for p in self.FILTERED_TITLE_PATTERNS]

    def should_filter(self, item: GazetteItem) -> Tuple[bool, str]:
        """
        Öğenin filtrelenmesi gerekip gerekmediğini kontrol et

        Returns:
            (should_filter, reason) tuple
        """
        title = item.title
        category = item.category

        # 1. İlan bölümü filtrelemesi (kategori bazlı)
        if self.filter_announcements:
            for pattern in self.category_patterns:
                if pattern.search(category):
                    return True, "İlan bölümü"

        # 2. İlan bölümü filtrelemesi (başlık bazlı)
        if self.filter_announcements:
            for pattern in self.title_patterns:
                if pattern.search(title):
                    return True, "İlan içeriği"

        # 3. Üniversite içerikleri
        if self.filter_universities:
            if self.UNIVERSITY_PATTERN.search(title):
                return True, "Üniversite/Akademik"

        # 4. Merkez Bankası döviz haberleri
        if self.filter_central_bank:
            if self.CENTRAL_BANK_PATTERN.search(title):
                return True, "Merkez Bankası/Döviz"

        return False, ""

    def filter_items(self, items: List[GazetteItem]) -> FilterResult:
        """
        İçerik listesini filtrele

        Args:
            items: Filtrelenecek öğeler

        Returns:
            FilterResult nesnesi
        """
        kept = []
        filtered = []
        filter_reasons = {}

        for item in items:
            should_filter, reason = self.should_filter(item)

            if should_filter:
                filtered.append(item)
                if reason not in filter_reasons:
                    filter_reasons[reason] = 0
                filter_reasons[reason] += 1
            else:
                kept.append(item)

        return FilterResult(
            kept_items=kept,
            filtered_items=filtered,
            filter_summary=filter_reasons
        )

    def get_filter_stats(self, result: FilterResult) -> str:
        """Filtreleme istatistiklerini metin olarak döndür"""
        total = len(result.kept_items) + len(result.filtered_items)
        filtered_count = len(result.filtered_items)

        if filtered_count == 0:
            return ""

        lines = [f"({filtered_count}/{total} içerik filtrelendi)"]

        for reason, count in result.filter_summary.items():
            lines.append(f"  - {reason}: {count}")

        return "\n".join(lines)


def main():
    """Test fonksiyonu"""
    # Test verileri
    test_items = [
        GazetteItem("Hâkimler ve Savcılar Kuruluna Ait Karar", "HÂKİMLER VE SAVCILAR KURULU KARARI", "http://test.com/1.pdf"),
        GazetteItem("İstanbul Üniversitesi Yönetmeliği", "YÖNETMELİKLER", "http://test.com/2.pdf"),
        GazetteItem("Dip Tarama Malzemesi Yönetmeliği", "YÖNETMELİKLER", "http://test.com/3.htm"),
        GazetteItem("T.C. Merkez Bankasınca Belirlenen Döviz Kurları", "TEBLİĞLER", "http://test.com/4.htm"),
        GazetteItem("Özelleştirme İdaresi Kararı", "TEBLİĞLER", "http://test.com/5.pdf"),
        GazetteItem("a - Yargı İlânları", "İLÂN BÖLÜMÜ", "http://test.com/6.htm"),
        GazetteItem("b - Artırma, Eksiltme ve İhale İlânları", "İLÂN BÖLÜMÜ", "http://test.com/7.htm"),
        GazetteItem("c - Çeşitli İlânlar", "İLÂN BÖLÜMÜ", "http://test.com/8.htm"),
        GazetteItem("Vergi Kanunu Değişikliği", "YASAMA BÖLÜMÜ", "http://test.com/9.htm"),
    ]

    filter_obj = GazetteFilter()
    result = filter_obj.filter_items(test_items)

    print("=== FİLTRELEME TEST SONUÇLARI ===\n")

    print(f"✓ Korunan içerikler ({len(result.kept_items)}):")
    for item in result.kept_items:
        print(f"   [{item.category}] {item.title}")

    print(f"\n✗ Filtrelenen içerikler ({len(result.filtered_items)}):")
    for item in result.filtered_items:
        print(f"   [{item.category}] {item.title}")

    print(f"\n{filter_obj.get_filter_stats(result)}")


if __name__ == "__main__":
    main()
