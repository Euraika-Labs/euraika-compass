import hashlib
import io

import pytest
from PIL import Image

from compass.errors import APIError
from compass.storage import BlobStore


def png_bytes():
    output = io.BytesIO()
    Image.new("RGB", (32, 24), "white").save(output, format="PNG")
    return output.getvalue()


def test_original_bytes_deduplicate_and_crop_is_separate(tmp_path):
    store = BlobStore(tmp_path, 100_000, 100_000)
    data = png_bytes()
    info = store.store_image(data)
    again = store.store_image(data)
    assert again.sha256 == info.sha256 == hashlib.sha256(data).hexdigest()
    assert store.path(info.sha256).read_bytes() == data
    crop, temporary = store.crop(info.sha256, {"x": 2, "y": 3, "width": 10, "height": 8})
    assert temporary
    with Image.open(crop) as image:
        assert image.size == (10, 8)
    assert store.path(info.sha256).read_bytes() == data
    crop.unlink()
    assert len(list(store.root.rglob("*"))) == 2  # Prefix directory and one original.


@pytest.mark.parametrize("content", [b"<svg><script>alert(1)</script></svg>", b"not an image", b""])
def test_invalid_image_cannot_be_stored(tmp_path, content):
    store = BlobStore(tmp_path, 100_000, 100_000)
    with pytest.raises(APIError):
        store.store_image(content)
    assert not store.root.exists()


def test_png_checksum_error_returns_invalid_image_without_storing(tmp_path):
    content = bytearray(png_bytes())
    idat = content.index(b"IDAT")
    payload_length = int.from_bytes(content[idat - 4 : idat], "big")
    content[idat + 4 + payload_length] ^= 1  # Corrupt IDAT CRC, leaving pixel data intact.
    with Image.open(io.BytesIO(content)) as image:
        image.load()  # Pixel decoding alone misses this checksum error.
    store = BlobStore(tmp_path, 100_000, 100_000)
    with pytest.raises(APIError) as error:
        store.store_image(bytes(content))
    assert error.value.status == 422
    assert error.value.code == "invalid_image"
    assert isinstance(error.value.__cause__, SyntaxError)
    assert not store.root.exists()
    assert not store.staging.exists()


def test_dimensions_and_regions_have_real_bounds(tmp_path):
    store = BlobStore(tmp_path, 100_000, 10)
    with pytest.raises(APIError) as error:
        store.store_image(png_bytes())
    assert error.value.code == "image_too_large"
    store = BlobStore(tmp_path, 100_000, 100_000)
    info = store.store_image(png_bytes())
    with pytest.raises(APIError) as error:
        store.crop(info.sha256, {"x": 30, "y": 0, "width": 10, "height": 2})
    assert error.value.code == "invalid_region"
    with pytest.raises(APIError):
        store.path("../../private")
