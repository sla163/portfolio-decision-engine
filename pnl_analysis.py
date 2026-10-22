from portfolio_manager import (
    _format_price_date,
    get_holdings,
    get_live_price_with_date,
    get_live_usdtry,
)


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

        if sembol.startswith("NAKIT"):
            deger_try = adet if para == "TRY" else adet * usd_try
            toplam_maliyet_try += deger_try
            toplam_guncel_try += deger_try
            satirlar.append(f"💵 `{sembol}`: {adet:,.2f} {para} (Nakit)")
            continue

        guncel_fiyat, fiyat_tarihi = get_live_price_with_date(sembol, sinif)
        varlik_maliyet = adet * maliyet
        varlik_guncel = adet * guncel_fiyat
        kar_zarar_tutari = varlik_guncel - varlik_maliyet
        kar_orani = ((guncel_fiyat / maliyet) - 1) * 100 if maliyet > 0 else 0

        carpan = usd_try if para == "USD" else 1.0
        toplam_maliyet_try += varlik_maliyet * carpan
        toplam_guncel_try += varlik_guncel * carpan

        isaret = "🟢 +" if kar_zarar_tutari >= 0 else "🔴 "
        satirlar.append(
            f"*{sembol}* ({adet} ad. @ {maliyet:.2f} {para}) -> "
            f"Son: `{guncel_fiyat:.2f} {para}` ({fiyat_tarihi.isoformat()})\n"
            f"   └ Fark: {isaret}{kar_zarar_tutari:,.2f} {para} (%{kar_orani:+.1f})"
        )
        price_date_line = _format_price_date(sembol, fiyat_tarihi)
        if "UYARI:" in price_date_line:
            satirlar.append(price_date_line)

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
