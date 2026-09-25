from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

import app.visual_intelligence as visual


class FakeOcrResult:
    def to_json(self) -> list[dict]:
        return [
            {"box": [[1, 1], [100, 1], [100, 20], [1, 20]], "txt": "ESP32-S3", "score": 0.98},
            {"box": [[1, 30], [100, 30], [100, 50], [1, 50]], "txt": "SILABS CP2102", "score": 0.96},
            {"box": [[1, 60], [100, 60], [100, 80], [1, 80]], "txt": "generic word", "score": 0.92},
        ]


class FakeOcr:
    def __call__(self, _image: bytes) -> FakeOcrResult:
        return FakeOcrResult()


def png_fixture() -> bytes:
    image = Image.new("RGB", (320, 160), "white")
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def test_board_image_returns_reviewable_marking_candidates(monkeypatch) -> None:
    monkeypatch.setattr(visual, "_ocr_engine", lambda: FakeOcr())
    report = visual.analyze_board_image(png_fixture(), "board.png")
    candidates = {item["marking"]: item for item in report["candidates"]}
    assert candidates["ESP32-S3"]["suggested_role"] == "mcu_soc"
    assert candidates["CP2102"]["suggested_role"] == "usb_uart_bridge"
    assert candidates["SILABS"]["suggested_role"] == "component_marking"
    assert "GENERIC" not in candidates
    assert report["needs_review"] is True
    assert report["privacy"] == {"image_persisted": False, "image_bytes_returned": False, "local_processing": True}


def test_board_image_rejects_invalid_and_oversized_inputs() -> None:
    with pytest.raises(visual.VisualAnalysisError, match="supported"):
        visual.analyze_board_image(b"not-an-image", "board.jpg")
    with pytest.raises(visual.VisualAnalysisError, match="MiB"):
        visual.analyze_board_image(b"x" * (visual.MAX_IMAGE_BYTES + 1), "board.jpg")
