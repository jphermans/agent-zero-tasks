# Email service for e-ink dashboard.
# Fetches unread count and recent senders via IMAP with caching.

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import logging
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "email_cache.json")
CACHE_TTL = timedelta(minutes=5)


class EmailService:
    """Fetches email data via IMAP with caching."""

    def __init__(self, config):
        self.config = config
        self.server = config.get("email", {}).get("server", "imap.gmail.com")
        self.port = config.get("email", {}).get("port", 993)
        self.user = config.get("email", {}).get("user", "")
        self.password = config.get("email", {}).get("password", "")
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
                logger.debug("Using cached email data")
                return cache["data"]
        except Exception as e:
            logger.debug(f"Email cache read failed: {e}")
        return None

    def _write_cache(self, data):
        try:
            cache = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data,
            }
            with open(CACHE_FILE, "w") as f:
                json.dump(cache, f, indent=2)
            logger.debug("Email cache updated")
        except Exception as e:
            logger.warning(f"Email cache write failed: {e}")

    def _fallback_cache(self):
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, "r") as f:
                    cache = json.load(f)
                logger.info("Using stale email cache as fallback")
                return cache.get("data")
        except Exception:
            pass
        return None

    def _decode_str(self, raw):
        """Decode email header string."""
        if not raw:
            return ""
        try:
            decoded = decode_header(raw)
            parts = []
            for part, charset in decoded:
                if isinstance(part, bytes):
                    charset = charset or "utf-8"
                    try:
                        parts.append(part.decode(charset, errors="replace"))
                    except (LookupError, UnicodeDecodeError):
                        parts.append(part.decode("utf-8", errors="replace"))
                else:
                    parts.append(str(part))
            return "".join(parts)
        except Exception:
            return str(raw)

    def _connect(self):
        """Establish IMAP connection. Returns imaplib.IMAP4_SSL or None."""
        try:
            conn = imaplib.IMAP4_SSL(self.server, self.port)
            conn.login(self.user, self.password)
            conn.select("INBOX", readonly=True)
            return conn
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP connection/login failed: {e}")
            return None
        except Exception as e:
            logger.error(f"IMAP connection error: {e}")
            return None

    def _disconnect(self, conn):
        """Safely close IMAP connection."""
        try:
            conn.close()
            conn.logout()
        except Exception:
            pass

    def get_unread_count(self):
        """Get count of unread emails. Returns int."""
        cached = self._read_cache()
        if cached is not None and "unread_count" in cached:
            return cached["unread_count"]
        if not self.user or not self.password:
            logger.warning("Email credentials not configured")
            fallback = self._fallback_cache()
            return fallback.get("unread_count", 0) if fallback else 0
        conn = self._connect()
        if not conn:
            fallback = self._fallback_cache()
            return fallback.get("unread_count", 0) if fallback else 0
        try:
            status, messages = conn.search(None, "UNSEEN")
            if status != "OK":
                return 0
            msg_ids = messages[0].split()
            count = len(msg_ids)
            cached = cached or {}
            cached["unread_count"] = count
            self._write_cache(cached)
            logger.info(f"Unread emails: {count}")
            return count
        except Exception as e:
            logger.error(f"Error fetching unread count: {e}")
            fallback = self._fallback_cache()
            return fallback.get("unread_count", 0) if fallback else 0
        finally:
            self._disconnect(conn)

    def get_recent_senders(self, count=5):
        """Get recent email senders and subjects. Returns list of dicts."""
        cached = self._read_cache()
        if cached is not None and "recent_senders" in cached:
            return cached["recent_senders"][:count]
        if not self.user or not self.password:
            logger.warning("Email credentials not configured")
            fallback = self._fallback_cache()
            return (fallback.get("recent_senders") or [])[:count] if fallback else []
        conn = self._connect()
        if not conn:
            fallback = self._fallback_cache()
            return (fallback.get("recent_senders") or [])[:count] if fallback else []
        try:
            status, messages = conn.search(None, "ALL")
            if status != "OK":
                return []
            msg_ids = messages[0].split()
            recent_ids = msg_ids[-count:] if len(msg_ids) > count else msg_ids
            recent_ids.reverse()
            senders = []
            for mid in recent_ids:
                try:
                    status, msg_data = conn.fetch(mid, "(RFC822)")
                    if status != "OK":
                        continue
                    raw = msg_data[0][1]
                    msg = email.message_from_bytes(raw)
                    from_addr = self._decode_str(msg.get("From", ""))
                    subject = self._decode_str(msg.get("Subject", ""))
                    date_str = msg.get("Date", "")
                    try:
                        from email.utils import parsedate_to_datetime
                        dt = parsedate_to_datetime(date_str)
                        date_display = dt.strftime("%b %d %H:%M")
                    except Exception:
                        date_display = date_str[:20] if date_str else ""
                    senders.append({
                        "from": from_addr,
                        "subject": subject,
                        "date": date_display,
                    })
                    if len(senders) >= count:
                        break
                except Exception as e:
                    logger.debug(f"Error parsing message {mid}: {e}")
                    continue
            cached = cached or {}
            cached["recent_senders"] = senders
            self._write_cache(cached)
            logger.info(f"Fetched {len(senders)} recent senders")
            return senders
        except Exception as e:
            logger.error(f"Error fetching recent senders: {e}")
            fallback = self._fallback_cache()
            return (fallback.get("recent_senders") or [])[:count] if fallback else []
        finally:
            self._disconnect(conn)
