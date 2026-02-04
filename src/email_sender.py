"""
SendGrid E-posta Gönderici
Filtrelenmiş Resmi Gazete içeriklerini şık HTML formatında e-posta ile gönderir.
"""

import os
from typing import List, Dict
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, HtmlContent
from scraper import GazetteItem, GazetteData
from filter import FilterResult


class EmailSender:
    """SendGrid ile e-posta gönderici"""

    def __init__(self, api_key: str = None, from_email: str = None):
        """
        Args:
            api_key: SendGrid API anahtarı (veya SENDGRID_API_KEY env)
            from_email: Gönderen e-posta adresi (veya FROM_EMAIL env)
        """
        self.api_key = api_key or os.environ.get('SENDGRID_API_KEY')
        self.from_email = from_email or os.environ.get('FROM_EMAIL', 'resmigazete@bot.com')

        if not self.api_key:
            raise ValueError("SendGrid API key gerekli. SENDGRID_API_KEY environment variable ayarlayın.")

    def _group_by_category(self, items: List[GazetteItem]) -> Dict[str, List[GazetteItem]]:
        """İçerikleri kategorilere göre grupla"""
        grouped = {}
        for item in items:
            if item.category not in grouped:
                grouped[item.category] = []
            grouped[item.category].append(item)
        return grouped

    def _generate_html(self, gazette_data: GazetteData,
                       filter_result: FilterResult) -> str:
        """HTML e-posta içeriği oluştur"""
        grouped = self._group_by_category(filter_result.kept_items)

        # Filtreleme özeti
        total_items = len(filter_result.kept_items) + len(filter_result.filtered_items)
        filtered_count = len(filter_result.filtered_items)

        html = f"""
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resmi Gazete - {gazette_data.date}</title>
</head>
<body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
    <div style="background-color: #ffffff; border-radius: 8px; padding: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">

        <!-- Başlık -->
        <div style="text-align: center; border-bottom: 3px solid #c41e3a; padding-bottom: 20px; margin-bottom: 25px;">
            <h1 style="color: #c41e3a; margin: 0; font-size: 28px;">T.C. Resmi Gazete</h1>
            <p style="color: #666; margin: 10px 0 0 0; font-size: 16px;">
                {gazette_data.date} | Sayı: {gazette_data.issue_number}
            </p>
        </div>

        <!-- Özet bilgi -->
        <div style="background-color: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin-bottom: 25px; border-radius: 0 4px 4px 0;">
            <p style="margin: 0; color: #333;">
                <strong>{len(filter_result.kept_items)}</strong> içerik listeleniyor
                {f' <span style="color: #888;">({filtered_count} içerik filtrelendi)</span>' if filtered_count > 0 else ''}
            </p>
        </div>
"""

        # Her kategori için bölüm oluştur
        category_icons = {
            'YASAMA BÖLÜMÜ': '⚖️',
            'YÜRÜTME VE İDARE BÖLÜMÜ': '🏛️',
            'YARGI BÖLÜMÜ': '⚖️',
            'MİLLETLERARASI ANDLAŞMALAR': '🌍',
            'YÖNETMELİKLER': '📋',
            'TEBLİĞLER': '📢',
            'GENELGELER': '📄',
            'CUMHURBAŞKANLIĞI': '🇹🇷',
        }

        for category, items in grouped.items():
            icon = '📰'
            for key, emoji in category_icons.items():
                if key in category.upper():
                    icon = emoji
                    break

            html += f"""
        <!-- {category} -->
        <div style="margin-bottom: 25px;">
            <h2 style="color: #333; font-size: 18px; border-bottom: 2px solid #e9ecef; padding-bottom: 10px; margin-bottom: 15px;">
                {icon} {category}
            </h2>
            <ul style="list-style: none; padding: 0; margin: 0;">
"""
            for item in items:
                link_icon = '📄' if item.item_type == 'pdf' else '🔗'
                link_style = 'color: #007bff; text-decoration: none;' if item.item_type == 'htm' else 'color: #dc3545; text-decoration: none;'

                html += f"""
                <li style="padding: 10px 0; border-bottom: 1px solid #f0f0f0;">
                    <a href="{item.link}" style="{link_style}" target="_blank">
                        {link_icon} {item.title}
                    </a>
                    <span style="color: #999; font-size: 12px; margin-left: 5px;">[{item.item_type.upper()}]</span>
                </li>
"""

            html += """
            </ul>
        </div>
"""

        # Filtreleme detayları (varsa)
        if filtered_count > 0 and filter_result.filter_summary:
            html += """
        <!-- Filtreleme Detayları -->
        <div style="background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 4px; padding: 15px; margin-top: 20px;">
            <h3 style="color: #856404; margin: 0 0 10px 0; font-size: 14px;">🔍 Filtrelenen İçerikler</h3>
            <ul style="margin: 0; padding-left: 20px; color: #856404; font-size: 13px;">
"""
            for reason, count in filter_result.filter_summary.items():
                html += f"""
                <li>{reason}: {count} öğe</li>
"""
            html += """
            </ul>
        </div>
"""

        # Footer
        html += f"""
        <!-- Footer -->
        <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e9ecef;">
            <a href="{gazette_data.url}" style="display: inline-block; background-color: #c41e3a; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                Tam Gazeteyi Görüntüle
            </a>
            <p style="color: #999; font-size: 12px; margin-top: 20px;">
                Bu e-posta Resmi Gazete Takip Botu tarafından otomatik olarak gönderilmiştir.<br>
                <a href="https://www.resmigazete.gov.tr" style="color: #999;">www.resmigazete.gov.tr</a>
            </p>
        </div>

    </div>
</body>
</html>
"""
        return html

    def _generate_plain_text(self, gazette_data: GazetteData,
                             filter_result: FilterResult) -> str:
        """Düz metin e-posta içeriği oluştur"""
        grouped = self._group_by_category(filter_result.kept_items)

        text = f"""
T.C. RESMİ GAZETE
{gazette_data.date} | Sayı: {gazette_data.issue_number}
{'=' * 50}

Toplam {len(filter_result.kept_items)} içerik
"""

        for category, items in grouped.items():
            text += f"\n\n{category}\n{'-' * len(category)}\n"
            for item in items:
                text += f"• {item.title} [{item.item_type.upper()}]\n  {item.link}\n"

        if filter_result.filter_summary:
            text += f"\n\nFiltrelenen içerikler:\n"
            for reason, count in filter_result.filter_summary.items():
                text += f"  - {reason}: {count}\n"

        text += f"\n\nTam Gazete: {gazette_data.url}\n"

        return text

    def send(self, to_email: str, gazette_data: GazetteData,
             filter_result: FilterResult) -> bool:
        """
        E-posta gönder

        Args:
            to_email: Alıcı e-posta adresi
            gazette_data: Gazete verisi
            filter_result: Filtreleme sonucu

        Returns:
            Başarılı ise True
        """
        if not filter_result.kept_items:
            print("Gönderilecek içerik yok, e-posta atlandı.")
            return False

        subject = f"Resmi Gazete - {gazette_data.date} (Sayı: {gazette_data.issue_number})"

        html_content = self._generate_html(gazette_data, filter_result)
        plain_content = self._generate_plain_text(gazette_data, filter_result)

        message = Mail(
            from_email=Email(self.from_email, "Resmi Gazete Bot"),
            to_emails=To(to_email),
            subject=subject,
            plain_text_content=Content("text/plain", plain_content),
            html_content=HtmlContent(html_content)
        )

        try:
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)

            if response.status_code in [200, 201, 202]:
                print(f"E-posta başarıyla gönderildi: {to_email}")
                print(f"Status Code: {response.status_code}")
                return True
            else:
                print(f"E-posta gönderim hatası. Status: {response.status_code}")
                return False

        except Exception as e:
            print(f"E-posta gönderim hatası: {e}")
            return False


