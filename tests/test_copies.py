import pytest

pytest.importorskip("rapidfuzz")
from frame2text4llm.copies import TextIndex  # noqa: E402


def index():
    t = TextIndex()
    t.add("youtube:a", ["Chef de famille", "je vous ai appelé avez-vous eu des nouvelles de Rose"])
    t.add("youtube:b", ["Le coronavirus est une maladie des Blancs", "Le vaccin nous protège"])
    return t


def test_a_noisy_reading_finds_its_video():
    score, key = index().closest("Le coronavlrus est une maladie des Blane")
    assert key == "youtube:b" and score >= 85


def test_a_line_from_no_video():
    score, _ = index().closest("Nous avons récolté le mil cette année")
    assert score < 70


def test_nothing_shared():
    assert index().closest("xyz") == (0.0, "")
