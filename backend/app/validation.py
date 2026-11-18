from app.schemas import AssetKind

IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/webm"}
MAX_IMAGE_BYTES = 25 * 1024 * 1024
MAX_VIDEO_BYTES = 100 * 1024 * 1024


class UploadValidationError(ValueError):
    pass


def validate_upload(filename: str, content_type: str, size: int) -> AssetKind:
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        raise UploadValidationError("Use a simple filename without path segments.")
    if size <= 0:
        raise UploadValidationError(f"{filename} is empty.")
    if content_type in IMAGE_TYPES:
        if size > MAX_IMAGE_BYTES:
            raise UploadValidationError(f"{filename} exceeds the 25 MB image limit.")
        return AssetKind.PHOTO
    if content_type in VIDEO_TYPES:
        if size > MAX_VIDEO_BYTES:
            raise UploadValidationError(f"{filename} exceeds the 100 MB video limit.")
        return AssetKind.VIDEO
    raise UploadValidationError(
        f"{filename} is unsupported. Use JPEG, PNG, WebP, MP4, MOV, or WebM."
    )


def validate_upload_count(count: int, sample: bool = False) -> None:
    minimum = 1 if sample else 10
    maximum = 25
    if not minimum <= count <= maximum:
        raise UploadValidationError(
            f"Add between {minimum} and {maximum} media files; received {count}."
        )
