import os
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone

import requests
import yaml
import yfinance as yf

PRICE_STALE_AFTER_DAYS = 7


def get_live_usdtry() -> float:
    """TCMB resmi XML servisinden anlık USD/TRY efektif satış kurunu çeker."""
    try:
        response = requests.get(
            "https://www.tcmb.gov.tr/kurlar/today.xml",
            timeout=10
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)
        for currency in root.findall("Currency"):
            if currency.get("Kod") == "USD":
                forex_selling = currency.findtext("ForexSelling")
                if forex_selling:
                    return float(forex_selling)
    except Exception as e:
        print(f"[UYARI] TCMB kuru çekilemedi: {e}")

    try:
        response = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/USDTRY=X",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        response.raise_for_status()
        result = response.json()["chart"]["result"][0]
        rate = result["meta"].get("regularMarketPrice")
        if rate is not None:
            return float(rate)
    except Exception as e:
        print(f"[UYARI] Yahoo Finance kuru da çekilemedi: {e}")

    raise RuntimeError("USD/TRY kuru TCMB veya Yahoo Finance üzerinden alınamadı.")


def format_ticker(symbol: str, sinif: str) -> str | None:
    """Sembolü Yahoo Finance formatına dönüştürür."""
    ticker = symbol.upper().strip()
    if ticker.startswith("NAKIT"):
        return None
    if "bist" in sinif.lower() and not ticker.endswith(".IS"):
        return f"{ticker}.IS"
    return ticker


def get_live_price_with_date(symbol: str, sinif: str) -> tuple[float, date]:
    """Varlığın son kapanış fiyatını ve işlem tarihini döndürür."""
    ticker = format_ticker(symbol, sinif)
    if ticker is None:
        raise ValueError(f"Nakit varlık için piyasa fiyatı istenemez: {symbol}")

    try:
        history = yf.Ticker(ticker).history(period="1mo")
        close_prices = history["Close"].dropna()
        if not close_prices.empty:
            return float(close_prices.iloc[-1]), close_prices.index[-1].date()
    except Exception as e:
        raise RuntimeError(f"{symbol} ({ticker}) fiyatı alınamadı: {e}") from e
    raise RuntimeError(f"{symbol} ({ticker}) için son 5 günde fiyat verisi bulunamadı.")


def get_live_price(symbol: str, sinif: str) -> float:
    """Varlığın son kapanış fiyatını alır."""
    price, _ = get_live_price_with_date(symbol, sinif)
    return price


def _format_price_date(symbol: str, price_date: date) -> str:
    line = f"- {symbol}: {price_date.isoformat()}"
    today = datetime.now(timezone.utc).date()
    if today - price_date > timedelta(days=PRICE_STALE_AFTER_DAYS):
        return f"{line} (UYARI: fiyat verisi {PRICE_STALE_AFTER_DAYS} günden eski)"
    return line


