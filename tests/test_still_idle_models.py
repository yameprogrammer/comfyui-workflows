"""Idle still-model wiring: aliases, graphs, intent routing. No Comfy."""

from __future__ import annotations

import unittest

from lib.flux1_runner import build_flux1_fill_api, build_flux1_t2i_api, check_flux1_models
from lib.flux2_klein_runner import build_klein_i2i_api, build_klein_t2i_api, check_klein_models
from lib.sdxl_runner import build_sdxl_t2i_api, check_sdxl_models
from lib.still_model_profiles import (
    KREA_PROFILE_CHOICES,
    SDXL_MODEL_CHOICES,
    ZIMAGE_MODEL_CHOICES,
    ZIMAGE_UNET_ALIASES,
    resolve_krea_unet,
    resolve_sdxl_profile,
    resolve_zimage_unet,
)
from lib.tool_intent import search_intents


class TestAliases(unittest.TestCase):
    def test_krea_turbo_leaves_preset_default(self):
        self.assertIsNone(resolve_krea_unet("turbo"))
        self.assertIsNone(resolve_krea_unet(None))

    def test_krea_named_profiles(self):
        raw = resolve_krea_unet("raw")
        self.assertIn("Krea2Raw", raw)
        self.assertIn("Animosity", resolve_krea_unet("animosity"))
        explicit = r"Krea2Turbo\custom.safetensors"
        self.assertEqual(resolve_krea_unet("gpt", explicit), explicit)

    def test_krea_unknown(self):
        with self.assertRaises(KeyError):
            resolve_krea_unet("not-a-profile")

    def test_zimage_all_aliases(self):
        self.assertGreaterEqual(len(ZIMAGE_MODEL_CHOICES), 6)
        self.assertEqual(
            resolve_zimage_unet("v13"),
            r"ZImageTurbo\moodyProMix_zitV13FP8.safetensors",
        )
        self.assertTrue(resolve_zimage_unet("gguf").endswith(".gguf"))
        self.assertEqual(set(ZIMAGE_MODEL_CHOICES), set(ZIMAGE_UNET_ALIASES))

    def test_sdxl_profiles(self):
        j = resolve_sdxl_profile("juggernaut")
        self.assertIn("juggernautXL", j["ckpt"])
        self.assertEqual(resolve_sdxl_profile("lightning")["steps"], 6)
        self.assertEqual(resolve_sdxl_profile("pony")["dialect"], "pony_score")
        self.assertEqual(set(SDXL_MODEL_CHOICES), {"juggernaut", "lightning", "pony", "nsfw"})


class TestGraphs(unittest.TestCase):
    def test_flux1_t2i_gguf_dualclip(self):
        api = build_flux1_t2i_api(prompt="a bicycle", seed=1)
        self.assertEqual(api["1"]["class_type"], "UnetLoaderGGUF")
        self.assertIn("flux1-dev", api["1"]["inputs"]["unet_name"])
        self.assertEqual(api["2"]["class_type"], "DualCLIPLoader")
        self.assertEqual(api["2"]["inputs"]["type"], "flux")
        self.assertEqual(api["6"]["class_type"], "FluxGuidance")
        self.assertEqual(api["8"]["class_type"], "KSampler")

    def test_flux1_fill_needs_mask_nodes(self):
        api = build_flux1_fill_api(
            prompt="blue jacket", image_name="a.png", mask_name="m.png", seed=2
        )
        self.assertIn("flux1-fill", api["1"]["inputs"]["unet_name"])
        self.assertEqual(api["11"]["class_type"], "InpaintModelConditioning")
        self.assertEqual(api["9"]["class_type"], "ImageToMask")

    def test_klein_t2i_uses_flux2_latent(self):
        api = build_klein_t2i_api(prompt="diner", seed=3)
        self.assertEqual(api["1"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(api["2"]["inputs"]["type"], "flux2")
        self.assertEqual(api["20"]["class_type"], "EmptyFlux2LatentImage")
        self.assertEqual(api["9"]["class_type"], "Flux2Scheduler")

    def test_klein_i2i_uses_denoise_ksampler(self):
        api = build_klein_i2i_api(
            prompt="coastal cliff", image_name="x.png", seed=4, denoise=0.4
        )
        self.assertEqual(api["21"]["class_type"], "VAEEncode")
        self.assertEqual(api["8"]["inputs"]["denoise"], 0.4)

    def test_sdxl_checkpoint_graph(self):
        spec = resolve_sdxl_profile("lightning")
        api = build_sdxl_t2i_api(
            prompt="scout",
            negative="lowres",
            ckpt_name=spec["ckpt"],
            width=1024,
            height=1024,
            seed=5,
            steps=spec["steps"],
            cfg=spec["cfg"],
            sampler=spec["sampler"],
            scheduler=spec["scheduler"],
        )
        self.assertEqual(api["1"]["class_type"], "CheckpointLoaderSimple")
        self.assertIn("dreamshaperXL", api["1"]["inputs"]["ckpt_name"])
        self.assertEqual(api["5"]["inputs"]["steps"], 6)


class TestOnDisk(unittest.TestCase):
    def test_weights_present(self):
        flux = check_flux1_models(need_fill=False)
        fill = check_flux1_models(need_fill=True)
        klein = check_klein_models()
        sdxl = check_sdxl_models()
        self.assertTrue(flux["ok"], flux)
        self.assertTrue(fill["ok"], fill)
        self.assertTrue(klein["ok"], klein)
        self.assertTrue(sdxl["ok"], sdxl)


class TestIntent(unittest.TestCase):
    def test_flux_query(self):
        hits = search_intents("flux1 dev t2i", limit=5)
        ids = [h["id"] for h in hits]
        self.assertIn("still_flux", ids[:3])

    def test_flux_fill_query(self):
        hits = search_intents("flux fill inpaint mask", limit=5)
        self.assertEqual(hits[0]["id"], "still_flux_fill")

    def test_klein_query(self):
        hits = search_intents("flux2 klein 9b", limit=5)
        ids = [h["id"] for h in hits]
        self.assertIn("still_flux2_klein", ids[:3])

    def test_sdxl_query(self):
        hits = search_intents("juggernaut sdxl photoreal", limit=5)
        ids = [h["id"] for h in hits]
        self.assertIn("still_sdxl", ids[:3])

    def test_examples_use_workspace(self):
        from lib.tool_intent import INTENT_TOOLS

        for tid in ("still_flux", "still_flux_fill", "still_flux2_klein", "still_sdxl"):
            card = next(t for t in INTENT_TOOLS if t["id"] == tid)
            blob = " ".join(card["examples"])
            self.assertNotIn("dumps/", blob)
            self.assertIn("AGENT_WORKSPACE", blob)

    def test_krea_profile_choices_cover_idle_unets(self):
        self.assertIn("animosity", KREA_PROFILE_CHOICES)
        self.assertIn("raw", KREA_PROFILE_CHOICES)
        self.assertIn("gpt", KREA_PROFILE_CHOICES)


if __name__ == "__main__":
    unittest.main()
