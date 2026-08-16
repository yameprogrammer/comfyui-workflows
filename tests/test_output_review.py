import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lib.output_review import (
    attach_review_hint,
    blocking_ids,
    build_pack,
    detect_kind,
    format_checks,
    lever_for,
    write_record,
)


def _tiny_png(path: str) -> None:
    # 1x1 PNG
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f"
        b"\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    Path(path).write_bytes(png)


class TestOutputReview(unittest.TestCase):
    def test_detect_kind(self):
        self.assertEqual(detect_kind("a.png"), "still")
        self.assertEqual(detect_kind("a.MP4"), "clip")
        self.assertEqual(detect_kind("a.flac"), "audio")

    def test_blocking_ids_still(self):
        ids = blocking_ids("still")
        self.assertIn("S1_intent", ids)
        self.assertIn("S4_anatomy", ids)
        self.assertNotIn("S7_light", ids)

    def test_lever_anatomy(self):
        row = lever_for("S4_anatomy")
        self.assertIn("hand_detail", row["cli"])

    def test_attach_review_hint_on_png(self):
        r = attach_review_hint({"ok": True, "output_path": "C:/tmp/hero.png"})
        self.assertEqual(r["next_action"], "review_media")
        self.assertIn("review_media.py pack", r["review_cli"])

    def test_attach_skips_json(self):
        r = attach_review_hint({"ok": True, "output_path": "C:/tmp/meta.json"})
        self.assertNotIn("next_action", r)

    def test_pack_and_record_pass(self):
        with tempfile.TemporaryDirectory() as td:
            img = os.path.join(td, "hero.png")
            pack = os.path.join(td, "rev")
            _tiny_png(img)
            res = build_pack(img, intent="medium yellow parasol", pack_dir=pack)
            self.assertTrue(res.get("ok"), res)
            self.assertTrue(os.path.isfile(res["review_md"]))
            rec = write_record(
                pack,
                verdict="pass",
                notes="opened; umbrella hero; hands OK",
                opened=True,
            )
            self.assertTrue(rec.get("ok"), rec)
            self.assertEqual(rec["verdict"], "pass")

    def test_pass_without_opened_fails(self):
        with tempfile.TemporaryDirectory() as td:
            img = os.path.join(td, "hero.png")
            pack = os.path.join(td, "rev")
            _tiny_png(img)
            self.assertTrue(build_pack(img, intent="x", pack_dir=pack).get("ok"))
            rec = write_record(pack, verdict="pass", notes="nope", opened=False)
            self.assertFalse(rec.get("ok"))
            self.assertEqual(rec.get("error"), "NOT_OPENED")

    def test_fail_requires_id_and_prints_lever(self):
        with tempfile.TemporaryDirectory() as td:
            img = os.path.join(td, "hero.png")
            pack = os.path.join(td, "rev")
            _tiny_png(img)
            self.assertTrue(build_pack(img, intent="x", pack_dir=pack).get("ok"))
            rec = write_record(
                pack,
                verdict="fail",
                notes="extra fingers",
                opened=True,
                fails=["S4_anatomy"],
            )
            self.assertTrue(rec.get("ok"), rec)
            self.assertIn("hand_detail", rec.get("next_cli") or "")

    def test_format_checks_lists_blocking(self):
        text = format_checks("still")
        self.assertIn("S1_intent", text)
        self.assertIn("block", text)

    def test_cli_script_pack_and_record(self):
        root = Path(__file__).resolve().parents[1]
        script = root / "scripts" / "review_media.py"
        with tempfile.TemporaryDirectory() as td:
            img = os.path.join(td, "hero.png")
            pack = os.path.join(td, "rev")
            _tiny_png(img)
            r1 = subprocess.run(
                [sys.executable, str(script), "pack", "-i", img, "--intent", "medium", "-o", pack, "--json"],
                cwd=str(root),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(r1.returncode, 0, r1.stderr)
            r2 = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "record",
                    "--pack",
                    pack,
                    "--verdict",
                    "fail",
                    "--fail",
                    "S1_intent",
                    "--opened",
                    "--notes",
                    "wrong shot",
                    "--json",
                ],
                cwd=str(root),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(r2.returncode, 0, r2.stderr)
            rec = (Path(pack) / "record.json").read_text(encoding="utf-8")
            self.assertIn("S1_intent", rec)


class TestReviewIntentRank(unittest.TestCase):
    def test_quality_eval_ranks_review(self):
        from lib.tool_intent import search_intents

        hits = search_intents("결과 검수", limit=5)
        self.assertEqual(hits[0]["id"], "output_review")

    def test_well_made_ranks_review(self):
        from lib.tool_intent import search_intents

        hits = search_intents("잘 나왔는지 평가", limit=5)
        self.assertEqual(hits[0]["id"], "output_review")


if __name__ == "__main__":
    unittest.main()