def get_holdings() -> list:
    """
    Portföyü önce Cloudflare KV API üzerinden çeker.
    Erişilemezse yedek olarak yerel holdings.yaml dosyasını okur.
    """
    worker_url = os.getenv("PORTFOLIO_API_URL")
    api_token = os.getenv("PORTFOLIO_API_TOKEN")

    if worker_url:
        if not api_token:
            raise ValueError("PORTFOLIO_API_TOKEN ortam değişkeni tanımlı değil!")
        try:
            response = requests.get(
                worker_url.rstrip("/"),
                headers={"Authorization": f"Bearer {api_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if not isinstance(data, list):
                    raise ValueError("Portfolio API yanıtı bir liste değil.")
                print(f"Portföy KV deposundan başarıyla çekildi ({len(data)} varlık).")
                return data
            print(f"KV yanıt kodu: {response.status_code}, yerel dosyaya geçiliyor.")
        except Exception as e:
            print(f"KV bağlantı hatası: {e}, yerel dosya aranıyor.")

    if os.path.exists("holdings.yaml"):
        with open("holdings.yaml", "r", encoding="utf-8") as holdings_file:
            local_data = yaml.safe_load(holdings_file) or []
            if not isinstance(local_data, list):
                raise ValueError("holdings.yaml içeriği bir liste olmalıdır.")
            return local_data

    return []


def _get_holding_value(item: dict, usd_try: float) -> tuple[str, float, date | None]:
    sinif = item.get("sinif", "diger")
    sembol = item.get("sembol", "")
    adet = float(item.get("adet", 0))
    para = str(item.get("para") or item.get("para_birimi", "TRY")).upper()

    if sembol.upper().startswith("NAKIT"):
        value = adet
        price_date = None
    else:
        price, price_date = get_live_price_with_date(sembol, sinif)
        value = adet * price

    if para == "USD":
        value *= usd_try
    return sinif, value, price_date


def _load_constraints() -> dict:
    if not os.path.exists("constraints.yaml"):
        return {}
    with open("constraints.yaml", "r", encoding="utf-8") as constraints_file:
        return yaml.safe_load(constraints_file) or {}


def get_portfolio_summary() -> str:
    """Portföyü güncel piyasa değerleriyle hedef sınıflara göre özetler."""
    holdings = get_holdings()
    constraints = _load_constraints()
    hedefler = constraints.get("siniflar", {})
    usd_try_kuru = get_live_usdtry()

    sinif_toplamlari = {}
    toplam_portfoy = 0.0
    price_dates = []

    for item in holdings:
        sinif, tutar, price_date = _get_holding_value(item, usd_try_kuru)
        sinif_toplamlari[sinif] = sinif_toplamlari.get(sinif, 0.0) + tutar
        toplam_portfoy += tutar
        if price_date:
            price_dates.append((item.get("sembol", ""), price_date))

    ozet_satirlari = [
        f"KULLANICININ GÜNCEL PORTFÖY SAPMALARI (USD/TRY: {usd_try_kuru:.2f}):"
    ]

    if toplam_portfoy > 0:
        for sinif, hedef_bilgi in hedefler.items():
            hedef_yuzde = hedef_bilgi.get("hedef", 0)
            fiili_tutar = sinif_toplamlari.get(sinif, 0.0)
            fiili_yuzde = round((fiili_tutar / toplam_portfoy) * 100, 1)
            fark = round(fiili_yuzde - hedef_yuzde, 1)

            durum = "Dengeli"
            if fark < -3:
                durum = "Eksik (Öncelikli Alım)"
            elif fark > 3:
                durum = "Fazla"

            ozet_satirlari.append(
                f"- {sinif}: Hedef %{hedef_yuzde} | Fiili %{fiili_yuzde} ({durum})"
            )

    if price_dates:
        ozet_satirlari.append("Son kapanış fiyatı tarihleri:")
        ozet_satirlari.extend(
            _format_price_date(symbol, price_date)
            for symbol, price_date in price_dates
        )

    return "\n".join(ozet_satirlari)


def get_rebalancing_recommendations() -> str:
    """constraints.yaml kısıtlarına göre net alım/satım önerilerini TL bazında hesaplar."""
    holdings = get_holdings()
    if not holdings:
        return "Portföyde kayıtlı varlık bulunamadı."

    hedefler = _load_constraints().get("siniflar", {})
    usd_try = get_live_usdtry()

    sinif_degerleri = {}
    toplam_portfoy = 0.0

    for item in holdings:
        sinif, tutar, _ = _get_holding_value(item, usd_try)
        sinif_degerleri[sinif] = sinif_degerleri.get(sinif, 0.0) + tutar
        toplam_portfoy += tutar

    oneriler = [f"🎯 **PORTFÖY DENGELEME ANALİZİ (Toplam: {toplam_portfoy:,.2f} TRY)**\n"]

    for sinif, hedef_bilgi in hedefler.items():
        hedef_yuzde = float(hedef_bilgi.get("hedef", 0))
        olmasi_gereken_tutar = toplam_portfoy * (hedef_yuzde / 100.0)
        fiili_tutar = sinif_degerleri.get(sinif, 0.0)
        fark_tutar = olmasi_gereken_tutar - fiili_tutar

        if fark_tutar > 500:
            oneriler.append(f"➕ *{sinif}*: `{fark_tutar:,.0f} TRY` eksik (Alım önerilir).")
        elif fark_tutar < -500:
            oneriler.append(f"➖ *{sinif}*: `{abs(fark_tutar):,.0f} TRY` fazla.")
        else:
            oneriler.append(f"✅ *{sinif}*: Dengeli.")

    return "\n".join(oneriler)
