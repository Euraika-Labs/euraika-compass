import hashlib
import io
import os
import re
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from compass.errors import APIError


@dataclass(frozen=True)
class ImageInfo:
    sha256: str
    media_type: str
    width: int
    height: int


class BlobStore:
    def __init__(self, data_dir: Path, max_bytes: int, max_pixels: int):
        self.root = data_dir / "assets"
        self.staging = data_dir / "staging"
        self.max_bytes = max_bytes
        self.max_pixels = max_pixels

    def path(self, digest: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise APIError(400, "invalid_asset", "The asset identifier is invalid.")
        return self.root / digest[:2] / digest

    def store_image(self, data: bytes) -> ImageInfo:
        if len(data) > self.max_bytes:
            raise APIError(413, "image_too_large", "The image exceeds the upload size limit.")
        if not data:
            raise APIError(422, "invalid_image", "Choose a non-empty image file.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(data)) as image:
                    if image.format not in {"JPEG", "PNG", "WEBP"}:
                        raise APIError(415, "unsupported_image", "Use a JPEG, PNG or WebP image.")
                    width, height = image.size
                    if width * height > self.max_pixels:
                        raise APIError(413, "image_too_large", "The image exceeds the pixel limit.")
                    if getattr(image, "n_frames", 1) != 1:
                        raise APIError(415, "unsupported_image", "Animated images are not supported.")
                    media_type = Image.MIME[image.format]
                    image.verify()
                with Image.open(io.BytesIO(data)) as image:
                    image.load()
        except APIError:
            raise
        except (
            UnidentifiedImageError,
            SyntaxError,
            OSError,
            ValueError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as exc:
            raise APIError(422, "invalid_image", "The file is not a valid supported image.") from exc

        digest = hashlib.sha256(data).hexdigest()
        destination = self.path(digest)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            self.staging.mkdir(parents=True, exist_ok=True)
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(dir=self.staging, delete=False) as temp:
                    temp_path = Path(temp.name)
                    temp.write(data)
                    temp.flush()
                    os.fsync(temp.fileno())
                os.replace(temp_path, destination)
            except OSError as exc:
                raise APIError(507, "storage_failed", "The image could not be saved to local storage.") from exc
            finally:
                if temp_path is not None:
                    temp_path.unlink(missing_ok=True)
        return ImageInfo(digest, media_type, width, height)

    def crop(self, digest: str, region: dict | None) -> tuple[Path, bool]:
        original = self.path(digest)
        if not original.is_file():
            raise APIError(404, "asset_unavailable", "The saved image file is unavailable.")
        if region is None:
            return original, False
        self.staging.mkdir(parents=True, exist_ok=True)
        with Image.open(original) as image:
            x, y, width, height = (region[key] for key in ("x", "y", "width", "height"))
            if min(x, y) < 0 or min(width, height) <= 0:
                raise APIError(422, "invalid_region", "Choose a valid image region.")
            if x + width > image.width or y + height > image.height:
                raise APIError(422, "invalid_region", "The region lies outside the original image.")
            with tempfile.NamedTemporaryFile(suffix=".png", dir=self.staging, delete=False) as temp:
                path = Path(temp.name)
            try:
                image.crop((x, y, x + width, y + height)).save(path, format="PNG")
            except Exception:
                path.unlink(missing_ok=True)
                raise
        return path, True
