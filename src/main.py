"""
Resmi Gazete Takip Botu - Ana Çalıştırıcı
Günlük Resmi Gazete içeriklerini çeker, filtreler ve e-posta ile gönderir.
"""

import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

from scraper import ResmiGazeteScraper, GazetteData
from filter import GazetteFilter, FilterResult
from email_sender import EmailSender


def load_environment():
    """Environment değişkenlerini yükle"""
    # .env dosyası varsa yükle
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)

    # GitHub Actions secrets otomatik olarak environment'a eklenir


def run_bot(to_email: str = None, dry_run: bool = False, verbose: bool = False) -> bool:
    """
    Ana bot işlemini çalıştır

    Args:
        to_email: Alıcı e-posta adresi (veya TO_EMAIL env)
        dry_run: True ise e-posta göndermeden test et
        verbose: Detaylı çıktı

    Returns:
        Başarılı ise True
    """
    load_environment()

    # E-posta adresi
    recipient = to_email or os.environ.get('TO_EMAIL')
    if not recipient and not dry_run:
        print("HATA: Alıcı e-posta adresi belirtilmedi.")
        print("TO_EMAIL environment variable ayarlayın veya --to parametresi kullanın.")
        return False

    print("=" * 60)
    print("RESMİ GAZETE TAKİP BOTU")
    print(f"Çalışma zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. Resmi Gazete'yi çek
    print("\n[1/4] Resmi Gazete çekiliyor...")
    try:
        scraper = ResmiGazeteScraper()
        gazette_data = scraper.scrape()
        print(f"      Tarih: {gazette_data.date}")
        print(f"      Sayı: {gazette_data.issue_number}")
        print(f"      Toplam içerik: {len(gazette_data.items)}")
    except Exception as e:
        print(f"HATA: Resmi Gazete çekilemedi: {e}")
        return False

    # İçerik yoksa çık
    if not gazette_data.items:
        print("\nUYARI: Güncel içerik bulunamadı. Bot sonlandırılıyor.")
        return True

    # 2. Filtreleme
    print("\n[2/4] İçerikler filtreleniyor...")
    gazette_filter = GazetteFilter(
        filter_universities=True,
        filter_announcements=True,
        filter_central_bank=True,
        filter_appointments=False
    )
    filter_result = gazette_filter.filter_items(gazette_data.items)

    print(f"      Korunan: {len(filter_result.kept_items)}")
    print(f"      Filtrelenen: {len(filter_result.filtered_items)}")

    if verbose and filter_result.filter_summary:
        print("\n      Filtreleme detayları:")
        for reason, count in filter_result.filter_summary.items():
            print(f"        - {reason}: {count}")

    # Filtrelenmiş içerik yoksa
    if not filter_result.kept_items:
        print("\nUYARI: Tüm içerikler filtrelendi. E-posta gönderilmeyecek.")
        return True

    # 3. Kategorilere göre özet
    print("\n[3/4] İçerik özeti:")
    categories = {}
    for item in filter_result.kept_items:
        if item.category not in categories:
            categories[item.category] = 0
        categories[item.category] += 1

    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"      • {cat}: {count}")

    # 4. E-posta gönderimi
    if dry_run:
        print("\n[4/4] DRY RUN - E-posta gönderilmedi.")
        print(f"      Alıcı olacaktı: {recipient or 'belirtilmedi'}")

        if verbose:
            print("\n      İçerik listesi:")
            for item in filter_result.kept_items[:10]:
                print(f"        - {item.title[:50]}...")
            if len(filter_result.kept_items) > 10:
                print(f"        ... ve {len(filter_result.kept_items) - 10} içerik daha")
    else:
        print(f"\n[4/4] E-posta gönderiliyor: {recipient}")
        try:
            sender = EmailSender()
            success = sender.send(recipient, gazette_data, filter_result)
            if not success:
                print("HATA: E-posta gönderilemedi.")
                return False
        except Exception as e:
            print(f"HATA: E-posta gönderim hatası: {e}")
            return False

    print("\n" + "=" * 60)
    print("Bot başarıyla tamamlandı.")
    print("=" * 60)

    return True


def main():
    """CLI giriş noktası"""
    parser = argparse.ArgumentParser(
        description='Resmi Gazete Takip Botu',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python main.py --dry-run                    # Test modu (e-posta göndermez)
  python main.py --to email@example.com       # Belirli adrese gönder
  python main.py --verbose                    # Detaylı çıktı
  python main.py                              # TO_EMAIL env kullanarak çalıştır

Environment Variables:
  SENDGRID_API_KEY    SendGrid API anahtarı (zorunlu)
  TO_EMAIL            Varsayılan alıcı e-posta adresi
  FROM_EMAIL          Gönderen e-posta adresi (opsiyonel)
        """
    )

    parser.add_argument(
        '--to', '-t',
        metavar='EMAIL',
        help='Alıcı e-posta adresi'
    )

    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Test modu - e-posta göndermeden çalıştır'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Detaylı çıktı göster'
    )

    args = parser.parse_args()

    success = run_bot(
        to_email=args.to,
        dry_run=args.dry_run,
        verbose=args.verbose
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
