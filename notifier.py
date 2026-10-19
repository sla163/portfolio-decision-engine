import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_message(message: str) -> bool:
    """Telegram botu üzerinden belirtilen sohbete/kanala Markdown formatında mesaj gönderir."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("TELEGRAM_BOT_TOKEN veya TELEGRAM_CHAT_ID tanımlı değil!")

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }

    response = requests.post(url, json=payload, timeout=10)
    if response.status_code == 200:
        print("[BAŞARILI] Bülten Telegram'a iletildi.")
        return True
    else:
        # Markdown ayrıştırma hatası olursa düz metin olarak tekrar dene
        print(f"[UYARI] Telegram Markdown hatası ({response.status_code}), düz metin deneniyor...")
        payload.pop("parse_mode", None)
        retry_res = requests.post(url, json=payload, timeout=10)
        return retry_res.status_code == 200