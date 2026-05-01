"""
client.py
---------
Low-level Binance Futures Testnet REST client.

Responsibilities:
  - HMAC-SHA256 request signing
  - Timestamping
  - HTTP execution via `requests`
  - Logging every request/response pair (redacting secrets)
  - Raising typed exceptions for API and network errors
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger("trading_bot.client")

# ── Public constants ──────────────────────────────────────────────────────────
BASE_URL = "https://testnet.binancefuture.com"
RECV_WINDOW = 5000  # ms


# ── Exceptions ────────────────────────────────────────────────────────────────
class BinanceAPIError(Exception):
    """Raised when Binance returns a non-2xx response or an error payload."""

    def __init__(self, code: int, message: str, http_status: int = 0):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(f"[{code}] {message} (HTTP {http_status})")


class BinanceNetworkError(Exception):
    """Raised on connection/timeout failures."""


# ── Client ────────────────────────────────────────────────────────────────────
class BinanceClient:
    """
    Minimal authenticated client for Binance Futures Testnet (USDT-M).

    Usage:
        client = BinanceClient(api_key="...", api_secret="...")
        data   = client.get("/fapi/v2/account")
        order  = client.post("/fapi/v1/order", params={...})
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = BASE_URL,
        timeout: int = 10,
    ):
        if not api_key or not api_secret:
            raise ValueError("Both api_key and api_secret must be provided.")

        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.info("BinanceClient initialised — base URL: %s", self._base_url)

    # ── Signing helpers ───────────────────────────────────────────────────────

    def _timestamp(self) -> int:
        return int(time.time() * 1000)

    def _sign(self, params: dict) -> dict:
        """Add timestamp + HMAC-SHA256 signature to a params dict."""
        params["timestamp"] = self._timestamp()
        params["recvWindow"] = RECV_WINDOW
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    # ── Safe log helper ───────────────────────────────────────────────────────

    @staticmethod
    def _safe_params(params: dict) -> dict:
        """Return a copy of params with the signature redacted."""
        safe = dict(params)
        if "signature" in safe:
            safe["signature"] = "***"
        return safe

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = True,
    ) -> dict:
        params = dict(params or {})
        if signed:
            params = self._sign(params)

        url = f"{self._base_url}{path}"

        logger.debug(
            "→ %s %s | params: %s",
            method.upper(),
            path,
            self._safe_params(params),
        )

        try:
            if method.upper() == "GET":
                response = self._session.get(url, params=params, timeout=self._timeout)
            elif method.upper() == "POST":
                response = self._session.post(url, data=params, timeout=self._timeout)
            elif method.upper() == "DELETE":
                response = self._session.delete(url, params=params, timeout=self._timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network connection error: %s", exc)
            raise BinanceNetworkError(f"Connection failed: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out after %ds: %s", self._timeout, exc)
            raise BinanceNetworkError(f"Request timed out after {self._timeout}s") from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Unexpected request error: %s", exc)
            raise BinanceNetworkError(str(exc)) from exc

        logger.debug(
            "← HTTP %d | %s",
            response.status_code,
            response.text[:500],  # truncate very long responses
        )

        # Parse JSON
        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response (HTTP %d): %s", response.status_code, response.text)
            raise BinanceAPIError(
                code=-1,
                message=f"Non-JSON response: {response.text[:200]}",
                http_status=response.status_code,
            )

        # Binance returns error as {"code": <negative>, "msg": "..."}
        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            code = data.get("code", -1)
            msg = data.get("msg", "Unknown API error")
            logger.error("Binance API error %d: %s", code, msg)
            raise BinanceAPIError(code=code, message=msg, http_status=response.status_code)

        if not response.ok:
            raise BinanceAPIError(
                code=response.status_code,
                message=response.text[:300],
                http_status=response.status_code,
            )

        return data

    # ── Public methods ────────────────────────────────────────────────────────

    def get(self, path: str, params: Optional[dict] = None, signed: bool = True) -> dict:
        return self._request("GET", path, params, signed)

    def post(self, path: str, params: Optional[dict] = None, signed: bool = True) -> dict:
        return self._request("POST", path, params, signed)

    def delete(self, path: str, params: Optional[dict] = None, signed: bool = True) -> dict:
        return self._request("DELETE", path, params, signed)

    # ── Convenience methods ───────────────────────────────────────────────────

    def ping(self) -> bool:
        """Test connectivity to the REST API (no auth required)."""
        try:
            self.get("/fapi/v1/ping", signed=False)
            logger.info("Ping successful — testnet is reachable.")
            return True
        except (BinanceAPIError, BinanceNetworkError) as exc:
            logger.error("Ping failed: %s", exc)
            return False

    def get_server_time(self) -> int:
        """Return Binance server time in milliseconds."""
        data = self.get("/fapi/v1/time", signed=False)
        return data["serverTime"]

    def get_exchange_info(self, symbol: Optional[str] = None) -> dict:
        """Retrieve exchange info (all symbols or one specific symbol)."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self.get("/fapi/v1/exchangeInfo", params=params, signed=False)

    def get_account(self) -> dict:
        """Retrieve futures account details (balances, positions)."""
        return self.get("/fapi/v2/account")

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """Retrieve all open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self.get("/fapi/v1/openOrders", params=params)

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Cancel a specific order by orderId."""
        return self.delete(
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
        )
