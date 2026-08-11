"""
Quick standalone test for the API-Football (RapidAPI) image source added to
MediaSourcer. Runs no pipeline — just instantiates MediaSourcer and calls the
new fetch method directly for a known player and a known team.

With RAPIDAPI_FOOTBALL_KEY unset, both calls must cleanly return None (the
whole feature is a no-op without the key).
"""
import sys, os
sys.path.insert(0, '.')

from footybitez.media.media_sourcer import MediaSourcer

sourcer = MediaSourcer()

if not sourcer.rapidapi_football_key:
    print("RAPIDAPI_FOOTBALL_KEY not set — expecting None for both lookups (no-op mode).")

player_path = sourcer._fetch_api_football_image("Mohamed Salah", is_team=False)
print(f"Player (Mohamed Salah) -> {player_path}")

team_path = sourcer._fetch_api_football_image("Liverpool", is_team=True)
print(f"Team (Liverpool) -> {team_path}")

if not sourcer.rapidapi_football_key:
    assert player_path is None, "Expected None with no RAPIDAPI_FOOTBALL_KEY set"
    assert team_path is None, "Expected None with no RAPIDAPI_FOOTBALL_KEY set"
    print("OK: no-op behavior confirmed with key unset.")
