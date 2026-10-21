import os
import requests
from pnl_analysis import calculate_portfolio_pnl
from portfolio_manager import get_portfolio_summary

def update_kv_cache():
    worker_url = os.getenv("PORTFOLIO_API_URL")
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not worker_url or not token:
        print("[HATA] PORTFOLIO_API_URL veya TELEGRAM_BOT_TOKEN eksik!")
        return

    print("Analiz hesaplanıyor...")
    pnl_metni = calculate_portfolio_pnl()
    hedef_metni = get_portfolio_summary()
    
    tam_rapor = f"{pnl_metni}\n\n{'='*25}\n\n{hedef_metni}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    res = requests.post(
        f"{worker_url}/cache_analysis",
        headers=headers,
        json={"report": tam_rapor},
        timeout=15
    )

    if res.status_code == 200:
        print("Analiz KV'ye başarıyla önbelleklendi (cached).")
    else:
        print(f"Hata oluştu: {res.status_code} - {res.text}")

if __name__ == "__main__":
    update_kv_cache()