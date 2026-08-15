import unittest

from lib.tool_intent import search_intents


class TestToolIntent(unittest.TestCase):
    def test_shorts_caption_edit_ranks_edit_not_youtube(self):
        hits = search_intents("쇼츠 자막 넣고 편집", limit=5)
        ids = [h["id"] for h in hits]
        self.assertIn(hits[0]["id"], {"render_edit", "render_title", "edit_timeline"})
        if "youtube_ref_ingest" in ids:
            self.assertGreater(ids.index("youtube_ref_ingest"), 0)

    def test_youtube_url_still_finds_ingest(self):
        hits = search_intents("유튜브 레퍼 자막 뽑아", limit=5)
        self.assertEqual(hits[0]["id"], "youtube_ref_ingest")

    def test_examples_not_dumps(self):
        from lib.tool_intent import INTENT_TOOLS

        yt = next(t for t in INTENT_TOOLS if t["id"] == "youtube_ref_ingest")
        blob = " ".join(yt["examples"])
        self.assertNotIn("dumps/", blob)
        self.assertIn("AGENT_WORKSPACE", blob)


if __name__ == "__main__":
    unittest.main()
