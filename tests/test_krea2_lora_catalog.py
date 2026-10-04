import json
import tempfile
import unittest
from pathlib import Path

from lib.krea2_lora_catalog import catalog, draft_card, recommend


class TestKrea2LoraCatalog(unittest.TestCase):
    def _touch(self, folder: Path, name: str) -> None:
        (folder / name).write_bytes(b"x" * 32)

    def test_known_file_is_ready_on_matching_slot(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self._touch(folder, "krea2_darkbrush.safetensors")
            self._touch(folder, "depth-control-lora.safetensors")
            rows = {row["id"]: row for row in catalog(roots=[folder], min_bytes=1)}
            self.assertTrue(rows["darkbrush"]["apply"])
            self.assertEqual(rows["darkbrush"]["slot"], "t2i")
            self.assertIn("--lora", rows["darkbrush"]["cli"])
            self.assertTrue(rows["depth_control"]["apply"])
            self.assertEqual(rows["depth_control"]["slot"], "control")
            self.assertIn("generate_krea2_control", rows["depth_control"]["cli"])
            self.assertNotIn("--lora", rows["depth_control"]["cli"])

    def test_new_file_stays_off_until_card_is_filled(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self._touch(folder, "studio_gloss.safetensors")
            row = catalog(roots=[folder], min_bytes=1)[0]
            self.assertEqual(row["status"], "unclassified")
            self.assertFalse(row["apply"])
            written = draft_card("studio_gloss.safetensors", roots=[folder], min_bytes=1)
            self.assertTrue(written["ok"])
            still = catalog(roots=[folder], min_bytes=1)[0]
            self.assertFalse(still["apply"])
            card_path = Path(written["purpose_card"])
            card = json.loads(card_path.read_text(encoding="utf-8"))
            card["purpose"] = "윤광 스튜디오 룩"
            card["when"] = ["윤광이 샷의 목적일 때"]
            card["keywords"] = ["윤광", "gloss"]
            card_path.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
            ready = catalog(roots=[folder], min_bytes=1)[0]
            self.assertTrue(ready["apply"])
            hit = recommend("윤광 스튜디오", roots=[folder], min_bytes=1)
            self.assertEqual(hit["match"]["id"], "studio_gloss")
            missed = recommend("깨끗한 실사 인물", roots=[folder], min_bytes=1)
            self.assertIsNone(missed["match"])


if __name__ == "__main__":
    unittest.main()
