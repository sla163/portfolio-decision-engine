from fetcher import fetch_all_news
from analyzer import analyze_and_summarize
from notifier import send_telegram_message
from portfolio_manager import get_portfolio_summary 
import sys
 
def run_pipeline():
    print("1. Portföy durumu hesaplanıyor...")
    portfoy_durumu = get_portfolio_summary()  # Otomatik hesaplandı!
    
    print("2. Haberler taranıyor...")
    news_data = fetch_all_news(limit_per_feed=5)

    if not news_data.strip():
            print("[HATA] Hiçbir haber çekilemedi. İşlem sonlandırılıyor.")
            sys.exit(1)
    
    print("3. Analiz ediliyor...")
    bulletin = analyze_and_summarize(news_data, portfoy_ozeti=portfoy_durumu)
    
    print("4. Telegram'a gönderiliyor...")
    send_telegram_message(bulletin)

if __name__ == "__main__":
    run_pipeline()