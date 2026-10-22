import unittest
from datetime import date
from unittest.mock import patch

import pandas as pd

import portfolio_manager


class PortfolioManagerTests(unittest.TestCase):
    def test_format_ticker_distinguishes_bist_and_us_symbols(self):
        self.assertEqual(portfolio_manager.format_ticker("ASELS", "bist_katilim"), "ASELS.IS")
        self.assertEqual(portfolio_manager.format_ticker("AVPT", "abd_hisse_etf"), "AVPT")
        self.assertIsNone(portfolio_manager.format_ticker("NAKIT_TRY", "nakit_para"))

    @patch.dict("os.environ", {"PORTFOLIO_API_URL": "https://worker.example/", "PORTFOLIO_API_TOKEN": "api-token"})
    @patch("portfolio_manager.requests.get")
    def test_get_holdings_uses_bearer_api_token(self, get):
        get.return_value.status_code = 200
        get.return_value.json.return_value = [{"sembol": "ASELS"}]

        self.assertEqual(portfolio_manager.get_holdings(), [{"sembol": "ASELS"}])
        get.assert_called_once_with(
            "https://worker.example",
            headers={"Authorization": "Bearer api-token"},
            timeout=10,
        )

    @patch("portfolio_manager.yf.Ticker")
    def test_get_live_price_uses_recent_close_and_class_formatting(self, ticker):
        ticker.return_value.history.return_value = pd.DataFrame(
            {"Close": [12.5]},
            index=pd.to_datetime(["2026-10-22"]),
        )

        self.assertEqual(portfolio_manager.get_live_price("AVPT", "abd_hisse_etf"), 12.5)
        ticker.assert_called_once_with("AVPT")
        ticker.return_value.history.assert_called_once_with(period="1mo")

    @patch("portfolio_manager.yf.Ticker")
    def test_get_live_price_with_date_returns_market_date(self, ticker):
        ticker.return_value.history.return_value = pd.DataFrame(
            {"Close": [12.5]},
            index=pd.to_datetime(["2026-10-22"]),
        )

        self.assertEqual(
            portfolio_manager.get_live_price_with_date("AVPT", "abd_hisse_etf"),
            (12.5, date(2026, 10, 22)),
        )

    def test_old_price_date_is_marked_stale(self):
        old_date = date(2020, 1, 1)

        self.assertIn("UYARI:", portfolio_manager._format_price_date("AVPT", old_date))

    @patch("portfolio_manager.get_live_usdtry", return_value=10)
    @patch(
        "portfolio_manager.get_live_price_with_date",
        side_effect=lambda symbol, _: ({"ASELS": 20, "AVPT": 5}[symbol], date(2026, 10, 22)),
    )
    @patch("portfolio_manager._load_constraints", return_value={"siniflar": {"bist_katilim": {"hedef": 25}}})
    @patch(
        "portfolio_manager.get_holdings",
        return_value=[
            {"sembol": "ASELS", "sinif": "bist_katilim", "adet": 2, "para": "TRY"},
            {"sembol": "AVPT", "sinif": "abd_hisse_etf", "adet": 1, "para": "USD"},
            {"sembol": "NAKIT_TRY", "sinif": "nakit_para", "adet": 20, "para": "TRY"},
        ],
    )
    def test_portfolio_summary_uses_market_values_and_currency_conversion(
        self, get_holdings, load_constraints, get_live_price_with_date, get_live_usdtry
    ):
        summary = portfolio_manager.get_portfolio_summary()

        self.assertIn("bist_katilim: Hedef %25 | Fiili %36.4", summary)
        get_live_price_with_date.assert_any_call("ASELS", "bist_katilim")
        get_live_price_with_date.assert_any_call("AVPT", "abd_hisse_etf")
        self.assertIn("ASELS: 2026-10-22", summary)

    @patch("portfolio_manager.requests.get", side_effect=RuntimeError("unavailable"))
    def test_exchange_rate_failure_is_not_replaced_by_a_fixed_rate(self, get):
        with self.assertRaisesRegex(RuntimeError, "USD/TRY kuru"):
            portfolio_manager.get_live_usdtry()
        self.assertEqual(get.call_count, 2)


if __name__ == "__main__":
    unittest.main()
