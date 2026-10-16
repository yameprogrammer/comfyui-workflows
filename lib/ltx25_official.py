"""Small API graphs following pinned official LTX-2.5 task recipes.

A2V: ComfyUI-LTXVideo 44c8a36, LTX-2.5_A2V_Two_Stage_Distilled.json.
T2A: local official-derived LTX-2.5_T2A_Ambience_int8.json.
No automatic community quality adapters are added to these reference graphs.
"""

DIT = "ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors"
ENCODER = "gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors"
AUDIO_VAE = "ltx-2.5-audio-vae-bf16.safetensors"
VIDEO_VAE = "ltx-2.5-video-vae-bf16.safetensors"
UPSCALER = "ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors"
SIGMAS = "1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0"


def build_task(task, *, prompt, seconds=2.0, fps=24, seed=42, width=384, height=256,
               image_name=None, audio_name=None, prefix="ltx25_official"):
    if task not in {"t2a", "a2v"}:
        raise ValueError("Supported reference tasks: t2a, a2v")
    if task == "a2v" and not audio_name:
        raise ValueError("A2V requires an input audio file")
    frames = 1 + int(seconds * fps // 8) * 8
    if width % 32 or height % 32:
        raise ValueError("Base width and height must be divisible by 32")
    graph = {}

    def add(kind, **inputs):
        key = str(len(graph) + 1)
        graph[key] = {"class_type": kind, "inputs": inputs}
        return [key, 0]

    model = add("UNETLoader", unet_name=DIT, weight_dtype="default")
    clip = add("CLIPLoader", clip_name=ENCODER, type="ltxv", device="default")
    avae = add("VAELoader", vae_name=AUDIO_VAE)
    pos = add("CLIPTextEncode", clip=clip, text=prompt)
    neg = add("CLIPTextEncode", clip=clip, text="")
    cond = add("LTXVConditioning", positive=pos, negative=neg, frame_rate=fps)
    pos, neg = cond, [cond[0], 1]
    sampler = add("KSamplerSelect", sampler_name="euler_ancestral")
    sigmas = add("ManualSigmas", sigmas=SIGMAS)
    if task == "t2a":
        model = add("LTXVAudioOnlyModel", model=model)
        video = add("LTXVAudioOnlyEmptyVideoLatent")
        audio = add("LTXVEmptyLatentAudio", frames_number=frames, frame_rate=fps, batch_size=1, audio_vae=avae)
    else:
        vvae = add("VAELoader", vae_name=VIDEO_VAE)
        original = add("LoadAudio", audio=audio_name)
        original = add("TrimAudioDuration", audio=original, start_index=0.0, duration=seconds)
        audio = add("LTXVAudioVAEEncode", audio=original, audio_vae=avae)
        frozen = add("SolidMask", value=0.0, width=1024, height=1024)
        audio = add("SetLatentNoiseMask", samples=audio, mask=frozen)
        video = add("EmptyLTXVLatentVideo", width=width, height=height, length=frames, batch_size=1)
        if image_name:
            image = add("LoadImage", image=image_name)
            image = add("ImageScale", image=image, upscale_method="lanczos", width=width, height=height, crop="center")
            preprocessed = add("LTXVPreprocess", image=image, img_compression=18)
            video = add("LTXVImgToVideoInplace", vae=vvae, image=preprocessed, latent=video, strength=0.7, bypass=False)
    latent = add("LTXVConcatAVLatent", video_latent=video, audio_latent=audio)
    noise = add("RandomNoise", noise_seed=seed)
    guider = add("CFGGuider", model=model, positive=pos, negative=neg, cfg=1.0)
    sampled = add("SamplerCustomAdvanced", noise=noise, guider=guider, sampler=sampler, sigmas=sigmas, latent_image=latent)
    separated = add("LTXVSeparateAVLatent", av_latent=sampled)
    if task == "t2a":
        decoded = add("LTXVAudioVAEDecode", samples=[separated[0], 1], audio_vae=avae)
        add("SaveAudioAdvanced", audio=decoded, filename_prefix="audio/" + prefix, format="flac")
    else:
        upscaler = add("LatentUpscaleModelLoader", model_name=UPSCALER)
        video = add("LTXVLatentUpsampler", samples=separated, upscale_model=upscaler, vae=vvae)
        if image_name:
            image = add("ImageScale", image=image, upscale_method="lanczos", width=width * 2, height=height * 2, crop="center")
            video = add("LTXVImgToVideoInplace", vae=vvae, image=image, latent=video, strength=1.0, bypass=False)
        latent = add("LTXVConcatAVLatent", video_latent=video, audio_latent=audio)
        sigma2 = add("ManualSigmas", sigmas="0.909375, 0.725, 0.421875, 0.0")
        noise2 = add("RandomNoise", noise_seed=seed + 1)
        sampled = add("SamplerCustomAdvanced", noise=noise2, guider=guider, sampler=sampler, sigmas=sigma2, latent_image=latent)
        video = add("LTXVSeparateAVLatent", av_latent=sampled)
        decoded = add("VAEDecodeTiled", samples=video, vae=vvae, tile_size=512, overlap=64, temporal_size=64, temporal_overlap=8)
        add("VHS_VideoCombine", images=decoded, audio=original, frame_rate=fps, loop_count=0,
            filename_prefix="video/" + prefix, format="video/h264-mp4", pix_fmt="yuv420p", crf=18,
            save_metadata=True, trim_to_audio=False, pingpong=False, save_output=True)
    return graph, {"task": task, "frames": frames, "fps": fps, "base_width": width, "base_height": height,
                   "prompt_enhance": False, "quality_loras": "official reference graph has no added quality adapters",
                   "audio_policy": "audio only generated" if task == "t2a" else "input audio frozen in both sampling stages; original trimmed waveform muxed"}


def build_ingredients(*, prompt, image_name, seconds=5.0, fps=24, seed=42,
                      width=768, height=448, prefix="ltx25_ingredients",
                      adapter_strength=1.0, sampler_name="euler_ancestral"):
    """2.5 adapter-card candidate; separate from the pinned 2.3-adapter JSON."""
    frames = 1 + int(seconds * fps // 8) * 8
    if not image_name or frames < 121:
        raise ValueError("Ingredients requires a reference sheet and >=121 reference/output frames")
    if width % 32 or height % 32:
        raise ValueError("Ingredients width/height must be divisible by 32")
    if "reference sheet:" not in prompt.lower() or "generated video:" not in prompt.lower():
        raise ValueError("Ingredients prompt needs Reference sheet: and Generated video: sections")
    graph = {}

    def add(kind, **inputs):
        key = str(len(graph) + 1)
        graph[key] = {"class_type": kind, "inputs": inputs}
        return [key, 0]

    model = add("UNETLoader", unet_name=DIT, weight_dtype="default")
    model = add("LTXICLoRALoaderModelOnly", model=model,
                lora_name="LTX2.5\\ltx-2.5-22b-ic-lora-ingredients-0.9.safetensors", strength_model=adapter_strength)
    clip = add("CLIPLoader", clip_name=ENCODER, type="ltxv", device="default")
    vvae = add("VAELoader", vae_name=VIDEO_VAE)
    avae = add("VAELoader", vae_name=AUDIO_VAE)
    image = add("LoadImage", image=image_name)
    image = add("ImageScale", image=image, upscale_method="lanczos", width=width, height=height, crop="disabled")
    reference = add("RepeatImageBatch", image=image, amount=frames)
    pos = add("CLIPTextEncode", clip=clip, text=prompt)
    neg = add("CLIPTextEncode", clip=clip, text="worst quality, inconsistent motion, blurry, jittery, distorted")
    cond = add("LTXVConditioning", positive=pos, negative=neg, frame_rate=fps)
    video = add("EmptyLTXVLatentVideo", width=width, height=height, length=frames, batch_size=1)
    guide = add("LTXAddVideoICLoRAGuide", positive=cond, negative=[cond[0], 1], vae=vvae,
                latent=video, image=reference, frame_idx=0, strength=1.0, latent_downscale_factor=1.0,
                crop="disabled", use_tiled_encode=False, tile_size=256, tile_overlap=64)
    audio = add("LTXVEmptyLatentAudio", frames_number=frames, frame_rate=fps, batch_size=1, audio_vae=avae)
    latent = add("LTXVConcatAVLatent", video_latent=[guide[0], 2], audio_latent=audio)
    guider = add("CFGGuider", model=model, positive=guide, negative=[guide[0], 1], cfg=1.0)
    noise = add("RandomNoise", noise_seed=seed)
    sampler = add("KSamplerSelect", sampler_name=sampler_name)
    sigmas = add("ManualSigmas", sigmas=SIGMAS)
    sampled = add("SamplerCustomAdvanced", noise=noise, guider=guider, sampler=sampler, sigmas=sigmas, latent_image=latent)
    separated = add("LTXVSeparateAVLatent", av_latent=sampled)
    cropped = add("LTXVCropGuides", positive=guide, negative=[guide[0], 1], latent=separated)
    images = add("VAEDecodeTiled", samples=[cropped[0], 2], vae=vvae,
                 tile_size=512, overlap=64, temporal_size=64, temporal_overlap=8)
    audio = add("LTXVAudioVAEDecode", samples=[separated[0], 1], audio_vae=avae)
    add("VHS_VideoCombine", images=images, audio=audio, frame_rate=fps, loop_count=0,
        filename_prefix="video/" + prefix, format="video/h264-mp4", pix_fmt="yuv420p", crf=18,
        save_metadata=True, trim_to_audio=False, pingpong=False, save_output=True)
    return graph, {"task": "ingredients", "frames": frames, "fps": fps, "width": width, "height": height,
                   "adapter": "LTX2.5/ltx-2.5-22b-ic-lora-ingredients-0.9.safetensors",
                   "source": "2.5 model-card candidate, not an unchanged official 2.3-adapter workflow",
                   "reference_downscale_factor": 1, "adapter_strength": adapter_strength, "sampler": sampler_name, "reference_frames": frames,
                   "reference_encode": "untiled, matching official UI",
                   "quality_loras": "task-specific Ingredients adapter only; existing AIO quality policy unchanged"}
