import asyncio
import math
import os
import re
import tempfile
from pathlib import Path, PurePosixPath
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


def wsl_kraken_prefix(distribution: str, *paths: str) -> list[str]:
    """Validate private configuration before starting a shell-free WSL process."""
    if os.name != "nt" or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._()-]{0,79}", distribution):
        raise AdapterError("invalid_worker_config", "Choose an installed Windows WSL distribution.")
    wsl = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "wsl.exe"
    if not wsl.is_file():
        raise AdapterError("worker_not_installed", "Windows Subsystem for Linux is not available.")
    if any(not path or not PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts
           or any(ord(char) < 32 for char in path) for path in paths):
        raise AdapterError("invalid_worker_config", "Kraken in WSL requires absolute Linux paths for its executable and weights.")
    return [str(wsl), "--distribution", distribution, "--exec"]


async def _wsl_path(prefix: list[str], path: Path) -> str:
    process = await asyncio.create_subprocess_exec(
        *prefix, "/usr/bin/wslpath", "-a", "-u", str(path.resolve()),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        creationflags=0x08000000,
    )
    try:
        output, _ = await asyncio.wait_for(process.communicate(), timeout=25)
        value = output.decode("utf-8").rstrip("\r\n")
        if process.returncode or not PurePosixPath(value).is_absolute() or "\n" in value or "\x00" in value:
            raise AdapterError("worker_path_unavailable", "The WSL reader could not access the working image path.")
        return value
    finally:
        await _stop_owned_process(process)


async def _stop_owned_process(process) -> None:
    if process is not None and process.returncode is None:
        try:
            process.terminate()
        except ProcessLookupError:
            return
        try:
            await asyncio.wait_for(process.wait(), timeout=5)
        except asyncio.TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            await process.wait()


async def transcribe_kraken(
    image_path: Path,
    executable: str,
    model_path: Path | str,
    model_id: str,
    *,
    segmentation_model: Path | str,
    wsl_distribution: str = "",
    language: str | None = None,
    timeout: float = 180,
) -> TranscriptionResult:
    if not image_path.is_file():
        raise AdapterError("invalid_image", "The selected image is not available.")
    prefix = wsl_kraken_prefix(wsl_distribution, executable, str(model_path), str(segmentation_model)) if wsl_distribution else []
    if not prefix and not Path(model_path).is_file():
        raise AdapterError(
            "missing_model", "The selected local recognition weights are not installed."
        )
    if not prefix and not Path(segmentation_model).is_file():
        raise AdapterError("missing_model", "The local segmentation weights are not installed.")
    with tempfile.TemporaryDirectory(prefix="compass-kraken-") as directory:
        output = Path(directory) / "reading.xml"
        process = None
        try:
            options = {"creationflags": 0x08000000} if os.name == "nt" else {}
            if prefix:
                image_arg, output_arg = await asyncio.gather(_wsl_path(prefix, image_path), _wsl_path(prefix, output))
                model_arg, segmenter_arg = str(model_path), str(segmentation_model)
                # A Linux deadline also bounds work if the Windows client stops unexpectedly.
                command = [*prefix, "/usr/bin/timeout", "--kill-after=5s", f"{int(timeout)}s",
                           "/usr/bin/env", "OMP_NUM_THREADS=4", "MKL_NUM_THREADS=4", executable]
            else:
                image_arg, output_arg = str(image_path.resolve()), str(output)
                model_arg, segmenter_arg = str(Path(model_path).resolve()), str(Path(segmentation_model).resolve())
                command = [executable]
            script = (language or "").casefold().replace("_", "-").split("-", 1)[0]
            direction = "horizontal-rl" if script in {"ar", "ara", "arabic", "he", "heb", "hebrew"} else "horizontal-lr"
            process = await asyncio.create_subprocess_exec(
                *command,
                "-f",
                "image",
                "-a",
                "-r",
                "-i",
                image_arg,
                output_arg,
                "segment",
                "-bl",
                "--text-direction",
                direction,
                "--model",
                segmenter_arg,
                "ocr",
                "--model",
                model_arg,
                "--num-line-workers",
                "0",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                **options,
            )
            await asyncio.wait_for(process.wait(), timeout=timeout)
            if prefix and process.returncode in {124, 137}:
                raise AdapterError("worker_timeout", "The local image-reading task timed out.")
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
        except (OSError, UnicodeError):
            raise AdapterError(
                "worker_failed", "The configured local reader could not run."
            ) from None
        finally:
            await _stop_owned_process(process)
