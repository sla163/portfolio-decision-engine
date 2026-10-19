import os
import yfinance as yf
from portfolio_manager import get_holdings, get_live_usdtry

def format_ticker(symbol: str, sinif: str) -> str:
    """Sembolü Yahoo Finance formatına dönüştürür."""
    sym = symbol.upper().strip()
    if sym.startswith("NAKIT"):
        return None
    if "bist" in sinif.lower() or not "." in sym:
        return f"{sym}.IS" if not sym.endswith(".IS") else sym
    return sym

def calculate_portfolio_pnl() -> str:
    holdings = get_holdings()
    if not holdings:
        return "Portföyde kayıtlı varlık bulunamadı."

    usd_try = get_live_usdtry()
    toplam_maliyet_try = 0.0
    toplam_guncel_try = 0.0
    
    satirlar = ["📈 **PORTFÖY GÜNCEL KÂR / ZARAR DURUMU**\n"]

    for item in holdings:
        sembol = item.get("sembol", "").upper()
        adet = float(item.get("adet", 0))
        maliyet = float(item.get("maliyet", 0))
        para = (item.get("para") or item.get("para_birimi", "TRY")).upper()
        sinif = item.get("sinif", "")

        # Nakit varlık kontrolü
        if sembol.startswith("NAKIT"):
            deger_try = adet if para == "TRY" else adet * usd_try
            toplam_maliyet_try += deger_try
            toplam_guncel_try += deger_try
            satirlar.append(f"💵 `{sembol}`: {adet:,.2f} {para} (Nakit)")
            continue

        ticker = format_ticker(sembol, sinif)
        guncel_fiyat = maliyet  # Fallback

        if ticker:
            try:
                data = yf.Ticker(ticker).history(period="1d")
                if not data.empty:
                    guncel_fiyat = float(data["Close"].iloc[-1])
            except Exception:
                pass

        varlik_maliyet = adet * maliyet
        varlik_guncel = adet * guncel_fiyat
        kar_zarar_tutari = varlik_guncel - varlik_maliyet
        kar_orani = ((guncel_fiyat / maliyet) - 1) * 100 if maliyet > 0 else 0

        carpan = usd_try if para == "USD" else 1.0
        toplam_maliyet_try += varlik_maliyet * carpan
        toplam_guncel_try += varlik_guncel * carpan

        isaret = "🟢 +" if kar_zarar_tutari >= 0 else "🔴 "
        satirlar.append(
            f"*{sembol}* ({adet} ad. @ {maliyet:.2f} {para}) -> Son: `{guncel_fiyat:.2f} {para}`\n"
            f"   └ Fark: {isaret}{kar_zarar_tutari:,.2f} {para} (%{kar_orani:+.1f})"
        )

    toplam_fark_try = toplam_guncel_try - toplam_maliyet_try
    toplam_oran = ((toplam_guncel_try / toplam_maliyet_try) - 1) * 100 if toplam_maliyet_try > 0 else 0
    toplam_isaret = "🟢 +" if toplam_fark_try >= 0 else "🔴 "

    satirlar.append("\n" + "—" * 25)
    satirlar.append(f"Toplam Maliyet: `{toplam_maliyet_try:,.2f} TRY`")
    satirlar.append(f"Güncel Değer : `{toplam_guncel_try:,.2f} TRY`")
    satirlar.append(f"Net Durum    : {toplam_isaret}{toplam_fark_try:,.2f} TRY (%{toplam_oran:+.2f})")

    return "\n".join(satirlar)

if __name__ == "__main__":
    print(calculate_portfolio_pnl())