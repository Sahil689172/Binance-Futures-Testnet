"""
orders.py
---------
Order placement logic — sits between the CLI and the raw HTTP client.

Responsibilities:
  - Build correct parameter dicts for each order type
  - Call the appropriate client endpoints
  - Log request summaries and response highlights
  - Return structured result dicts to the caller
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from .client import BinanceClient, BinanceAPIError, BinanceNetworkError

logger = logging.getLogger("trading_bot.orders")

# ── Precision helpers ─────────────────────────────────────────────────────────
# Binance Futures requires specific decimal precision per symbol.
# For testnet convenience we apply sensible defaults; a production bot
# should query /fapi/v1/exchangeInfo and use the actual filters.

QUANTITY_PRECISION: Dict[str, int] = {
    "BTCUSDT": 3,
    "ETHUSDT": 3,
    "BNBUSDT": 2,
    "XRPUSDT": 1,
    "SOLUSDT": 0,
    "ADAUSDT": 0,
    "DOGEUSDT": 0,
    "AVAXUSDT": 2,
    "DOTUSDT": 1,
    "MATICUSDT": 0,
}

PRICE_PRECISION: Dict[str, int] = {
    "BTCUSDT": 1,
    "ETHUSDT": 2,
    "BNBUSDT": 3,
    "XRPUSDT": 4,
    "SOLUSDT": 2,
    "ADAUSDT": 4,
    "DOGEUSDT": 5,
    "AVAXUSDT": 2,
    "DOTUSDT": 3,
    "MATICUSDT": 4,
}

DEFAULT_QTY_PRECISION = 3
DEFAULT_PRICE_PRECISION = 2


def _qty_str(symbol: str, qty: Decimal) -> str:
    prec = QUANTITY_PRECISION.get(symbol, DEFAULT_QTY_PRECISION)
    return f"{qty:.{prec}f}"


def _price_str(symbol: str, price: Decimal) -> str:
    prec = PRICE_PRECISION.get(symbol, DEFAULT_PRICE_PRECISION)
    return f"{price:.{prec}f}"


# ── Result formatter ──────────────────────────────────────────────────────────

def _format_order_result(raw: dict) -> dict:
    """
    Extract and normalise the most useful fields from a Binance order response.
    Returns a flat dict suitable for display and downstream processing.
    """
    return {
        "orderId": raw.get("orderId"),
        "clientOrderId": raw.get("clientOrderId"),
        "symbol": raw.get("symbol"),
        "status": raw.get("status"),
        "side": raw.get("side"),
        "type": raw.get("type"),
        "origQty": raw.get("origQty"),
        "executedQty": raw.get("executedQty"),
        "avgPrice": raw.get("avgPrice"),
        "price": raw.get("price"),
        "stopPrice": raw.get("stopPrice"),
        "timeInForce": raw.get("timeInForce"),
        "updateTime": raw.get("updateTime"),
    }


# ── Core order placer ─────────────────────────────────────────────────────────

class OrderManager:
    """
    High-level order manager — wraps BinanceClient with order-specific logic.

    All public methods return a dict:
        {
            "success": bool,
            "summary": dict,    # what was sent
            "result":  dict,    # normalised API response (on success)
            "error":   str,     # human-readable error (on failure)
        }
    """

    def __init__(self, client: BinanceClient):
        self._client = client

    # ── Internal dispatcher ───────────────────────────────────────────────────

    def _place_order(self, params: dict) -> dict:
        symbol = params.get("symbol", "?")
        logger.info(
            "Placing order | symbol=%s side=%s type=%s qty=%s price=%s",
            params.get("symbol"),
            params.get("side"),
            params.get("type"),
            params.get("quantity"),
            params.get("price", "—"),
        )
        try:
            raw = self._client.post("/fapi/v1/order", params=params)
            result = _format_order_result(raw)
            logger.info(
                "Order placed ✓ | orderId=%s status=%s executedQty=%s avgPrice=%s",
                result["orderId"],
                result["status"],
                result["executedQty"],
                result["avgPrice"],
            )
            return {"success": True, "summary": params, "result": result, "error": None}

        except BinanceAPIError as exc:
            logger.error("API error placing order for %s: %s", symbol, exc)
            return {"success": False, "summary": params, "result": None, "error": str(exc)}

        except BinanceNetworkError as exc:
            logger.error("Network error placing order for %s: %s", symbol, exc)
            return {"success": False, "summary": params, "result": None, "error": str(exc)}

    # ── Public order methods ──────────────────────────────────────────────────

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
    ) -> dict:
        """Place a MARKET order."""
        params = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": _qty_str(symbol, quantity),
        }
        return self._place_order(params)

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        time_in_force: str = "GTC",
    ) -> dict:
        """Place a LIMIT order (Good-Till-Cancelled by default)."""
        params = {
            "symbol": symbol,
            "side": side,
            "type": "LIMIT",
            "quantity": _qty_str(symbol, quantity),
            "price": _price_str(symbol, price),
            "timeInForce": time_in_force,
        }
        return self._place_order(params)

    def place_stop_market_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        stop_price: Decimal,
    ) -> dict:
        """
        Place a STOP_MARKET order (Bonus order type).

        The order becomes a MARKET order once the stop price is reached.
        Commonly used as a stop-loss.
        """
        params = {
            "symbol": symbol,
            "side": side,
            "type": "STOP_MARKET",
            "quantity": _qty_str(symbol, quantity),
            "stopPrice": _price_str(symbol, stop_price),
        }
        return self._place_order(params)

    def place_take_profit_market_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        stop_price: Decimal,
    ) -> dict:
        """
        Place a TAKE_PROFIT_MARKET order (Bonus order type).

        Triggers a MARKET sell/buy once the stop price is touched from below/above.
        """
        params = {
            "symbol": symbol,
            "side": side,
            "type": "TAKE_PROFIT_MARKET",
            "quantity": _qty_str(symbol, quantity),
            "stopPrice": _price_str(symbol, stop_price),
        }
        return self._place_order(params)

    # ── Convenience wrappers ──────────────────────────────────────────────────

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """Return open orders, optionally filtered by symbol."""
        try:
            return self._client.get_open_orders(symbol)
        except (BinanceAPIError, BinanceNetworkError) as exc:
            logger.error("Could not fetch open orders: %s", exc)
            return []

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Cancel an order by orderId."""
        try:
            raw = self._client.cancel_order(symbol, order_id)
            logger.info("Order %d cancelled successfully.", order_id)
            return {"success": True, "result": raw, "error": None}
        except (BinanceAPIError, BinanceNetworkError) as exc:
            logger.error("Could not cancel order %d: %s", order_id, exc)
            return {"success": False, "result": None, "error": str(exc)}
