import os
import yaml
import requests
import xml.etree.ElementTree as ET

def get_live_usdtry() -> float:
    """TCMB resmi XML servisinden anlık USD/TRY efektif satış kurunu çeker."""
    try:
        url = "https://www.tcmb.gov.tr/kurlar/today.xml"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            for currency in root.findall("Currency"):
                if currency.get("Kod") == "USD":
                    forex_selling = currency.find("ForexSelling").text
                    return float(forex_selling)
    except Exception as e:
        print(f"[UYARI] TCMB kuru çekilemedi: {e}")
    
    # Alternatif yedek: Yahoo Finance v8
    try:
        y_url = "https://query1.finance.yahoo.com/v8/finance/chart/USDTRY=X"
        y_res = requests.get(y_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        data = y_res.json()
        return float(data['chart']['result'][0]['meta']['regularMarketPrice'])
    except Exception as e:
        print(f"[UYARI] Yahoo Finance kuru da çekilemedi: {e}")
        return 34.0


def get_holdings() -> list:
    """
    Portföyü önce Cloudflare KV API üzerinden çeker.
    Erişilemezse yedek olarak yerel holdings.yaml dosyasını okur.
    """
    worker_url = os.getenv("PORTFOLIO_API_URL")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    if worker_url and bot_token:
        try:
            response = requests.get(
                worker_url,
                headers={"Authorization": f"Bearer {bot_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                print(f"Portföy KV deposundan başarıyla çekildi ({len(data)} varlık).")
                return data
            else:
                print(f"KV yanıt kodu: {response.status_code}, yerel dosyaya geçiliyor.")
        except Exception as e:
            print(f"KV bağlantı hatası: {e}, yerel dosya aranıyor.")

    # Local fallback
    if os.path.exists("holdings.yaml"):
        with open("holdings.yaml", "r", encoding="utf-8") as f:
            local_data = yaml.safe_load(f) or []
            return local_data

    return []


def get_portfolio_summary() -> str:
    """Portföyü KV'den alarak hedef sınıflara göre güncel sapma özetini hesaplar."""
    try:
        holdings = get_holdings()

        constraints = {}
        if os.path.exists("constraints.yaml"):
            with open("constraints.yaml", "r", encoding="utf-8") as f:
                constraints = yaml.safe_load(f) or {}
            
        hedefler = constraints.get("siniflar", {})
        usd_try_kuru = get_live_usdtry()
        
        sinif_toplamlari = {}
        toplam_portfoy = 0.0
        
        for item in holdings:
            sinif = item.get("sinif", "diger")
            adet = float(item.get("adet", 0))
            maliyet = float(item.get("maliyet", 0))
            tutar = adet * maliyet
            
            para = item.get("para") or item.get("para_birimi", "TRY")
            if str(para).upper() == "USD":
                tutar *= usd_try_kuru
                
            sinif_toplamlari[sinif] = sinif_toplamlari.get(sinif, 0.0) + tutar
            toplam_portfoy += tutar

        ozet_satirlari = [
            f"KULLANICININ GÜNCEL PORTFÖY SAPMALARI (TCMB USD/TRY: {usd_try_kuru:.2f}):"
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
                    
                ozet_satirlari.append(f"- {sinif}: Hedef %{hedef_yuzde} | Fiili %{fiili_yuzde} ({durum})")
        
        return "\n".join(ozet_satirlari)
    except Exception as e:
        return f"Portföy bilgisi okunamadı: {e}"


def get_rebalancing_recommendations() -> str:
    """constraints.yaml kısıtlarına göre net alım/satım önerilerini TL bazında hesaplar."""
    holdings = get_holdings()
    if not holdings:
        return "Portföyde kayıtlı varlık bulunamadı."

    constraints = {}
    if os.path.exists("constraints.yaml"):
        with open("constraints.yaml", "r", encoding="utf-8") as f:
            constraints = yaml.safe_load(f) or {}

    hedefler = constraints.get("siniflar", {})
    usd_try = get_live_usdtry()

    sinif_degerleri = {}
    toplam_portfoy = 0.0

    for item in holdings:
        sinif = item.get("sinif", "diger")
        adet = float(item.get("adet", 0))
        maliyet = float(item.get("maliyet", 0))
        tutar = adet * maliyet
        para = item.get("para") or item.get("para_birimi", "TRY")
        if str(para).upper() == "USD":
            tutar *= usd_try
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