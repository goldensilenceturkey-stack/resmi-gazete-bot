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
        r'merkez bankası.{0,30}(döviz|kur|efektif|parite)',
        re.IGNORECASE
    )

    # Filtrelenecek kategoriler
    FILTERED_CATEGORIES = [
        'YARGI İLÂNLARI',
        'YARGIILANLARI',
        'YARGI ILANLARI',
        'ARTIRMA, EKSİLTME',
        'ARTIRMA EKSİLTME',
        'ARTIRMA,EKSİLTME',
        'ÇEŞİTLİ İLÂNLAR',
        'ÇEŞİTLİ ILANLAR',
        'CESITLI ILANLAR',
    ]

    # Atama/kadro ilanları pattern
    APPOINTMENT_PATTERN = re.compile(
        r'atama|kadro|münhal|personel alımı|sözleşmeli personel',
        re.IGNORECASE
    )

    def __init__(self, filter_universities: bool = True,
                 filter_announcements: bool = True,
                 filter_central_bank: bool = True,
                 filter_appointments: bool = False):
        """
        Filtre yapılandırması

        Args:
            filter_universities: Üniversite içeriklerini filtrele
            filter_announcements: İlan bölümlerini filtrele
            filter_central_bank: Merkez Bankası döviz haberlerini filtrele
            filter_appointments: Atama/kadro ilanlarını filtrele
        """
        self.filter_universities = filter_universities
        self.filter_announcements = filter_announcements
        self.filter_central_bank = filter_central_bank
        self.filter_appointments = filter_appointments

    def should_filter(self, item: GazetteItem) -> Tuple[bool, str]:
        """
        Öğenin filtrelenmesi gerekip gerekmediğini kontrol et

        Returns:
            (should_filter, reason) tuple
        """
        # Kategori bazlı filtreleme
        if self.filter_announcements:
            category_upper = item.category.upper()
            # Türkçe karakterleri normalize et
            category_normalized = self._normalize_turkish(category_upper)

            for filtered_cat in self.FILTERED_CATEGORIES:
                filtered_normalized = self._normalize_turkish(filtered_cat.upper())
                if filtered_normalized in category_normalized or category_normalized in filtered_normalized:
                    return True, f"İlan kategorisi: {item.category}"

        # Üniversite içerikleri
        if self.filter_universities:
            if self.UNIVERSITY_PATTERN.search(item.title):
                return True, "Üniversite/Akademik içerik"

        # Merkez Bankası döviz haberleri
        if self.filter_central_bank:
            if self.CENTRAL_BANK_PATTERN.search(item.title):
                return True, "Merkez Bankası döviz/kur"

        # Atama/kadro ilanları
        if self.filter_appointments:
            if self.APPOINTMENT_PATTERN.search(item.title):
                return True, "Atama/Kadro ilanı"

        return False, ""

    def _normalize_turkish(self, text: str) -> str:
        """Türkçe karakterleri normalize et"""
        replacements = {
            'İ': 'I', 'Ğ': 'G', 'Ü': 'U', 'Ş': 'S', 'Ö': 'O', 'Ç': 'C',
            'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c',
            'Â': 'A', 'â': 'a', 'Î': 'I', 'î': 'i', 'Û': 'U', 'û': 'u',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

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
                # Filtreleme nedenlerini say
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
        GazetteItem("Hâkimler ve Savcılar Kurulu Kararı", "YÜRÜTME VE İDARE BÖLÜMÜ", "http://test.com/1.pdf"),
        GazetteItem("İstanbul Üniversitesi Yönetmeliği", "YÖNETMELİKLER", "http://test.com/2.pdf"),
        GazetteItem("Ankara Üniversitesi Fakülte Yönetmeliği", "YÖNETMELİKLER", "http://test.com/3.pdf"),
        GazetteItem("Merkez Bankası Döviz Kurları", "TEBLİĞLER", "http://test.com/4.pdf"),
        GazetteItem("Vergi Kanunu Değişikliği", "YASAMA BÖLÜMÜ", "http://test.com/5.pdf"),
        GazetteItem("ABC İflas İlanı", "YARGI İLÂNLARI", "http://test.com/6.pdf"),
        GazetteItem("XYZ Şirketi İhalesi", "ARTIRMA, EKSİLTME", "http://test.com/7.pdf"),
        GazetteItem("Özelleştirme Kararı", "YÜRÜTME VE İDARE BÖLÜMÜ", "http://test.com/8.pdf"),
    ]

    filter_obj = GazetteFilter()
    result = filter_obj.filter_items(test_items)

    print("=== FİLTRELEME SONUÇLARI ===\n")

    print(f"Korunan içerikler ({len(result.kept_items)}):")
    for item in result.kept_items:
        print(f"  ✓ {item.title}")

    print(f"\nFiltrelenen içerikler ({len(result.filtered_items)}):")
    for item in result.filtered_items:
        print(f"  ✗ {item.title}")

    print(f"\n{filter_obj.get_filter_stats(result)}")


if __name__ == "__main__":
    main()
