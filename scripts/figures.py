"""The guide's figures, made with the library on sandbox/sample_short.mp4: a Burkinabè sketch subtitled in
French, with the watermark `clideo.com` on every frame. From the repository folder:

    uv run --extra easyocr --extra lid python scripts/figures.py docs/images

Writes overlays.png, windows.png and language.png. EasyOCR reads 512 frames in about a minute and a half on a
Mac M5, and MMS-LID hears the windows in a few seconds.
"""

import copy
import sys
import tempfile
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from frame2text4llm.export.audio_generator import AudioGenerator
from frame2text4llm.framer import VideoReader
from frame2text4llm.language import LanguageID
from frame2text4llm.ocr import OCRBatchProcessor, OCRManager
from frame2text4llm.ocr.utils.filters import mark_non_subtitles, seconds, strip_overlays, windows
from frame2text4llm.ocr.utils.text_utils import _merge_segments

VIDEO = "sandbox/sample_short.mp4"
INK, ORANGE, BROWN, GREY = "#222222", "#F48635", "#B85D22", "#BBBBBB"
SPAN = 60  # seconds shown on the timelines


def bars(ax, segments, y, color, label, span=SPAN):
    for s in segments:
        a, b = seconds(s["start_time"]), seconds(s["end_time"])
        if a < span:
            ax.add_patch(Rectangle((a, y - 0.3), max(b - a, 0.3), 0.6, fc=color, ec="white", lw=1.5))
    ax.text(-1, y, label, ha="right", va="center", fontsize=10)


def timeline(ax, span=SPAN):
    ax.set_xlim(0, span)
    ax.set_yticks([])
    ax.set_xlabel("seconds")
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)


def main(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    reader = VideoReader(VIDEO)
    frames = reader.extract_frames(target_fps=2)
    h, w = frames[0].image.shape[:2]
    band = (int(h * 0.7), h, 0, w)
    results = OCRBatchProcessor(OCRManager(reader, region=band)).process_batch(
        frames, tool="easyocr", lang="fr", n_cores=1, show_progress=False
    )
    raw = copy.deepcopy(results)
    before = _merge_segments(copy.deepcopy(results))
    strip_overlays(results)
    after = _merge_segments(results)
    duration = len(frames) / 2

    # 1. the watermark taken out
    at = next(i for i, r in enumerate(raw) if "clideo" in r["text"].lower() and len(r["text"]) > 30)
    fig = plt.figure(figsize=(11, 5.2))
    img = fig.add_axes([0.03, 0.42, 0.34, 0.52])
    img.imshow(cv2.cvtColor(frames[at].image[band[0] : band[1]], cv2.COLOR_BGR2RGB))
    img.axis("off")
    img.set_title(f"the subtitle band at {raw[at]['time_formatted']}", fontsize=10)
    fig.text(0.03, 0.30, "EasyOCR reads", fontsize=10, color=GREY)
    fig.text(0.03, 0.24, raw[at]["text"], fontsize=10, color=INK)
    fig.text(0.03, 0.15, "after strip_overlays", fontsize=10, color=GREY)
    fig.text(0.03, 0.09, results[at]["text"], fontsize=10, color=BROWN)
    ax = fig.add_axes([0.52, 0.16, 0.45, 0.72])
    bars(ax, before, 1, GREY, f"merged as read\n{len(before)} segments")
    bars(ax, after, 0, ORANGE, f"logo taken out\n{len(after)} segments")
    ax.set_ylim(-0.8, 1.8)
    timeline(ax)
    ax.set_title(f"the first {SPAN} s of the video", fontsize=10)
    fig.savefig(out / "overlays.png", dpi=150)
    plt.close(fig)

    # 2. what is dropped, and the windows
    mark_non_subtitles(after, duration)
    found = windows(after)
    fig, ax = plt.subplots(figsize=(11, 2.8))
    bars(ax, [s for s in after if not s["drop"]], 1, GREY, "subtitles", duration)
    bars(ax, [s for s in after if s["drop"]], 1, BROWN, "", duration)
    for x in found:
        a, b = seconds(x["start_time"]), seconds(x["end_time"])
        ax.add_patch(Rectangle((a, -0.3), b - a, 0.6, fill=False, ec=ORANGE, lw=1.5))
    ax.text(-3, 0, "windows", ha="right", va="center", fontsize=10)
    ax.set_ylim(-0.8, 1.6)
    timeline(ax, duration)
    kept = sum(seconds(x["end_time"]) - seconds(x["start_time"]) for x in found)
    dropped = sum(bool(s["drop"]) for s in after)
    ax.set_title(
        f"{len(found)} windows of 5 to 30 s, {kept:.0f} s of the {duration:.0f} s; "
        + (
            f"in brown, {dropped} segments marked by mark_non_subtitles"
            if dropped
            else "no segment marked by mark_non_subtitles"
        ),
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(out / "windows.png", dpi=150)
    plt.close(fig)

    # 3. the language heard in each window
    with tempfile.TemporaryDirectory() as tmp:
        paths = AudioGenerator(VIDEO, tmp_audio_dir=tmp).extract_segments(found)
        heard = LanguageID().hear([str(p) for p in paths])
    fig, ax = plt.subplots(figsize=(11, 3))
    x = range(len(heard))
    ax.bar([i - 0.2 for i in x], [hd["moore"] for hd in heard], 0.4, color=ORANGE, label="Moore")
    ax.bar([i + 0.2 for i in x], [hd["french"] for hd in heard], 0.4, color=GREY, label="French")
    ax.set_xticks(list(x), [str(i + 1) for i in x], fontsize=8)
    for i, hd in enumerate(heard):
        ax.text(i, 1.02, hd["language"], ha="center", va="bottom", fontsize=7, rotation=90)
    ax.set_xlabel("window")
    ax.set_ylabel("probability")
    ax.set_ylim(0, 1)
    ax.legend(frameon=False)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    moore = sum(hd["language"] == "moore" for hd in heard)
    ax.set_title(
        f"MMS-LID hears Moore in {moore} of the {len(heard)} windows; above each, the language it hears most",
        fontsize=10,
        pad=34,
    )
    fig.tight_layout()
    fig.savefig(out / "language.png", dpi=150)
    plt.close(fig)
    print(len(before), len(after), len(found), moore, len(heard))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
