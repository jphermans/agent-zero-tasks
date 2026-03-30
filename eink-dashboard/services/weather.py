"""Weather service for e-ink dashboard."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import logging
from datetime import datetime, timedelta, timezone
from collections import Counter

import requests

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "weather_cache.json")
CACHE_TTL = timedelta(minutes=15)


class WeatherService:
    """Fetches weather data from OpenWeatherMap with caching."""

    def __init__(self, config):
        self.config = config
        self.api_key = config.get("weather", {}).get("api_key", "")
        self.location = config.get("weather", {}).get("location", "London,GB")
        self.units = config.get("weather", {}).get("units", "metric")
        self.base_url = "https://api.openweathermap.org/data/2.5"
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
                logger.debug("Using cached weather data")
                return cache["data"]
        except Exception as e:
            logger.debug(f"Weather cache read failed: {e}")
        return None

    def _write_cache(self, data):
        try:
            cache = {"timestamp": datetime.now(timezone.utc).isoformat(), "data": data}
            with open(CACHE_FILE, "w") as f:
                json.dump(cache, f, indent=2)
            logger.debug("Weather cache updated")
        except Exception as e:
            logger.warning(f"Weather cache write failed: {e}")

    def _fallback_cache(self):
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, "r") as f:
                    cache = json.load(f)
                logger.info("Using stale weather cache as fallback")
                return cache.get("data")
        except Exception:
            pass
        return None

    def get_current(self):
        """Fetch current weather. Returns dict or None."""
        cached = self._read_cache()
        if cached is not None and "current" in cached:
            return cached["current"]
        if not self.api_key:
            logger.warning("No OpenWeatherMap API key configured")
            fallback = self._fallback_cache()
            return fallback.get("current") if fallback else None
        try:
            params = {"q": self.location, "appid": self.api_key, "units": self.units}
            resp = requests.get(f"{self.base_url}/weather", params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            current = {
                "temp": round(data["main"]["temp"]),
                "feels_like": round(data["main"]["feels_like"]),
                "humidity": data["main"]["humidity"],
                "wind_speed": round(data["wind"].get("speed", 0), 1),
                "description": data["weather"][0]["description"].title(),
                "icon": data["weather"][0]["icon"],
            }
            cached = cached or {}
            cached["current"] = current
            self._write_cache(cached)
            logger.info(f"Fetched weather: {current['temp']}° {current['description']}")
            return current
        except requests.RequestException as e:
            logger.error(f"Weather API request failed: {e}")
            fallback = self._fallback_cache()
            return fallback.get("current") if fallback else None
        except (KeyError, IndexError) as e:
            logger.error(f"Weather API parsing failed: {e}")
            fallback = self._fallback_cache()
            return fallback.get("current") if fallback else None

    def get_forecast(self, days=3):
        """Fetch forecast. Returns list of dicts."""
        cached = self._read_cache()
        if cached is not None and "forecast" in cached:
            return cached["forecast"][:days]
        if not self.api_key:
            logger.warning("No OpenWeatherMap API key configured")
            fallback = self._fallback_cache()
            return (fallback.get("forecast") or [])[:days] if fallback else []
        # Try 5-day forecast endpoint and group by day
        try:
            params = {"q": self.location, "appid": self.api_key, "units": self.units}
            resp = requests.get(f"{self.base_url}/forecast", params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            daily = {}
            for entry in data.get("list", []):
                dt = datetime.fromtimestamp(entry["dt"], tz=timezone.utc)
                date_key = dt.strftime("%Y-%m-%d")
                if date_key not in daily:
                    daily[date_key] = {
                        "date": dt.strftime("%a %b %d"),
                        "temp_high": entry["main"]["temp_max"],
                        "temp_low": entry["main"]["temp_min"],
                        "descriptions": [],
                    }
                else:
                    daily[date_key]["temp_high"] = max(
                        daily[date_key]["temp_high"], entry["main"]["temp_max"]
                    )
                    daily[date_key]["temp_low"] = min(
                        daily[date_key]["temp_low"], entry["main"]["temp_min"]
                    )
                daily[date_key]["descriptions"].append(entry["weather"][0]["description"])
            forecast = []
            for date_key in sorted(daily.keys())[:days]:
                d = daily[date_key]
                most_common = Counter(d["descriptions"]).most_common(1)[0][0]
                forecast.append({
                    "date": d["date"],
                    "temp_high": round(d["temp_high"]),
                    "temp_low": round(d["temp_low"]),
                    "description": most_common.title(),
                })
            cached = cached or {}
            cached["forecast"] = forecast
            self._write_cache(cached)
            logger.info(f"Fetched {len(forecast)}-day forecast")
            return forecast
        except requests.RequestException as e:
            logger.error(f"Weather forecast API failed: {e}")
            fallback = self._fallback_cache()
            return (fallback.get("forecast") or [])[:days] if fallback else []
        except (KeyError, IndexError) as e:
            logger.error(f"Weather forecast parsing failed: {e}")
            fallback = self._fallback_cache()
            return (fallback.get("forecast") or [])[:days] if fallback else []
