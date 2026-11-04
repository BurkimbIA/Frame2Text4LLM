"""What is on screen but is not a subtitle, found from the OCR's text alone: logos and banners, credits,
scrolling text. The rules come from gom-dɛɛsa (BurkimbIA/bia-speech-translation, decisions D18 and D19),
measured on Burkinabè videos subtitled in French."""

import re
import string
import unicodedata
from difflib import SequenceMatcher
from typing import Any

# credits, at the start or the end of a film: who did what, a role and a name joined by dots
CREDITS = re.compile(
    r"r[ée]alisat|sc[ée]nar|sous[- ]?titr|montage|mixage|casting|cadreur|cam[ée]raman|r[ée]gisseur|"
    r"maquill|costumi|production|produit par|un film de|id[ée]e originale|droits r[ée]serv|copy ?right|"
    r"consultant|"
    r"lumi[eè]re ?:|\bOP[VS]\b|com[ée]diens?\b|en hommage|cr[ée]+e par|une s[ée]rie|aimable participation|"
    r"©|[._]{4,}",
    re.I,
)
# a cast list: a first name and a NAME, as credits print them
NAME = re.compile(r"\b[A-ZÀ-Ý][a-zà-ÿ]+(?:-[A-ZÀ-Ý][a-zà-ÿ]+)? [A-ZÀ-Ý]{3,}\b")


def seconds(time_formatted: str) -> float:
    """A frame's `MM:SS:mmm` time in seconds; minutes may pass 59."""
    m, s, ms = (int(x) for x in time_formatted.split(":"))
    return m * 60 + s + ms / 1000


def _fold(word: str) -> str:
    """A word as compared across readings: lower case, no accent, no punctuation around it."""
    plain = unicodedata.normalize("NFKD", word.lower()).encode("ascii", "ignore").decode()
    return plain.strip(string.punctuation)


def _key(word: str) -> str:
    """A word as compared across frames: lower case, letters and digits only, so that `clideo.com` is
    `clideocom`."""
    return "".join(c for c in word.lower() if c.isalnum())


def _keys(text: str) -> set[str]:
    """The frame's words as keys, and each two neighbours joined: the OCR reads one logo as `clideo com` on a
    frame and `clideocom` on the next."""
    k = [_key(w) for w in text.split()]
    k = [w for w in k if w]
    return set(k) | {a + b for a, b in zip(k, k[1:], strict=False)}


def strip_overlays(results: list[dict[str, Any]], frames: int = 60, holes: int = 2) -> dict[str, set[str]]:
    """Take out of the frames' text the words read on at least `frames` frames in a row, up to `holes` frames
    missed: 30 s at 2 frames a second. No subtitle stays that long; a logo, a banner or a credit line does.
    Left in, they make `_merge_segments` join every subtitle shown with them into one segment.

    Words are compared without case or punctuation, and two neighbours also count joined, so that the readings
    `clideo com`, `clideocom` and `clideo.com` of one logo are one word. Changes `results` in place, in time
    order as OCRBatchProcessor returns them, and returns the words taken from each frame, by its
    `time_formatted`."""
    seen: dict[str, list[int]] = {}
    for i, r in enumerate(results):
        if r.get("success"):
            for w in _keys(r.get("text", "")):
                seen.setdefault(w, []).append(i)
    removed: dict[int, set[str]] = {}
    for w, at in seen.items():
        run = [at[0]]
        for i in [*at[1:], None]:
            if i is not None and i - run[-1] <= holes + 1:
                run.append(i)
                continue
            if run[-1] - run[0] + 1 >= frames:
                for j in run:
                    removed.setdefault(j, set()).add(w)
            if i is not None:
                run = [i]
    for j, words in removed.items():
        tokens, kept, k = results[j]["text"].split(), [], 0
        while k < len(tokens):
            if k + 1 < len(tokens) and _key(tokens[k]) + _key(tokens[k + 1]) in words:
                k += 2
            elif _key(tokens[k]) in words:
                k += 1
            else:
                kept.append(tokens[k])
                k += 1
        results[j]["text"] = " ".join(kept)
    return {results[j]["time_formatted"]: words for j, words in removed.items()}


def _capitals(text: str) -> int:
    """How many words of three letters or more are written in capitals: names in credits are."""
    words = (w.strip(string.punctuation).replace("-", "") for w in text.split())
    return sum(len(w) >= 3 and w.isalpha() and w.isupper() for w in words)


def _shifted(a: str, b: str) -> bool:
    """Two readings that share a run of at least 10 characters and half the shorter: one text, moved."""
    a, b = a.lower(), b.lower()
    size = SequenceMatcher(None, a, b, autojunk=False).find_longest_match().size
    return a != b and size >= max(10, min(len(a), len(b)) / 2)


def mark_non_subtitles(
    segments: list[dict[str, Any]], duration: int | float, title: str = ""
) -> list[dict[str, Any]]:
    """Give each merged segment a `drop`: "" for a subtitle, else what it is.

    - "credits": a credits keyword, two words in capitals, a first name and a NAME, or the video's `title`.
      A credit after 85 % of the video's `duration` (seconds) drops everything after it too.
    - "ticker": three segments or more in a row, each the one before moved, as a scrolling text is read.

    Changes `segments` in place and returns them. Segments are `_merge_segments`'s, in time order."""
    folded_title = re.sub(r"[^a-z0-9]+", "_", _fold(title)).strip("_")
    tail = False
    for s in segments:
        text = s.get("text", "")
        s["drop"] = "" if text.strip() else "empty"
        if s["drop"]:
            continue
        line = re.sub(r"[^a-z0-9]+", "_", _fold(text)).strip("_")
        # shortcut: a video subtitled all in capitals loses every line here; none of gom-dɛɛsa's is
        if (
            tail
            or CREDITS.search(text)
            or _capitals(text) >= 2
            or NAME.search(text)
            or (len(line) >= 4 and folded_title and line in folded_title)
        ):
            s["drop"] = "credits"
            tail = tail or seconds(s["start_time"]) > 0.85 * duration
    kept = [s for s in segments if not s["drop"]]
    run = kept[:1]
    for a, b in zip(kept, [*kept[1:], None], strict=True):
        if b is not None and _shifted(a["text"], b["text"]):
            run.append(b)
            continue
        if len(run) >= 3:
            for s in run:
                s["drop"] = "ticker"
        run = [b]
    return segments
