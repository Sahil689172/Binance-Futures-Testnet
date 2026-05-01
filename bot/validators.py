"""
validators.py
-------------
Pure validation helpers — no I/O, no network calls.
Raise ValueError with human-readable messages on bad input.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Optional

logger = logging.getLogger("trading_bot.validators")

# ── Allowed enumerations ──────────────────────────────────────────────────────
VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET", "TAKE_PROFIT_MARKET"}

# Common Binance Futures symbols (non-exhaustive; validation is advisory)
COMMON_SYMBOLS = {
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT",
}


def validate_symbol(symbol: str) -> str:
    """Normalise and do a basic sanity-check on a trading symbol."""
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Symbol must be a non-empty string.")
    symbol = symbol.strip().upper()
    if len(symbol) < 5:
        raise ValueError(f"Symbol '{symbol}' seems too short. Expected e.g. BTCUSDT.")
    if not symbol.isalpha():
        raise ValueError(f"Symbol '{symbol}' must contain only letters (e.g. BTCUSDT).")
    if symbol not in COMMON_SYMBOLS:
        logger.warning(
            "Symbol '%s' is not in the pre-loaded common list — "
            "proceeding anyway; the API will reject it if invalid.",
            symbol,
        )
    return symbol


def validate_side(side: str) -> str:
    """Validate order side (BUY / SELL)."""
    if not side or not isinstance(side, str):
        raise ValueError("Side must be a non-empty string.")
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """Validate order type."""
    if not order_type or not isinstance(order_type, str):
        raise ValueError("Order type must be a non-empty string.")
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: str | float) -> Decimal:
    """Validate and parse quantity — must be a positive number."""
    try:
        qty = Decimal(str(quantity))
    except (InvalidOperation, TypeError):
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be > 0, got {qty}.")
    return qty


def validate_price(price: Optional[str | float], order_type: str) -> Optional[Decimal]:
    """
    Validate price:
      - Required for LIMIT / STOP_MARKET / TAKE_PROFIT_MARKET.
      - Ignored (and warned about) for MARKET orders.
    """
    order_type = order_type.strip().upper()

    if order_type == "MARKET":
        if price is not None:
            logger.warning("Price is ignored for MARKET orders.")
        return None

    # Price is required for non-MARKET types
    if price is None:
        raise ValueError(f"Price is required for {order_type} orders.")

    try:
        p = Decimal(str(price))
    except (InvalidOperation, TypeError):
        raise ValueError(f"Price '{price}' is not a valid number.")

    if p <= 0:
        raise ValueError(f"Price must be > 0, got {p}.")

    return p


def validate_stop_price(stop_price: Optional[str | float], order_type: str) -> Optional[Decimal]:
    """Validate stop price — required for STOP_MARKET / TAKE_PROFIT_MARKET orders."""
    if order_type not in {"STOP_MARKET", "TAKE_PROFIT_MARKET"}:
        return None
    if stop_price is None:
        raise ValueError(f"stopPrice is required for {order_type} orders.")
    try:
        sp = Decimal(str(stop_price))
    except (InvalidOperation, TypeError):
        raise ValueError(f"Stop price '{stop_price}' is not a valid number.")
    if sp <= 0:
        raise ValueError(f"Stop price must be > 0, got {sp}.")
    return sp


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: Optional[str | float] = None,
    stop_price: Optional[str | float] = None,
) -> dict:
    """
    Run all validations in one pass.
    Returns a clean dict of validated values ready for the API layer.
    """
    validated_symbol = validate_symbol(symbol)
    validated_side = validate_side(side)
    validated_type = validate_order_type(order_type)
    validated_qty = validate_quantity(quantity)
    validated_price = validate_price(price, validated_type)
    validated_stop = validate_stop_price(stop_price, validated_type)

    result = {
        "symbol": validated_symbol,
        "side": validated_side,
        "type": validated_type,
        "quantity": validated_qty,
        "price": validated_price,
        "stopPrice": validated_stop,
    }

    logger.debug("Validation passed: %s", result)
    return result
