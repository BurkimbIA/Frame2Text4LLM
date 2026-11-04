"""Is a video a copy of one already read? The same film is often published by several channels, cut or
re-encoded: its duration does not tell, its subtitles do. From gom-dɛɛsa (BurkimbIA/bia-speech-translation,
S161 and S171), where one subtitle line read from a short clip finds its copy among thousands of videos.

A line read by OCR is noisy ("Blane" for "Blanc"), so neither a ratio of whole strings nor shared word
trigrams find its copy. Character 5-grams pick the ten videos closest to it, then the best alignment of the line
inside each video's whole text decides: 85 or more out of 100 was a copy there; between 70 and 85, look."""

import unicodedata
from collections import Counter, defaultdict

try:  # the copies extra
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return " ".join("".join(c for c in text if c.isalpha() or c == " ").split())


def _grams(text: str) -> set[str]:
    return {text[i : i + 5] for i in range(len(text) - 4)}


class TextIndex:
    """The subtitles of the videos read so far, to find which one a new line comes from."""

    def __init__(self):
        if fuzz is None:
            raise ImportError("TextIndex needs the copies extra: pip install 'frame2text4llm[copies]'")
        self.lines: dict[str, list[str]] = defaultdict(list)
        self.index: dict[str, set[str]] = defaultdict(set)

    def add(self, key: str, texts: list[str]) -> None:
        """A video's subtitles, under `key`."""
        for text in texts:
            line = _norm(text)
            self.lines[key].append(line)
            for g in _grams(line):
                self.index[g].add(key)

    def closest(self, line: str, candidates: int = 10) -> tuple[float, str]:
        """The score out of 100 of the best alignment of `line` inside a video's text, and that video's key;
        (0, "") when no video shares a 5-gram with it. Only the `candidates` videos sharing most 5-grams are
        aligned."""
        line = _norm(line)
        near = Counter(k for g in _grams(line) for k in self.index.get(g, ()))
        # one string a video: aligned against single subtitles, a two-letter one fits inside any line
        return max(
            ((fuzz.partial_ratio(line, " ".join(self.lines[k])), k) for k, _ in near.most_common(candidates)),
            default=(0.0, ""),
        )
