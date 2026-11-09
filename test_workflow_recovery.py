import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from footybitez.content.documentary_generator import complete_scene_plan
from footybitez.content.quality import documentary_errors, short_errors
from footybitez.pipelines.club_match_pipeline import eligible_fixtures, fetch_fixtures, match_story

NOW = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)


def fixture(league=39, status="NS", hours=2, goals=None, penalties=None):
    return {
        "fixture": {"id": 1, "date": (NOW + timedelta(hours=hours)).isoformat(),
                    "status": {"short": status}, "venue": {}},
        "league": {"id": league}, "teams": {"home": {"name": "Arsenal"}, "away": {"name": "Chelsea"}},
        "goals": goals, "score": {"penalty": penalties},
    }


class WorkflowRecoveryTests(unittest.TestCase):
    def test_documentary_keeps_exact_visual_cues_and_covers_missing_narration(self):
        passage = "The winger waited until the defender stepped forward before running into the space. "
        chapter = {
            "script": "The first move began near the halfway line. " + passage * 14,
            "visual_scenes": [{"narration_snippet": passage.lower().strip(), "visual_type": "image",
                               "image_cue": "verified wing play"},
                              {"narration_snippet": "invented narration", "visual_type": "image"}],
        }
        original = chapter["script"]
        complete_scene_plan(chapter)
        self.assertEqual(chapter["script"], original)
        self.assertIn("verified wing play", [scene.get("image_cue") for scene in chapter["visual_scenes"]])
        self.assertFalse(documentary_errors({"title": "How the winger found space", "chapters": [chapter] * 3}))

    def test_preview_discovers_each_requested_competition_and_ignores_postponements(self):
        fixtures = [fixture(league=league) for league in (39, 140, 78, 135, 61, 2, 253, 307)]
        fixtures.extend([fixture(league=1), fixture(status="PST"), fixture(hours=9)])
        selected = eligible_fixtures(fixtures, "pre", NOW, {})
        self.assertEqual(len(selected), 8)
        for candidate in selected:
            self.assertFalse(short_errors(match_story(candidate, "pre")))
        self.assertEqual(len(eligible_fixtures(fixtures, "pre", NOW, {selected[0][1]: {}})), 7)

    def test_recap_rejects_live_and_incomplete_results_and_separates_penalties(self):
        goals = {"home": 1, "away": 1}
        fixtures = [fixture(status="1H", hours=-3, goals=goals),
                    fixture(status="PEN", hours=-3, goals=goals),
                    fixture(status="PEN", hours=-3, goals=goals, penalties={"home": 5, "away": 4})]
        selected = eligible_fixtures(fixtures, "post", NOW, {})
        self.assertEqual(len(selected), 1)
        story = match_story(selected[0], "post")
        self.assertIn("1–1", story["title"])
        self.assertIn("pens 5–4", story["title"])
        self.assertFalse(short_errors(story))

    @patch.dict("os.environ", {"API_FOOTBALL_KEY": "", "FOOTBALL_DATA_API_KEY": "test"})
    @patch("footybitez.pipelines.club_match_pipeline.requests.get")
    def test_football_data_shootout_totals_are_normalized(self, get):
        get.return_value.json.return_value = {"matches": [{
            "id": 10, "competition": {"code": "CL"}, "status": "FINISHED",
            "utcDate": (NOW - timedelta(hours=3)).isoformat(),
            "homeTeam": {"name": "Arsenal"}, "awayTeam": {"name": "Chelsea"},
            "score": {"duration": "PENALTY_SHOOTOUT", "fullTime": {"home": 6, "away": 5},
                      "penalties": {"home": 5, "away": 4}},
        }]}
        matches = eligible_fixtures(fetch_fixtures("post", NOW), "post", NOW, {})
        self.assertEqual(matches[0][-2:], ((1, 1), (5, 4)))


if __name__ == "__main__":
    unittest.main()
