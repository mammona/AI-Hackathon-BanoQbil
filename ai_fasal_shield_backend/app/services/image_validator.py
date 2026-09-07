from dataclasses import dataclass
from io import BytesIO

from PIL import Image, UnidentifiedImageError

from app.config import get_settings


@dataclass
class ImageValidationResult:
    ok: bool
    reason: str | None
    image: Image.Image | None
    width: int | None = None
    height: int | None = None
    # Kept for backward compatibility with older diagnostics. The lightweight
    # prototype validator intentionally does not reject on these heuristics.
    brightness: float | None = None
    contrast_std: float | None = None
    edge_variance: float | None = None


class ImageValidator:
    """Cheap technical validation only.

    V17 prototype intentionally does NOT perform semantic crop validation.
    We only check that the upload is non-empty, reasonably sized, decodable,
    and large enough for the disease classifier.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def validate(self, content: bytes) -> ImageValidationResult:
        if not content:
            return ImageValidationResult(False, "empty_image", None)

        if len(content) > self.settings.max_image_mb * 1024 * 1024:
            return ImageValidationResult(False, "image_too_large", None)

        try:
            image = Image.open(BytesIO(content))
            image.verify()
            image = Image.open(BytesIO(content)).convert("RGB")
        except (UnidentifiedImageError, OSError, ValueError):
            return ImageValidationResult(False, "image_decode_failed", None)

        width, height = image.size
        if width < self.settings.min_image_width or height < self.settings.min_image_height:
            return ImageValidationResult(
                False,
                "image_too_small",
                image,
                width,
                height,
            )

        return ImageValidationResult(True, None, image, width, height)
