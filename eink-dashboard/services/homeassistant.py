"""
Home Assistant service for e-ink dashboard.
Fetches smart home entity states via HA REST API with caching.
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
CACHE_FILE = os.path.join(CACHE_DIR, "ha_cache.json")
CACHE_TTL = timedelta(minutes=30)


class HomeAssistantService:
    """Fetches Home Assistant entity states with caching."""

    def __init__(self, config):
        self.config = config
        self.url = config.get("homeassistant", {}).get("url", "http://homeassistant.local:8123")
        self.token = config.get("homeassistant", {}).get("token", "")
        self.entity_filter = config.get("homeassistant", {}).get("entities", [])
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
                logger.debug("Using cached HA data")
                return cache["data"]
        except Exception as e:
            logger.debug(f"HA cache read failed: {e}")
        return None

    def _write_cache(self, data):
        try:
            cache = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data,
            }
            with open(CACHE_FILE, "w") as f:
                json.dump(cache, f, indent=2)
            logger.debug("HA cache updated")
        except Exception as e:
            logger.warning(f"HA cache write failed: {e}")

    def _fallback_cache(self):
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, "r") as f:
                    cache = json.load(f)
                logger.info("Using stale HA cache as fallback")
                return cache.get("data")
        except Exception:
            pass
        return None

    def _get_headers(self):
        """Build request headers with auth token."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def get_entities(self):
        """
        Fetch all entity states, optionally filtered by configured entity list.

        Returns:
            list of dicts with keys: 'entity_id', 'state', 'attributes'
        """
        cached = self._read_cache()
        if cached is not None and "entities" in cached:
            return cached["entities"]

        if not self.token:
            logger.warning("Home Assistant token not configured")
            fallback = self._fallback_cache()
            return fallback.get("entities", []) if fallback else []

        try:
            resp = requests.get(
                f"{self.url}/api/states",
                headers=self._get_headers(),
                timeout=10,
            )
            resp.raise_for_status()
            all_entities = resp.json()

            entities = []
            for ent in all_entities:
                entity_id = ent.get("entity_id", "")

                # Apply filter if configured
                if self.entity_filter:
                    # Support exact match and domain wildcard (e.g. "sensor.*")
                    matched = False
                    for pattern in self.entity_filter:
                        if pattern.endswith(".*"):
                            domain = pattern[:-1]
                            if entity_id.startswith(domain):
                                matched = True
                                break
                        elif entity_id == pattern:
                            matched = True
                            break
                    if not matched:
                        continue

                entities.append({
                    "entity_id": entity_id,
                    "state": ent.get("state", ""),
                    "attributes": ent.get("attributes", {}),
                })

            cached = cached or {}
            cached["entities"] = entities
            self._write_cache(cached)
            logger.info(f"Fetched {len(entities)} HA entities")
            return entities

        except requests.ConnectionError:
            logger.error(f"Cannot connect to Home Assistant at {self.url}")
            fallback = self._fallback_cache()
            return fallback.get("entities", []) if fallback else []
        except requests.RequestException as e:
            logger.error(f"Home Assistant API error: {e}")
            fallback = self._fallback_cache()
            return fallback.get("entities", []) if fallback else []
        except (KeyError, ValueError) as e:
            logger.error(f"Home Assistant response parsing failed: {e}")
            fallback = self._fallback_cache()
            return fallback.get("entities", []) if fallback else []

    def get_state(self, entity_id):
        """
        Get the state of a single entity.

        Returns:
            dict with 'entity_id', 'state', 'attributes' or None on failure
        """
        # Check cache first
        cached = self._read_cache()
        if cached and "entities" in cached:
            for ent in cached["entities"]:
                if ent["entity_id"] == entity_id:
                    return ent

        if not self.token:
            logger.warning("Home Assistant token not configured")
            return None

        try:
            resp = requests.get(
                f"{self.url}/api/states/{entity_id}",
                headers=self._get_headers(),
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "entity_id": data.get("entity_id", entity_id),
                "state": data.get("state", ""),
                "attributes": data.get("attributes", {}),
            }

        except requests.ConnectionError:
            logger.error(f"Cannot connect to Home Assistant at {self.url}")
            return None
        except requests.RequestException as e:
            logger.error(f"Home Assistant API error for {entity_id}: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Home Assistant response parsing failed for {entity_id}: {e}")
            return None
