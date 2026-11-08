import asyncio
import math
import os
import tempfile
from pathlib import Path
from xml.etree import ElementTree

from .base import REVIEW_WARNING, AdapterError, TranscriptionResult


def parse_alto(content: str, model_id: str) -> TranscriptionResult:
    """Retain actual ALTO line boxes. Do not infer missing glyphs or confidence."""
    if len(content) > 20 * 1024 * 1024 or "<!DOCTYPE" in content or "<!ENTITY" in content:
        raise AdapterError("invalid_worker_output", "The local reader returned unsupported XML.")
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError:
        raise AdapterError(
            "invalid_worker_output", "The local reader did not return valid ALTO text."
        ) from None
    lines: list[str] = []
    regions: list[dict] = []
    for line in root.findall(".//{*}TextLine"):
        fragments: list[str] = []
        for child in line:
            tag = child.tag.rsplit("}", 1)[-1]
            if tag in {"String", "HYP"}:
                fragments.append(child.attrib.get("CONTENT", ""))
            elif tag == "SP":
                fragments.append(" ")
        text = "".join(fragments)
        lines.append(text)
        try:
            values = [float(line.attrib[key]) for key in ("HPOS", "VPOS", "WIDTH", "HEIGHT")]
            if not all(math.isfinite(value) and value >= 0 for value in values):
                continue
        except (KeyError, ValueError):
            continue
        x, y, width, height = values
        regions.append(
            {
                "type": "line",
                "text": text,
                "bbox": {"x": x, "y": y, "width": width, "height": height},
                "coordinate_system": "input_pixels",
                "page": 0,
            }
        )
    text = "\n".join(lines)
    if not text.strip():
        raise AdapterError("empty_transcription", "The local reader did not find readable text.")
    return TranscriptionResult(
        text=text,
        engine="kraken",
        model_id=model_id,
        regions=regions,
        warnings=[
            REVIEW_WARNING,
            "Historical recognition profiles can use different abbreviation and diacritic conventions.",
        ],
    )


async def transcribe_kraken(
    image_path: Path,
    executable: str,
    model_path: Path,
    model_id: str,
    *,
    segmentation_model: Path,
    timeout: float = 180,
) -> TranscriptionResult:
    if not image_path.is_file():
        raise AdapterError("invalid_image", "The selected image is not available.")
    if not model_path.is_file():
        raise AdapterError(
            "missing_model", "The selected local recognition weights are not installed."
        )
    if not segmentation_model.is_file():
        raise AdapterError("missing_model", "The local segmentation weights are not installed.")
    with tempfile.TemporaryDirectory(prefix="compass-kraken-") as directory:
        output = Path(directory) / "reading.xml"
        process = None
        try:
            options = {"creationflags": 0x08000000} if os.name == "nt" else {}
            process = await asyncio.create_subprocess_exec(
                executable,
                "-a",
                "-i",
                str(image_path.resolve()),
                str(output),
                "segment",
                "-bl",
                "-m",
                str(segmentation_model.resolve()),
                "ocr",
                "-m",
                str(model_path.resolve()),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                **options,
            )
            await asyncio.wait_for(process.wait(), timeout=timeout)
            if process.returncode != 0 or not output.is_file():
                raise AdapterError(
                    "worker_failed",
                    "The local reader failed. Check its runtime and profile compatibility.",
                )
            if output.stat().st_size > 20 * 1024 * 1024:
                raise AdapterError(
                    "invalid_worker_output", "The local reader output exceeded the size limit."
                )
            return parse_alto(output.read_text(encoding="utf-8"), model_id)
        except FileNotFoundError:
            raise AdapterError(
                "worker_not_installed", "The configured local image reader is not installed."
            ) from None
        except asyncio.TimeoutError:
            raise AdapterError(
                "worker_timeout", "The local image-reading task timed out."
            ) from None
        except OSError:
            raise AdapterError(
                "worker_failed", "The configured local reader could not run."
            ) from None
        finally:
            if process is not None and process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
