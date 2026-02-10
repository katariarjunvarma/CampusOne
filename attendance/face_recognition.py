from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
import ssl
import urllib.request

import cv2
import numpy as np


@dataclass(frozen=True)
class RecognizedFace:
    label: int
    confidence: float
    bbox: Tuple[int, int, int, int]


@dataclass(frozen=True)
class RecognizedEmbedding:
    label: int
    similarity: float
    bbox: Tuple[int, int, int, int]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _model_dir() -> Path:
    d = _project_root() / "media" / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


_YUNET_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/"
    "face_detection_yunet_2023mar.onnx"
)
_SFACE_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/"
    "face_recognition_sface_2021dec.onnx"
)


def _ensure_file(url: str, path: Path) -> None:
    if path.exists() and path.stat().st_size > 0:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")

    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = r.read()
    except Exception:
        # macOS Python often lacks system certs -> CERTIFICATE_VERIFY_FAILED.
        # These are public model files; retry without SSL verification.
        ctx = ssl._create_unverified_context()  # nosec - intended fallback
        with urllib.request.urlopen(url, timeout=30, context=ctx) as r:
            data = r.read()
    tmp.write_bytes(data)
    tmp.replace(path)


_yn_detector: "cv2.FaceDetectorYN | None" = None
_sf_recognizer: "cv2.FaceRecognizerSF | None" = None


def _get_yunet_and_sface() -> tuple["cv2.FaceDetectorYN", "cv2.FaceRecognizerSF"]:
    global _yn_detector, _sf_recognizer

    if _yn_detector is not None and _sf_recognizer is not None:
        return _yn_detector, _sf_recognizer

    model_dir = _model_dir()
    yunet_path = model_dir / "face_detection_yunet_2023mar.onnx"
    sface_path = model_dir / "face_recognition_sface_2021dec.onnx"
    _ensure_file(_YUNET_URL, yunet_path)
    _ensure_file(_SFACE_URL, sface_path)

    detector = cv2.FaceDetectorYN.create(str(yunet_path), "", (320, 320))
    recognizer = cv2.FaceRecognizerSF.create(str(sface_path), "")

    _yn_detector = detector
    _sf_recognizer = recognizer
    return detector, recognizer


def _l2_normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    if n <= 0:
        return v
    return (v / n).astype(np.float32)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a2 = _l2_normalize(a.reshape(-1))
    b2 = _l2_normalize(b.reshape(-1))
    return float(np.dot(a2, b2))


def _extract_embeddings(image_bgr: np.ndarray) -> List[tuple[np.ndarray, Tuple[int, int, int, int]]]:
    detector, recognizer = _get_yunet_and_sface()

    h, w = image_bgr.shape[:2]
    detector.setInputSize((w, h))

    ok, faces = detector.detect(image_bgr)
    if not ok or faces is None or len(faces) == 0:
        return []

    out: List[tuple[np.ndarray, Tuple[int, int, int, int]]] = []
    for f in faces:
        x, y, fw, fh = [int(v) for v in f[:4]]
        if fw < 60 or fh < 60:
            continue
        face_aligned = recognizer.alignCrop(image_bgr, f)
        feat = recognizer.feature(face_aligned)
        out.append((_l2_normalize(feat), (x, y, fw, fh)))
    return out


def detect_faces_count_embedding(image_bgr: np.ndarray) -> int:
    detector, _recognizer = _get_yunet_and_sface()
    h, w = image_bgr.shape[:2]
    detector.setInputSize((w, h))
    ok, faces = detector.detect(image_bgr)
    if not ok or faces is None:
        return 0
    # Count only reasonably sized faces
    c = 0
    for f in faces:
        fw, fh = int(f[2]), int(f[3])
        if fw >= 60 and fh >= 60:
            c += 1
    return int(c)


def build_embedding_gallery(images_by_label: Dict[int, List[np.ndarray]], min_per_student: int = 5) -> Dict[int, np.ndarray]:
    gallery: Dict[int, np.ndarray] = {}
    for sid, imgs in images_by_label.items():
        feats: List[np.ndarray] = []
        for img_bgr in imgs:
            for feat, _bbox in _extract_embeddings(img_bgr):
                feats.append(feat)
        if len(feats) < min_per_student:
            continue
        mean = _l2_normalize(np.mean(np.stack(feats, axis=0), axis=0))
        gallery[int(sid)] = mean
    return gallery


