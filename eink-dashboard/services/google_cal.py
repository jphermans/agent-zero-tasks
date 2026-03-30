"""Google Calendar service for e-ink dashboard."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "calendar_cache.json")
TOKEN_FILE = os.path.join(CACHE_DIR, "google_token.json")
CACHE_TTL = timedelta(minutes=30)
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class GoogleCalendarService:
    """Fetches events from Google Calendar API with caching."""

    def __init__(self, config):
        self.config = config
        self.credentials_file = config.get("google", {}).get("credentials_file", "")
        self.service = None
        self._ensure_cache_dir()
        self._authenticate()

    def _ensure_cache_dir(self):
        os.makedirs(CACHE_DIR, exist_ok=True)

    def _authenticate(self):
        try:
            creds = None
            if os.path.exists(TOKEN_FILE):
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                elif self.credentials_file and os.path.exists(self.credentials_file):
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                else:
                    logger.warning("No valid Google credentials found")
                    return
                with open(TOKEN_FILE, "w") as f:
                    f.write(creds.to_json())
            self.service = build("calendar", "v3", credentials=creds)
            logger.info("Google Calendar authenticated successfully")
        except Exception as e:
            logger.error(f"Google Calendar authentication failed: {e}")
            self.service = None

    def _read_cache(self):
        try:
            if not os.path.exists(CACHE_FILE):
                return None
            with open(CACHE_FILE, "r") as f:
                cache = json.load(f)
            ts = datetime.fromisoformat(cache["timestamp"])
            if datetime.now(timezone.utc) - ts.replace(tzinfo=timezone.utc) < CACHE_TTL:
                logger.debug("Using cached calendar data")
                return cache["data"]
        except Exception as e:
            logger.debug(f"Cache read failed: {e}")
        return None

    def _write_cache(self, data):
        try:
            cache = {"timestamp": datetime.now(timezone.utc).isoformat(), "data": data}
            with open(CACHE_FILE, "w") as f:
                json.dump(cache, f, indent=2)
            logger.debug("Calendar cache updated")
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")

    def _fallback_cache(self):
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, "r") as f:
                    cache = json.load(f)
                logger.info("Using stale calendar cache as fallback")
                return cache.get("data", [])
        except Exception:
            pass
        return []

    def get_events(self, max_results=10):
        """Fetch upcoming calendar events. Returns list of dicts."""
        cached = self._read_cache()
        if cached is not None:
            return cached
        events = []
        if not self.service:
            logger.warning("Google Calendar service not available")
            return self._fallback_cache()
        try:
            now = datetime.now(timezone.utc).isoformat()
            end_time = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
            events_result = (
                self.service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    timeMax=end_time,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            raw_events = events_result.get("items", [])
            for event in raw_events:
                start = event.get("start", {})
                end = event.get("end", {})
                start_str = start.get("dateTime", start.get("date", ""))
                end_str = end.get("dateTime", end.get("date", ""))
                try:
                    if "T" in start_str:
                        sdt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                        start_display = sdt.strftime("%H:%M")
                    else:
                        start_display = "All day"
                except Exception:
                    start_display = start_str
                try:
                    if "T" in end_str:
                        edt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                        end_display = edt.strftime("%H:%M")
                    else:
                        end_display = "All day"
                except Exception:
                    end_display = end_str
                events.append({
                    "summary": event.get("summary", "No title"),
                    "start": start_display,
                    "end": end_display,
                    "location": event.get("location", ""),
                })
            self._write_cache(events)
            logger.info(f"Fetched {len(events)} calendar events")
        except HttpError as e:
            logger.error(f"Google Calendar API error: {e}")
            return self._fallback_cache()
        except Exception as e:
            logger.error(f"Error fetching calendar events: {e}")
            return self._fallback_cache()
        return events
