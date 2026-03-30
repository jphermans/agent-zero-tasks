"""
Cryptocurrency price service for e-ink dashboard.
Fetches crypto prices from CoinGecko API (free, no key) with caching.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import logging
from datetime import datetime, timedelta, timezone

import requests

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "crypto_cache.json")
CACHE_TTL = timedelta(minutes=15)


class CryptoService:
    """Fetches cryptocurrency prices from CoinGecko with caching."""

    def __init__(self, config):
        self.config = config
        self.coins = config.get("finance", {}).get("coins", ["bitcoin", "ethereum"])
        self.currency = config.get("finance", {}).get("currency", "usd")
        self.base_url = "https://api.coingecko.com/api/v3"
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        os.makedirs(CACHE_DIR, exist_ok=True)

    def _read_cache(self):
        try:
            if not os.path.exists(CACHE_FILE):
                return None
            with open(CACHE_FILE, "r") as f:
                cache = json.load(f)
            ts = datetime.fromisoformat(cache["timestamp"])
            if datetime.now(timezone.utc) - ts.replace(tzinfo=timezone.utc) < CACHE_TTL:
                logger.debug("Using cached crypto data")
                return cache["data"]
        except Exception as e:
            logger.debug(f"Crypto cache read failed: {e}")
        return None

    def _write_cache(self, data):
        try:
            cache = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data,
            }
            with open(CACHE_FILE, "w") as f:
                json.dump(cache, f, indent=2)
            logger.debug("Crypto cache updated")
        except Exception as e:
            logger.warning(f"Crypto cache write failed: {e}")

    def _fallback_cache(self):
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, "r") as f:
                    cache = json.load(f)
                logger.info("Using stale crypto cache as fallback")
                return cache.get("data")
        except Exception:
            pass
        return None

    def get_prices(self):
        """
        Fetch current prices and 24h change for configured coins.

        Returns:
            list of dicts with keys: 'name', 'symbol', 'price', 'change_24h', 'change_pct'
        """
        cached = self._read_cache()
        if cached is not None and "prices" in cached:
            return cached["prices"]

        try:
            ids = ",".join(self.coins)
            params = {
                "ids": ids,
                "vs_currency": self.currency,
                "order": "market_cap_desc",
                "sparkline": "false",
                "price_change_percentage": "24h",
            }
            resp = requests.get(
                f"{self.base_url}/coins/markets",
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            prices = []
            for coin in data:
                change_pct = coin.get("price_change_percentage_24h", 0) or 0
                change_abs = coin.get("price_change_24h", 0) or 0

                prices.append({
                    "name": coin.get("name", ""),
                    "symbol": coin.get("symbol", "").upper(),
                    "price": round(coin.get("current_price", 0), 2),
                    "change_24h": round(change_abs, 2),
                    "change_pct": round(change_pct, 2),
                })

            cached = cached or {}
            cached["prices"] = prices
            self._write_cache(cached)
            logger.info(f"Fetched prices for {len(prices)} coins")
            return prices

        except requests.ConnectionError:
            logger.error("Cannot connect to CoinGecko API")
            fallback = self._fallback_cache()
            return fallback.get("prices", []) if fallback else []
        except requests.RequestException as e:
            logger.error(f"CoinGecko API error: {e}")
            fallback = self._fallback_cache()
            return fallback.get("prices", []) if fallback else []
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"CoinGecko response parsing failed: {e}")
            fallback = self._fallback_cache()
            return fallback.get("prices", []) if fallback else []
