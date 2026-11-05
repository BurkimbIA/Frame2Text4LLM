import pytest

torch = pytest.importorskip("torch")
from frame2text4llm.ocr.tools import vlmocr  # noqa: E402


def test_pick_device_prefers_cuda_then_mps(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: True)
    assert vlmocr.pick_device() == "mps"
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)
    assert vlmocr.pick_device() == "cpu"
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert vlmocr.pick_device() == "cuda:0"


def test_bfloat16_on_mps_and_recent_gpus_only(monkeypatch):
    assert vlmocr.reads_bfloat16("mps")
    assert not vlmocr.reads_bfloat16("cpu")
    monkeypatch.setattr(torch.cuda, "get_device_capability", lambda: (7, 5))  # a T4
    assert not vlmocr.reads_bfloat16("cuda:0")
    monkeypatch.setattr(torch.cuda, "get_device_capability", lambda: (8, 0))
    assert vlmocr.reads_bfloat16("cuda:0")
