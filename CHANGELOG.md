# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- `VLMOCR` runs on Apple's GPU (MPS) when there is no CUDA, and loads Qwen3-VL in bfloat16 there: on a Mac M5 it
  reads as float32 does, 30 times faster. It fell back to the CPU before.
- `strip_overlays` and `process_batch(overlay_frames=60)` take logos and banners out of the frames before
  merging; `mark_non_subtitles` marks credits, the video's title and scrolling text in the merged segments. The
  rules come from gom-dɛɛsa.
- `windows` joins subtitles less than 2 s apart into windows of 5 to 30 s, as segments `AudioGenerator` cuts.

### Security

- certifi 2026.10.23 in `uv.lock`, and uv pinned to 0.13.4 in CI and in the pre-commit hook: earlier versions trust
  the compromised emSign ECC Root CA - G3 root.

### Changed

- The project lives at `BurkimbIA/Frame2Text4LLM`; the documentation moved to
  <https://burkimbia.github.io/Frame2Text4LLM/>.
- The version is set in `pyproject.toml`; `HISTORY.md` is now `CHANGELOG.md`.

## [0.1.0] - 2026-10-06

First release on PyPI.

### Added

- `pyproject.toml`, built with hatchling, and `uv.lock` for development. The OCR engines are
  extras: `easyocr`, `paddle`, `vlm`, `openai`, `all`.
- `VLMOCR` reads with any image-text-to-text model of transformers, Qwen3-VL-2B by default: on
  48 subtitle frames it made 0.53 % character error, against 37.49 % for `tool="easyocr"`.
- `merge_segments`: readings of one subtitle are merged when they share most of their words, one
  empty frame does not end a subtitle, and each segment has `best_time`, the frame read best.
- `OCRManager(region=...)`: the subtitle band, detected once per video when it is not given.
- `YoutubeConsumer(client=...)`: the pytubefix client, `MWEB` by default; files are named
  `youtube_<id>.mp4`.
- A documentation site: <https://sawallesalfo.github.io/Frame2Text4LLM/>.

### Fixed

- A segment ends when its subtitle leaves the screen; a subtitle seen on one frame no longer lasts
  0 s.
- `AudioGenerator` reads the frames' `MM:SS:mmm` times and seeks before reading: audio was cut in
  the wrong place.
- `SubtitleRegionDetector` takes the full width of the image; its margin cut the first letters.
- `OCRManager` loads a model once, not once per image.
- `SRTExporter` writes valid times past an hour, and each subtitle's own end.

## [0.0.1]

- First version, not published.