def recognize_embeddings_in_image(
    image_bgr: np.ndarray,
    gallery: Dict[int, np.ndarray],
    similarity_threshold: float = 0.45,
    ambiguity_margin: float = 0.04,
) -> List[RecognizedEmbedding]:
    results: List[RecognizedEmbedding] = []
    if not gallery:
        return results

    embeddings = _extract_embeddings(image_bgr)
    for feat, bbox in embeddings:
        scored = [(sid, _cosine_similarity(feat, g)) for sid, g in gallery.items()]
        scored.sort(key=lambda x: x[1], reverse=True)
        if not scored:
            continue
        best_sid, best_sim = scored[0]
        second_sim = scored[1][1] if len(scored) > 1 else -1.0
        if best_sim < similarity_threshold:
            continue
        if len(scored) > 1 and (best_sim - second_sim) < ambiguity_margin:
            continue
        results.append(RecognizedEmbedding(label=int(best_sid), similarity=float(best_sim), bbox=bbox))
    return results


def _to_gray_uint8(image_bgr: np.ndarray) -> np.ndarray:
    if image_bgr is None:
        raise ValueError("Empty image")
    if len(image_bgr.shape) == 2:
        return image_bgr
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)


def _detect_faces(gray: np.ndarray) -> List[Tuple[int, int, int, int]]:
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml")
    faces = detector.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=6, minSize=(60, 60))
    return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]


def _is_blurry(gray: np.ndarray, threshold: float = 90.0) -> bool:
    try:
        v = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    except Exception:
        return True
    return v < threshold


def _bbox_big_enough(bbox: Tuple[int, int, int, int], min_wh: int = 80) -> bool:
    _x, _y, w, h = bbox
    return w >= min_wh and h >= min_wh


def detect_faces_count(image_bgr: np.ndarray) -> int:
    gray = _to_gray_uint8(image_bgr)
    return int(len(_detect_faces(gray)))


def _crop_and_resize(gray: np.ndarray, bbox: Tuple[int, int, int, int], size: Tuple[int, int] = (200, 200)) -> np.ndarray:
    x, y, w, h = bbox
    roi = gray[y : y + h, x : x + w]
    roi = cv2.equalizeHist(roi)
    return cv2.resize(roi, size)


def train_lbph(training_images: List[np.ndarray], labels: List[int]) -> "cv2.face.LBPHFaceRecognizer":
    if len(training_images) == 0:
        raise ValueError("No training images")
    if len(training_images) != len(labels):
        raise ValueError("training_images and labels length mismatch")

    recognizer = cv2.face.LBPHFaceRecognizer_create(radius=2, neighbors=16, grid_x=8, grid_y=8)
    recognizer.train(training_images, np.array(labels, dtype=np.int32))
    return recognizer


def build_training_set(images_by_label: Dict[int, List[np.ndarray]]) -> Tuple[List[np.ndarray], List[int]]:
    train_images: List[np.ndarray] = []
    train_labels: List[int] = []

    for label, imgs in images_by_label.items():
        for img_bgr in imgs:
            gray = _to_gray_uint8(img_bgr)
            faces = _detect_faces(gray)
            if not faces:
                continue
            bbox = max(faces, key=lambda b: b[2] * b[3])
            if not _bbox_big_enough(bbox, min_wh=80):
                continue
            face_gray = gray[bbox[1] : bbox[1] + bbox[3], bbox[0] : bbox[0] + bbox[2]]
            if _is_blurry(face_gray, threshold=90.0):
                continue
            train_images.append(_crop_and_resize(gray, bbox))
            train_labels.append(int(label))

    return train_images, train_labels


def recognize_faces_in_image(
    recognizer: "cv2.face.LBPHFaceRecognizer",
    image_bgr: np.ndarray,
) -> List[RecognizedFace]:
    gray = _to_gray_uint8(image_bgr)
    bboxes = _detect_faces(gray)
    results: List[RecognizedFace] = []

    for bbox in bboxes:
        if not _bbox_big_enough(bbox, min_wh=80):
            continue
        face_gray = gray[bbox[1] : bbox[1] + bbox[3], bbox[0] : bbox[0] + bbox[2]]
        if _is_blurry(face_gray, threshold=90.0):
            continue
        roi = _crop_and_resize(gray, bbox)
        label, confidence = recognizer.predict(roi)
        results.append(RecognizedFace(label=int(label), confidence=float(confidence), bbox=bbox))

    return results


def detect_eyes_count(image_bgr: np.ndarray) -> int:
    gray = _to_gray_uint8(image_bgr)
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
    eyes = detector.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=6, minSize=(18, 18))
    return int(len(eyes))
