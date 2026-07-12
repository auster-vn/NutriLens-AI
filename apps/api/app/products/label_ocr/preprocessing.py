from __future__ import annotations

import io

import numpy as np
from app.products.label_ocr.contracts import PreprocessedImage, PreprocessingMetadata
from PIL import Image, ImageEnhance, ImageOps, UnidentifiedImageError

MAX_IMAGE_PIXELS = 24_000_000


class LabelImageError(ValueError):
    pass


def preprocess_image(image_bytes: bytes) -> PreprocessedImage:
    source = _load_image(image_bytes)
    original_width, original_height = source.size
    source.thumbnail((2400, 2400))
    rgb = np.asarray(source.convert("RGB"))
    try:
        enhanced, adaptive, metadata = _opencv_pipeline(rgb, original_width, original_height)
        variants = {
            "enhanced": Image.fromarray(enhanced),
            "adaptive": Image.fromarray(adaptive),
        }
    except ImportError:
        grayscale = ImageOps.autocontrast(source.convert("L"))
        enhanced_image = ImageEnhance.Sharpness(grayscale).enhance(1.4)
        array = np.asarray(enhanced_image)
        metadata = _fallback_metadata(array, original_width, original_height)
        variants = {"enhanced": enhanced_image, "adaptive": enhanced_image}
    return PreprocessedImage(variants=variants, metadata=metadata)


def _load_image(image_bytes: bytes) -> Image.Image:
    if not image_bytes:
        raise LabelImageError("The label image is empty.")
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise LabelImageError("The uploaded file is not a valid image.") from exc
    if image.width * image.height > MAX_IMAGE_PIXELS:
        raise LabelImageError("The label image resolution is too large.")
    return ImageOps.exif_transpose(image)


def _opencv_pipeline(
    rgb: np.ndarray,
    original_width: int,
    original_height: int,
) -> tuple[np.ndarray, np.ndarray, PreprocessingMetadata]:
    import cv2

    transforms: list[str] = ["exif_transpose", "resize_max_2400"]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())
    contrast = float(gray.std())
    glare_ratio = float(np.count_nonzero(gray >= 248) / gray.size)

    corrected, perspective_corrected = _correct_perspective(rgb)
    if perspective_corrected:
        transforms.append("perspective_warp")
        gray = cv2.cvtColor(corrected, cv2.COLOR_RGB2GRAY)
    skew_angle = _estimate_skew(gray)
    if 0.4 <= abs(skew_angle) <= 15:
        gray = _rotate(gray, skew_angle)
        transforms.append("deskew")
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    enhanced = cv2.GaussianBlur(clahe, (0, 0), 1.0)
    enhanced = cv2.addWeighted(clahe, 1.5, enhanced, -0.5, 0)
    adaptive = cv2.adaptiveThreshold(
        clahe,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        35,
        11,
    )
    transforms.extend(["clahe", "unsharp_mask", "adaptive_threshold"])
    issues = _quality_issues(blur_score, brightness, contrast, glare_ratio, gray.shape[1], gray.shape[0])
    penalties = min(0.8, 0.16 * len(issues))
    quality_score = round(max(0.0, 1.0 - penalties), 3)
    metadata = PreprocessingMetadata(
        original_width=original_width,
        original_height=original_height,
        output_width=int(gray.shape[1]),
        output_height=int(gray.shape[0]),
        blur_score=round(blur_score, 2),
        brightness=round(brightness, 2),
        contrast=round(contrast, 2),
        glare_ratio=round(glare_ratio, 4),
        skew_angle=round(skew_angle, 2),
        quality_score=quality_score,
        quality_issues=issues,
        perspective_corrected=perspective_corrected,
        transforms=transforms,
    )
    return enhanced, adaptive, metadata


def _correct_perspective(rgb: np.ndarray) -> tuple[np.ndarray, bool]:
    import cv2

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    image_area = rgb.shape[0] * rgb.shape[1]
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:8]:
        if cv2.contourArea(contour) < image_area * 0.22:
            continue
        perimeter = cv2.arcLength(contour, True)
        polygon = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(polygon) != 4:
            continue
        points = _order_points(polygon.reshape(4, 2).astype("float32"))
        width = int(max(np.linalg.norm(points[2] - points[3]), np.linalg.norm(points[1] - points[0])))
        height = int(max(np.linalg.norm(points[1] - points[2]), np.linalg.norm(points[0] - points[3])))
        if width < 200 or height < 120:
            continue
        destination = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype="float32")
        matrix = cv2.getPerspectiveTransform(points, destination)
        return cv2.warpPerspective(rgb, matrix, (width, height), borderMode=cv2.BORDER_REPLICATE), True
    return rgb, False


def _order_points(points: np.ndarray) -> np.ndarray:
    ordered = np.zeros((4, 2), dtype="float32")
    sums = points.sum(axis=1)
    differences = np.diff(points, axis=1).reshape(-1)
    ordered[0], ordered[2] = points[np.argmin(sums)], points[np.argmax(sums)]
    ordered[1], ordered[3] = points[np.argmin(differences)], points[np.argmax(differences)]
    return ordered


def _estimate_skew(gray: np.ndarray) -> float:
    import cv2

    inverted = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    coordinates = np.column_stack(np.where(inverted > 0))
    if len(coordinates) < 50:
        return 0.0
    angle = float(cv2.minAreaRect(coordinates[:, ::-1].astype("float32"))[-1])
    if angle < -45:
        angle = 90 + angle
    elif angle > 45:
        angle -= 90
    return angle


def _rotate(gray: np.ndarray, angle: float) -> np.ndarray:
    import cv2

    height, width = gray.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    return cv2.warpAffine(gray, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _quality_issues(
    blur: float, brightness: float, contrast: float, glare: float, width: int, height: int
) -> list[str]:
    issues: list[str] = []
    if blur < 55:
        issues.append("image_blurry")
    if brightness < 55:
        issues.append("image_too_dark")
    elif brightness > 225:
        issues.append("image_overexposed")
    if contrast < 28:
        issues.append("image_low_contrast")
    if glare > 0.18:
        issues.append("image_glare")
    if min(width, height) < 500:
        issues.append("image_resolution_low")
    return issues


def _fallback_metadata(array: np.ndarray, original_width: int, original_height: int) -> PreprocessingMetadata:
    brightness, contrast = float(array.mean()), float(array.std())
    issues = _quality_issues(
        100, brightness, contrast, float(np.count_nonzero(array >= 248) / array.size), *array.shape[::-1]
    )
    return PreprocessingMetadata(
        original_width=original_width,
        original_height=original_height,
        output_width=int(array.shape[1]),
        output_height=int(array.shape[0]),
        blur_score=0,
        brightness=round(brightness, 2),
        contrast=round(contrast, 2),
        glare_ratio=round(float(np.count_nonzero(array >= 248) / array.size), 4),
        skew_angle=0,
        quality_score=round(max(0.0, 1 - 0.16 * len(issues)), 3),
        quality_issues=issues + ["opencv_unavailable"],
        transforms=["exif_transpose", "resize_max_2400", "autocontrast", "sharpen"],
    )