def main():
    """Test fonksiyonu"""
    from scraper import GazetteItem, GazetteData
    from filter import FilterResult

    # Test verisi
    test_items = [
        GazetteItem("Hâkimler ve Savcılar Kurulu Kararı", "YÜRÜTME VE İDARE BÖLÜMÜ", "http://test.com/1.pdf", "pdf"),
        GazetteItem("Vergi Kanunu Değişikliği", "YASAMA BÖLÜMÜ", "http://test.com/2.htm", "htm"),
        GazetteItem("Özelleştirme Kararı", "YÜRÜTME VE İDARE BÖLÜMÜ", "http://test.com/3.pdf", "pdf"),
    ]

    gazette_data = GazetteData(
        date="04 Şubat 2026",
        issue_number="33158",
        items=test_items,
        url="https://www.resmigazete.gov.tr"
    )

    filter_result = FilterResult(
        kept_items=test_items,
        filtered_items=[],
        filter_summary={}
    )

    # HTML çıktısını göster
    sender = EmailSender.__new__(EmailSender)
    sender.from_email = "test@test.com"
    html = sender._generate_html(gazette_data, filter_result)
    print("HTML e-posta içeriği oluşturuldu.")
    print(f"Uzunluk: {len(html)} karakter")

    # Gerçek gönderim için API key gerekli
    # sender = EmailSender()
    # sender.send("test@example.com", gazette_data, filter_result)


if __name__ == "__main__":
    main()
