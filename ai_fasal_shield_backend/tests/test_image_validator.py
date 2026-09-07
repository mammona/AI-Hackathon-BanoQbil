from io import BytesIO
from PIL import Image
from app.services.image_validator import ImageValidator


def make_image(size=(256, 256), value=128):
    image = Image.new("RGB", size, (value, value, value))
    buf = BytesIO()
    image.save(buf, format="JPEG")
    return buf.getvalue()


def test_invalid_bytes():
    result = ImageValidator().validate(b"not an image")
    assert result.ok is False


def test_too_small():
    result = ImageValidator().validate(make_image((64, 64)))
    assert result.ok is False
    assert result.reason == "image_too_small"
