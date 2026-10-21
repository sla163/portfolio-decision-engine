import os

import requests

from pnl_analysis import calculate_portfolio_pnl
from portfolio_manager import get_portfolio_summary


def update_kv_cache():
    worker_url = os.getenv("PORTFOLIO_API_URL")
    api_token = os.getenv("PORTFOLIO_API_TOKEN")

    if not worker_url or not api_token:
        raise ValueError("PORTFOLIO_API_URL veya PORTFOLIO_API_TOKEN eksik!")

    print("Analiz hesaplanıyor...")
    pnl_metni = calculate_portfolio_pnl()
    hedef_metni = get_portfolio_summary()
    tam_rapor = f"{pnl_metni}\n\n{'=' * 25}\n\n{hedef_metni}"

    response = requests.post(
        f"{worker_url.rstrip('/')}/cache_analysis",
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        },
        json={"report": tam_rapor},
        timeout=15,
    )
    response.raise_for_status()
    print("Analiz KV'ye başarıyla önbelleklendi (cached).")


if __name__ == "__main__":
    update_kv_cache()
