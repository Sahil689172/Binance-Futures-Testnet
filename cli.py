#!/usr/bin/env python3
"""
cli.py
------
CLI entry point for the Binance Futures Testnet Trading Bot.

Supported sub-commands:
  place   — place MARKET, LIMIT, STOP_MARKET, or TAKE_PROFIT_MARKET orders
  cancel  — cancel an existing order by orderId
  orders  — list all open orders (optionally filtered by symbol)
  ping    — verify connectivity to the Binance Futures Testnet
  account — display account balances

Environment variables (preferred over --api-key / --api-secret flags):
  BINANCE_API_KEY
  BINANCE_API_SECRET

Usage examples:
  python cli.py ping

  python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001

  python cli.py place --symbol BTCUSDT --side SELL --type LIMIT \\
                      --qty 0.001 --price 95000

  python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET \\
                      --qty 0.001 --stop-price 90000

  python cli.py orders --symbol BTCUSDT

  python cli.py cancel --symbol BTCUSDT --order-id 123456789

  python cli.py account
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from decimal import Decimal

# ── Bootstrap path so we can run `python cli.py` from the project root ────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.client import BinanceClient, BinanceAPIError, BinanceNetworkError
from bot.logging_config import setup_logging
from bot.orders import OrderManager
from bot.validators import validate_all


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_separator(char: str = "─", width: int = 60) -> None:
    print(char * width)


def _print_order_summary(params: dict) -> None:
    _print_separator()
    print("  ORDER REQUEST SUMMARY")
    _print_separator()
    for key, value in params.items():
        if value is not None and key != "signature":
            print(f"  {key:<18}: {value}")
    _print_separator()


def _print_order_result(result: dict) -> None:
    _print_separator()
    print("  ORDER RESPONSE")
    _print_separator()
    fields = [
        ("Order ID",       "orderId"),
        ("Client Order ID","clientOrderId"),
        ("Symbol",         "symbol"),
        ("Status",         "status"),
        ("Side",           "side"),
        ("Type",           "type"),
        ("Orig Qty",       "origQty"),
        ("Executed Qty",   "executedQty"),
        ("Avg Price",      "avgPrice"),
        ("Limit Price",    "price"),
        ("Stop Price",     "stopPrice"),
        ("Time-in-Force",  "timeInForce"),
    ]
    for label, key in fields:
        value = result.get(key)
        if value not in (None, "", "0", "0.00000"):
            print(f"  {label:<18}: {value}")
    _print_separator()


def _get_client(args: argparse.Namespace) -> BinanceClient:
    api_key = getattr(args, "api_key", None) or os.environ.get("BINANCE_API_KEY", "")
    api_secret = getattr(args, "api_secret", None) or os.environ.get("BINANCE_API_SECRET", "")

    if not api_key or not api_secret:
        print(
            "\n[ERROR] API credentials not found.\n"
            "  Set environment variables:  BINANCE_API_KEY  and  BINANCE_API_SECRET\n"
            "  or pass:  --api-key <key>  --api-secret <secret>\n"
        )
        sys.exit(1)

    return BinanceClient(api_key=api_key, api_secret=api_secret)


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------

def cmd_ping(args: argparse.Namespace) -> None:
    """Test connectivity."""
    client = _get_client(args)
    if client.ping():
        server_time = client.get_server_time()
        print(f"\n✅  Testnet is reachable — server time: {server_time} ms\n")
    else:
        print("\n❌  Could not reach Binance Futures Testnet.\n")
        sys.exit(1)


def cmd_place(args: argparse.Namespace) -> None:
    """Validate inputs and place an order."""
    # ── Validate ──────────────────────────────────────────────────────────────
    try:
        validated = validate_all(
            symbol=args.symbol,
            side=args.side,
            order_type=args.type,
            quantity=args.qty,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValueError as exc:
        print(f"\n[VALIDATION ERROR] {exc}\n")
        sys.exit(1)

    symbol     = validated["symbol"]
    side       = validated["side"]
    order_type = validated["type"]
    quantity   = validated["quantity"]
    price      = validated["price"]
    stop_price = validated["stopPrice"]

    # ── Print request summary ─────────────────────────────────────────────────
    summary = {
        "Symbol":     symbol,
        "Side":       side,
        "Order Type": order_type,
        "Quantity":   quantity,
    }
    if price:
        summary["Price"] = price
    if stop_price:
        summary["Stop Price"] = stop_price

    print()
    _print_order_summary(summary)

    # ── Place order ───────────────────────────────────────────────────────────
    client  = _get_client(args)
    manager = OrderManager(client)

    if order_type == "MARKET":
        outcome = manager.place_market_order(symbol, side, quantity)
    elif order_type == "LIMIT":
        outcome = manager.place_limit_order(symbol, side, quantity, price)
    elif order_type == "STOP_MARKET":
        outcome = manager.place_stop_market_order(symbol, side, quantity, stop_price)
    elif order_type == "TAKE_PROFIT_MARKET":
        outcome = manager.place_take_profit_market_order(symbol, side, quantity, stop_price)
    else:
        print(f"[ERROR] Unhandled order type: {order_type}")
        sys.exit(1)

    # ── Print result ──────────────────────────────────────────────────────────
    if outcome["success"]:
        _print_order_result(outcome["result"])
        print(f"\n✅  Order placed successfully!\n")
    else:
        print(f"\n❌  Order failed: {outcome['error']}\n")
        sys.exit(1)


def cmd_orders(args: argparse.Namespace) -> None:
    """List open orders."""
    client  = _get_client(args)
    manager = OrderManager(client)
    symbol  = args.symbol.upper() if args.symbol else None

    orders = manager.get_open_orders(symbol)

    if not orders:
        print(f"\n  No open orders{' for ' + symbol if symbol else ''}.\n")
        return

    print(f"\n  Open orders ({len(orders)}):")
    _print_separator()
    for o in orders:
        print(
            f"  ID={o.get('orderId')} | {o.get('symbol')} | "
            f"{o.get('side')} {o.get('type')} | "
            f"qty={o.get('origQty')} price={o.get('price')} | "
            f"status={o.get('status')}"
        )
    _print_separator()
    print()


def cmd_cancel(args: argparse.Namespace) -> None:
    """Cancel a specific order."""
    client  = _get_client(args)
    manager = OrderManager(client)
    symbol  = args.symbol.upper()

    print(f"\n  Cancelling order {args.order_id} for {symbol} …")
    outcome = manager.cancel_order(symbol, args.order_id)

    if outcome["success"]:
        print(f"✅  Order {args.order_id} cancelled successfully.\n")
    else:
        print(f"❌  Cancel failed: {outcome['error']}\n")
        sys.exit(1)


def cmd_account(args: argparse.Namespace) -> None:
    """Display account balances."""
    client = _get_client(args)
    try:
        account = client.get_account()
    except (BinanceAPIError, BinanceNetworkError) as exc:
        print(f"\n❌  Could not fetch account: {exc}\n")
        sys.exit(1)

    print()
    _print_separator()
    print("  ACCOUNT OVERVIEW")
    _print_separator()
    print(f"  Total Wallet Balance : {account.get('totalWalletBalance', '?')} USDT")
    print(f"  Unrealised PnL       : {account.get('totalUnrealizedProfit', '?')} USDT")
    print(f"  Available Balance    : {account.get('availableBalance', '?')} USDT")
    _print_separator()

    # Non-zero asset balances
    balances = [b for b in account.get("assets", []) if float(b.get("walletBalance", 0)) != 0]
    if balances:
        print("  Asset Balances:")
        for b in balances:
            print(f"    {b['asset']:<8}: {b['walletBalance']}")
        _print_separator()
    print()


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet (USDT-M) Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py ping
  python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
  python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --qty 0.001 --price 95000
  python cli.py place --symbol ETHUSDT --side SELL --type STOP_MARKET --qty 0.01 --stop-price 3000
  python cli.py orders --symbol BTCUSDT
  python cli.py cancel --symbol BTCUSDT --order-id 123456
  python cli.py account
        """,
    )

    # ── Global options ────────────────────────────────────────────────────────
    parser.add_argument(
        "--api-key",
        metavar="KEY",
        default=None,
        help="Binance API key (or set env var BINANCE_API_KEY)",
    )
    parser.add_argument(
        "--api-secret",
        metavar="SECRET",
        default=None,
        help="Binance API secret (or set env var BINANCE_API_SECRET)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Console log level (default: INFO; file always captures DEBUG)",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    # ── ping ──────────────────────────────────────────────────────────────────
    subparsers.add_parser("ping", help="Check connectivity to the Binance Futures Testnet")

    # ── place ─────────────────────────────────────────────────────────────────
    place_p = subparsers.add_parser("place", help="Place a new order")
    place_p.add_argument(
        "--symbol", required=True, metavar="SYMBOL",
        help="Trading pair, e.g. BTCUSDT",
    )
    place_p.add_argument(
        "--side", required=True, choices=["BUY", "SELL"],
        help="Order side",
    )
    place_p.add_argument(
        "--type", required=True,
        choices=["MARKET", "LIMIT", "STOP_MARKET", "TAKE_PROFIT_MARKET"],
        metavar="TYPE",
        help="Order type: MARKET | LIMIT | STOP_MARKET | TAKE_PROFIT_MARKET",
    )
    place_p.add_argument(
        "--qty", required=True, type=float, metavar="QUANTITY",
        help="Order quantity in base asset units",
    )
    place_p.add_argument(
        "--price", type=float, default=None, metavar="PRICE",
        help="Limit price (required for LIMIT orders)",
    )
    place_p.add_argument(
        "--stop-price", type=float, default=None, metavar="STOP_PRICE",
        help="Stop price (required for STOP_MARKET / TAKE_PROFIT_MARKET orders)",
    )

    # ── orders ────────────────────────────────────────────────────────────────
    orders_p = subparsers.add_parser("orders", help="List open orders")
    orders_p.add_argument(
        "--symbol", default=None, metavar="SYMBOL",
        help="Filter by symbol (optional)",
    )

    # ── cancel ────────────────────────────────────────────────────────────────
    cancel_p = subparsers.add_parser("cancel", help="Cancel an order")
    cancel_p.add_argument("--symbol", required=True, metavar="SYMBOL")
    cancel_p.add_argument("--order-id", required=True, type=int, metavar="ORDER_ID")

    # ── account ───────────────────────────────────────────────────────────────
    subparsers.add_parser("account", help="Show account balances")

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

COMMAND_MAP = {
    "ping":    cmd_ping,
    "place":   cmd_place,
    "orders":  cmd_orders,
    "cancel":  cmd_cancel,
    "account": cmd_account,
}


def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()

    # Initialise logging before anything else
    setup_logging(log_level=args.log_level)

    handler = COMMAND_MAP.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    handler(args)


if __name__ == "__main__":
    main()
