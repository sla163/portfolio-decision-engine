import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

print("--- DEĞER KONTROLÜ ---")
print("Bot Token:", TELEGRAM_BOT_TOKEN[:10] + "..." if TELEGRAM_BOT_TOKEN else "YOK (None)")
print("Chat ID:", repr(TELEGRAM_CHAT_ID))

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("\n[HATA] Token veya Chat ID boş geldi! .env dosyasını veya ortam değişkenlerini kontrol edin.")
else:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": "🚨 Deneme: Bot bağlantısı başarılı mı?"
    }
    res = requests.post(url, json=payload, timeout=10)
    print("\n--- TELEGRAM YANITI ---")
    print("Durum Kodu:", res.status_code)
    print("Yanıt Detayı:", res.text)