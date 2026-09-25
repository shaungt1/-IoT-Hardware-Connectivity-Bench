from __future__ import annotations

import hashlib
import re
import threading
import warnings
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError
from rapidocr import RapidOCR


MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
MAX_OCR_DIMENSION = 2400
MARKING = re.compile(r"[A-Za-z][A-Za-z0-9._-]{2,31}")
KNOWN_WORDS = {"arduino", "espressif", "jetson", "nodemcu", "raspberry", "seeed", "silabs", "wifi", "xiao"}
ROLE_PATTERNS = (
    (re.compile(r"^(?:CP21\d\d|CH34\d|FT23\d|PL2303)", re.I), "usb_uart_bridge"),
    (re.compile(r"^(?:ESP32|ESP8266|NRF52|RP2040|STM32|ATMEGA|SAMD)", re.I), "mcu_soc"),
    (re.compile(r"^(?:AMS1117|AP2112|ME6211|XC6206)", re.I), "voltage_regulator"),
    (re.compile(r"^(?:OV\d{4}|GC\d{4})", re.I), "camera_sensor"),
    (re.compile(r"^(?:MPU\d+|LSM\w+|BME\d+|BMP\d+|DHT\d+)", re.I), "sensor"),
    (re.compile(r"^(?:XIAO|NODEMCU|ARDUINO|RASPBERRY|JETSON)", re.I), "board"),
)


class VisualAnalysisError(ValueError):
    pass


_ocr_lock = threading.Lock()


@lru_cache(maxsize=1)
def _ocr_engine() -> RapidOCR:
    return RapidOCR()


def _role_for(marking: str) -> str:
    return next((role for pattern, role in ROLE_PATTERNS if pattern.search(marking)), "component_marking")


def _candidates(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    found: dict[tuple[str, str], dict[str, Any]] = {}
    for line in lines:
        for raw in MARKING.findall(line["text"]):
            marking = raw.strip("._-").upper()
            if len(marking) < 3:
                continue
            if not (any(char.isdigit() for char in marking) and any(char.isalpha() for char in marking)) and marking.lower() not in KNOWN_WORDS:
                continue
            role = _role_for(marking)
            key = (marking, role)
            candidate = {
                "id": hashlib.sha256(f"{marking}:{role}".encode()).hexdigest()[:16],
                "marking": marking,
                "suggested_role": role,
                "ocr_confidence": line["confidence"],
                "status": "unconfirmed",
                "source_text": line["text"],
            }
            if key not in found or candidate["ocr_confidence"] > found[key]["ocr_confidence"]:
                found[key] = candidate
    return sorted(found.values(), key=lambda item: (-item["ocr_confidence"], item["marking"]))


def analyze_board_image(data: bytes, filename: str) -> dict[str, Any]:
    if not data:
        raise VisualAnalysisError("Image input is empty")
    if len(data) > MAX_IMAGE_BYTES:
        raise VisualAnalysisError(f"Image exceeds the {MAX_IMAGE_BYTES // (1024 * 1024)} MiB limit")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                source.verify()
            with Image.open(BytesIO(data)) as source:
                width, height = source.size
                if width * height > MAX_IMAGE_PIXELS:
                    raise VisualAnalysisError(f"Image exceeds the {MAX_IMAGE_PIXELS:,}-pixel limit")
                if getattr(source, "n_frames", 1) != 1:
                    raise VisualAnalysisError("Animated and multi-frame images are not accepted")
                normalized = ImageOps.exif_transpose(source).convert("RGB")
                normalized.thumbnail((MAX_OCR_DIMENSION, MAX_OCR_DIMENSION), Image.Resampling.LANCZOS)
                normalized_size = normalized.size
                buffer = BytesIO()
                normalized.save(buffer, format="PNG", optimize=True)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombWarning) as error:
        raise VisualAnalysisError("Input is not a supported, safe JPEG, PNG, or WebP image") from error

    with _ocr_lock:
        result = _ocr_engine()(buffer.getvalue())
    records = result.to_json() if result is not None else []
    lines = [{
        "text": str(item["txt"]).strip(),
        "confidence": round(float(item["score"]), 5),
        "box": [[round(float(x), 2), round(float(y), 2)] for x, y in item["box"]],
    } for item in records if str(item.get("txt", "")).strip() and float(item.get("score", 0)) >= 0.35]
    candidates = _candidates(lines)
    return {
        "schema_version": "1.0",
        "filename": Path(filename).name or "board-image",
        "sha256": hashlib.sha256(data).hexdigest(),
        "input_bytes": len(data),
        "input_dimensions": {"width": width, "height": height},
        "normalized_dimensions": {"width": normalized_size[0], "height": normalized_size[1]},
        "ocr_engine": "RapidOCR ONNX Runtime",
        "lines": lines,
        "candidates": candidates,
        "needs_review": True,
        "limitations": [
            "OCR markings are candidates, not proof of board topology or electrical connectivity.",
            "Hidden, unmarked, passive, and visually ambiguous components require other evidence.",
        ],
        "privacy": {"image_persisted": False, "image_bytes_returned": False, "local_processing": True},
    }
