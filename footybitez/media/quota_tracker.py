"""
quota_tracker.py
Daily usage counter for Gemini API calls (Veo + image generation).
Backed by a simple JSON file — resets automatically each calendar day.

Usage:
    from footybitez.media.quota_tracker import can_use, record_use

    if can_use("veo"):
        success = generate_veo_clip(...)
        if success:
            record_use("veo")
"""

import json
import os
from datetime import date

# ─── Configuration ───────────────────────────────────────────────────────────
QUOTA_FILE = "footybitez/data/gemini_quota.json"

# Conservative limits (real Gemini API free-tier RPD is ~50 for Veo preview)
DAILY_LIMITS = {
    "veo":   45,   # 5-clip buffer below ~50 RPD free tier
    "gemini_image": 490,  # 10-clip buffer below 500 RPD free tier
}
# ─────────────────────────────────────────────────────────────────────────────


def _load() -> dict:
    """Load quota data. Returns empty dict if file missing or corrupt."""
    if os.path.exists(QUOTA_FILE):
        try:
            with open(QUOTA_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save(data: dict):
    """Save quota data to disk."""
    os.makedirs(os.path.dirname(QUOTA_FILE), exist_ok=True)
    with open(QUOTA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def _today_data() -> dict:
    """Return today's quota dict, resetting if it's a new day."""
    data = _load()
    today = str(date.today())
    if data.get("date") != today:
        data = {"date": today, "veo": 0, "gemini_image": 0}
    return data


def can_use(service: str) -> bool:
    """
    Returns True if there is remaining quota for the given service today.

    Args:
        service: "veo" or "imagen"
    """
    data = _today_data()
    limit = DAILY_LIMITS.get(service, 0)
    used = data.get(service, 0)
    remaining = limit - used
    if remaining <= 0:
        import logging
        logging.getLogger(__name__).warning(
            f"[QuotaTracker] {service} quota exhausted for today "
            f"({used}/{limit}). Using fallback."
        )
        return False
    return True


def record_use(service: str):
    """
    Increments the usage counter for the given service.
    Call this only after a SUCCESSFUL API call.

    Args:
        service: "veo" or "imagen"
    """
    data = _today_data()
    data[service] = data.get(service, 0) + 1
    _save(data)
    import logging
    logging.getLogger(__name__).info(
        f"[QuotaTracker] {service} usage: {data[service]}/{DAILY_LIMITS.get(service, '?')} today"
    )


def get_status() -> dict:
    """Returns current quota status for logging/debugging."""
    data = _today_data()
    return {
        service: {
            "used": data.get(service, 0),
            "limit": DAILY_LIMITS.get(service, 0),
            "remaining": DAILY_LIMITS.get(service, 0) - data.get(service, 0)
        }
        for service in DAILY_LIMITS
    }
