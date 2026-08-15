"""Assemble a MIDI cover-bed pack (new arrangement, no source master)."""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any

from lib.comfy_client import fail_result, ok_result, utc_now_iso
from lib.midi_arrange import arrange, default_arrangement, validate_arrangement
from lib.midi_render import render_midi
from lib.midi_smf import write_smf
from lib.music_skeleton import (
    extract_skeleton,
    parse_chord_list,
    save_skeleton,
    skeleton_from_symbols,
)
from lib.output_policy import die_if_toolbox
from lib.youtube_ingest import SOURCE_POLICY, download_audio

SOURCE_MD = """Internal analysis only.
This pack is a newly written MIDI arrangement (harmony skeleton → new genre bed).
Do not copy or re-upload the source master.
Do not send the source audio to Suno / MiniMax.
Use arrangement.wav (or a DAW render of arrangement.mid) as the instrumental bed.
Final vocals = new lyrics you write. Recognizable melody lock requires --keep contour and is still a derivative work if the source melody is copyrighted.
"""

_LYRIC_HINT = {
    "ko": "여기에 새 한국어 가사를 넣으세요.",
    "en": "Write new English lyrics here.",
    "ja": "新しい歌詞をここに書いてください。",
    "other": "Write new lyrics here.",
}

_GENRE_CAPTION = {
    "acoustic_ballad": "Acoustic ballad, warm steel guitar, soft piano, intimate room, no lead vocal MIDI",
    "lofi_hiphop": "Lo-fi hip hop instrumental, dusty drums, warm bass, vinyl pad, no lead vocal",
    "band_rock": "Live rock band instrumental, dry drums, electric guitar chops, driving bass",
    "edm_pulse": "Electronic pulse instrumental, four-on-the-floor kick, synth pad, tight bass",
    "piano_pop": "Piano pop instrumental, bright piano, light drums, supportive bass",
}


def _write(path: str, text: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _cover_prompt(arr: dict, lyrics_lang: str) -> str:
    genre = arr.get("genre") or "piano_pop"
    bpm = arr.get("bpm")
    key = arr.get("key") or "C"
    inst = ", ".join(arr.get("instruments") or [])
    caption = _GENRE_CAPTION.get(genre, genre)
    hint = _LYRIC_HINT.get(lyrics_lang, _LYRIC_HINT["other"])
    return (
        f"# Cover handoff\n\n"
        f"Use **arrangement.wav** (or a DAW render of `arrangement.mid`) as the bed.\n"
        f"Do **not** upload the source audio to Suno Cover or MiniMax.\n\n"
        f"## MiniMax caption\n\n"
        f"{caption}, {bpm} BPM, {key}, instruments: {inst}\n\n"
        f"## MiniMax lyrics template\n\n"
        f"[Verse]\n{hint}\n\n[Chorus]\n{hint}\n\n"
        f"## Suno Cover\n\n"
        f"Upload arrangement.wav → Cover → paste new lyrics → keep style close to the bed.\n"
    )


def build_cover_bed(
    *,
    out_dir: str,
    chords: str | None = None,
    audio_path: str | None = None,
    from_url: str | None = None,
    genre: str = "piano_pop",
    keep: str = "harmony_only",
    density: str = "medium",
    bpm: float | None = None,
    key: str = "C",
    bars: int = 8,
    transpose: int = 0,
    lyrics_lang: str = "ko",
    skip_render: bool = False,
    soundfont: str | None = None,
) -> dict[str, Any]:
    dest = die_if_toolbox(out_dir)
    os.makedirs(dest, exist_ok=True)

    tmp_audio = None
    source_kind = "chord_symbols"
    if from_url and not audio_path and not chords:
        print(SOURCE_POLICY)
        tmp_dir = tempfile.mkdtemp(prefix="midi_skel_", dir=dest)
        tmp_audio = os.path.join(tmp_dir, "source_tmp.wav")
        fetched = download_audio(from_url, tmp_audio)
        if not fetched.get("ok"):
            return fail_result(
                error=fetched.get("error") or "URL_AUDIO_FAILED",
                message=fetched.get("message") or "yt-dlp audio failed",
                tool="generate_midi_cover_bed",
            )
        audio_path = fetched.get("path") or tmp_audio
        source_kind = "url_analysis"

    if bool(chords) + bool(audio_path) != 1:
        return fail_result(
            error="INPUT",
            message="provide exactly one of --chords, --input, or --from-url",
            tool="generate_midi_cover_bed",
        )

    if chords:
        sk = skeleton_from_symbols(
            parse_chord_list(chords),
            bpm=float(bpm or 96),
            key=key,
        )
    else:
        extracted = extract_skeleton(str(audio_path))
        if extracted.get("ok") is False:
            return extracted
        sk = extracted
        if bpm:
            sk["bpm"] = float(bpm)

    arr = default_arrangement(
        genre=genre,
        bpm=float(bpm or sk.get("bpm") or 96),
        key=str(sk.get("key") or key),
        bars=int(bars),
        keep=keep,
        density=density,
    )
    arr["transpose"] = int(transpose)
    arr = validate_arrangement(arr)
    tracks = arrange(sk, arr)

    sk_path = save_skeleton(sk, os.path.join(dest, "skeleton.json"))
    arr_path = os.path.join(dest, "arrangement.json")
    with open(arr_path, "w", encoding="utf-8") as f:
        json.dump(arr, f, indent=2, ensure_ascii=False)
        f.write("\n")
    mid_path = write_smf(os.path.join(dest, "arrangement.mid"), tracks, bpm=arr["bpm"])
    _write(os.path.join(dest, "SOURCE.md"), SOURCE_MD)
    _write(os.path.join(dest, "cover_prompt.md"), _cover_prompt(arr, lyrics_lang))

    wav_path = None
    render_info: dict[str, Any] | None = None
    if not skip_render:
        render_info = render_midi(mid_path, os.path.join(dest, "arrangement.wav"), soundfont=soundfont)
        if render_info.get("ok"):
            wav_path = render_info.get("path")

    if tmp_audio and os.path.isfile(tmp_audio):
        try:
            os.remove(tmp_audio)
        except OSError:
            pass

    result = ok_result(
        tool="generate_midi_cover_bed",
        path=dest,
        output_path=dest,
        skeleton_path=sk_path,
        arrangement_path=arr_path,
        midi_path=mid_path,
        wav_path=wav_path,
        render=render_info,
        genre=arr["genre"],
        keep=arr["keep"],
        source_kind=source_kind,
        created_at=utc_now_iso(),
    )
    with open(os.path.join(dest, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return result
