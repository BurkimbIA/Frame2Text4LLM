"""The rules that tell a subtitle from other text on screen."""

import numpy as np

from frame2text4llm.framer.base import VideoFrame
from frame2text4llm.ocr.utils.filters import mark_non_subtitles, seconds, strip_overlays
from frame2text4llm.ocr.utils.text_utils import _merge_segments


def frames(texts, fps=2):
    return [
        {"time_formatted": VideoFrame(np.zeros(1), i / fps, i).time_formatted, "text": x, "success": True}
        for i, x in enumerate(texts)
    ]


def segment(text, start):
    t = VideoFrame(np.zeros(1), float(start), 0).time_formatted
    return {"text": text, "start_time": t, "end_time": t}


def test_seconds_past_an_hour():
    assert seconds("97:12:500") == 97 * 60 + 12.5


def test_a_logo_on_screen_for_40_s_leaves_the_subtitles_apart():
    texts = ["LOGO Bonjour chef"] * 10 + ["LOGO"] * 60 + ["LOGO Et la famille"] * 10
    results = frames(texts)
    removed = strip_overlays(results)
    assert all("logo" in w for w in removed.values()) and len(removed) == 80
    merged = _merge_segments(results)
    assert [s["text"] for s in merged] == ["Bonjour chef", "Et la famille"]


def test_a_subtitle_shown_10_s_stays():
    results = frames(["Bonjour chef"] * 20)
    assert strip_overlays(results) == {}
    assert results[0]["text"] == "Bonjour chef"


def test_credits_and_what_follows_them_at_the_end():
    segments = [
        segment("Bonjour chef !", 10),
        segment("Réalisation : Boubacar", 20),
        segment("Et la famille ?", 30),
        segment("Avec Awa OUEDRAOGO", 95),
        segment("Montage : Ali", 96),
        segment("Merci à tous", 98),
    ]
    drops = [s["drop"] for s in mark_non_subtitles(segments, duration=100)]
    assert drops == ["", "credits", "", "credits", "credits", "credits"]


def test_one_credit_word_late_in_the_dialogue_drops_only_its_line():
    segments = [segment("La production de coton a baissé", 88), segment("Il faut aider les paysans", 92)]
    assert [s["drop"] for s in mark_non_subtitles(segments, duration=100)] == ["credits", ""]


def test_nothing_left_after_the_credits_does_not_crash():
    assert mark_non_subtitles([], 100) == []
    assert [s["drop"] for s in mark_non_subtitles([segment("Réalisation : X", 1)], 100)] == ["credits"]


def test_the_title_is_not_a_subtitle():
    segments = mark_non_subtitles(
        [segment("Ah ! Ouaga !", 5), segment("On y va ?", 9)], 600, title="Ah! Ouaga!"
    )
    assert [s["drop"] for s in segments] == ["credits", ""]


def test_a_scrolling_text_read_three_times():
    line = "Le ministère de la Santé informe la population que la campagne commence lundi"
    segments = [segment(line[i:] + " " + line[:i], t) for i, t in ((0, 1), (6, 2), (12, 3))]
    segments.append(segment("Bonjour chef !", 10))
    assert [s["drop"] for s in mark_non_subtitles(segments, 600)] == ["ticker", "ticker", "ticker", ""]


def test_a_logo_read_three_ways_is_one_word():
    reads = ["clideo com", "clideocom", "clideo.com"]
    texts = [f"Bonjour chef {reads[i % 3]}" for i in range(20)] + [reads[i % 3] for i in range(60)]
    results = frames(texts)
    strip_overlays(results)
    assert {r["text"] for r in results} == {"Bonjour chef", ""}
