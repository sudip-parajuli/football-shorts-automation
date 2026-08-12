"""
Quick standalone test for the API-Football image source added to MediaSourcer.
Uses api-sports.io's direct dashboard API (dashboard.api-football.com) — the
RapidAPI marketplace listing for this API no longer exists. Runs no pipeline —
just instantiates MediaSourcer and calls the new fetch method directly for a
known player and a known team.

With API_FOOTBALL_KEY unset, both calls must cleanly return None (the whole
feature is a no-op without the key).
"""
import sys, os
sys.path.insert(0, '.')

from footybitez.media.media_sourcer import MediaSourcer

sourcer = MediaSourcer()

if not sourcer.api_football_key:
    print("API_FOOTBALL_KEY not set — expecting None for both lookups (no-op mode).")

player_path = sourcer._fetch_api_football_image("Mohamed Salah", is_team=False)
print(f"Player (Mohamed Salah) -> {player_path}")

team_path = sourcer._fetch_api_football_image("Liverpool", is_team=True)
print(f"Team (Liverpool) -> {team_path}")

if not sourcer.api_football_key:
    assert player_path is None, "Expected None with no API_FOOTBALL_KEY set"
    assert team_path is None, "Expected None with no API_FOOTBALL_KEY set"
    print("OK: no-op behavior confirmed with key unset.")
