import unittest

from lib.tool_intent import search_intents


class TestToolIntent(unittest.TestCase):
    def test_shorts_caption_edit_ranks_edit_not_youtube(self):
        hits = search_intents("쇼츠 자막 넣고 편집", limit=5)
        ids = [h["id"] for h in hits]
        self.assertEqual(hits[0]["id"], "edit_pack")
        if "youtube_ref_ingest" in ids:
            self.assertGreater(ids.index("youtube_ref_ingest"), 0)

    def test_concat_phrasing_ranks_edit_pack(self):
        hits = search_intents("클립 붙여 자막", limit=5)
        self.assertEqual(hits[0]["id"], "edit_pack")

    def test_youtube_url_still_finds_ingest(self):
        hits = search_intents("유튜브 레퍼 자막 뽑아", limit=5)
        self.assertEqual(hits[0]["id"], "youtube_ref_ingest")

    def test_flux_fill_outranks_generic_inpaint_on_flux_words(self):
        hits = search_intents("flux fill mask inpaint", limit=5)
        self.assertEqual(hits[0]["id"], "still_flux_fill")

    def test_review_query_ranks_output_review(self):
        hits = search_intents("결과물 능동 평가", limit=3)
        self.assertEqual(hits[0]["id"], "output_review")

    def test_examples_not_dumps(self):
        from lib.tool_intent import INTENT_TOOLS

        yt = next(t for t in INTENT_TOOLS if t["id"] == "youtube_ref_ingest")
        blob = " ".join(yt["examples"])
        self.assertNotIn("dumps/", blob)
        self.assertIn("AGENT_WORKSPACE", blob)


if __name__ == "__main__":
    unittest.main()
