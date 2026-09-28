"""
Vision analysis service.

Input is the recorded video file (one WebM/MP4 from the browser's
MediaRecorder). OpenCV reads it on the server and samples roughly one frame
per second - the browser never uploads frame images.

For every sampled frame:

    frame -> face detection (OpenCV Haar cascade, ships with opencv)
          -> eye-contact estimate (frontal face found near the frame centre)
          -> movement estimate (how much the picture changed since the
                                previous sampled frame)

and the results are aggregated over the whole recording:

    face_detection    % of sampled frames with a frontal face
    eye_contact       % of sampled frames with a frontal face near the centre
                      (an estimate, not a precise gaze measurement)
    gesture_activity  low / medium / high, from frame-to-frame movement
                      (simple motion measure, not gesture recognition)

Metrics that cannot be computed are ``None``.

A landmark / pose model or a temporal network (LSTM/GRU/Transformer) could be
added later by consuming the same sampled frames; the return shape stays the
same.
"""
import logging
import os

import cv2
import numpy as np

logger = logging.getLogger(__name__)

SAMPLE_INTERVAL_SECONDS = 1.0     # one analysed frame per second of video
MAX_SAMPLED_FRAMES = 180          # bounds processing time for long recordings
MAX_FRAME_WIDTH = 640             # frames are downscaled before analysis
FALLBACK_FPS = 30.0               # only used if neither timestamps nor duration are known

# Eye-contact estimate: face centre must be within this fraction of the
# half-width from the centre of the frame.
CENTER_TOLERANCE = 0.28

# Gesture activity: share of pixels that changed noticeably between two
# consecutive sampled frames (after downscaling + blur).
MOTION_PIXEL_DELTA = 25
MOTION_LOW_BELOW = 0.02
MOTION_HIGH_FROM = 0.08

_face_cascade = None


def _get_cascade():
    global _face_cascade
    if _face_cascade is None:
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        if cascade.empty():
            raise RuntimeError("The OpenCV face detector could not be loaded.")
        _face_cascade = cascade
    return _face_cascade


def is_ready() -> bool:
    """True when the visual analysis can run on this server."""
    try:
        _get_cascade()
        return True
    except Exception:
        logger.exception("[VISION] Face detector unavailable")
        return False


def _downscale(image):
    height, width = image.shape[:2]
    if width <= MAX_FRAME_WIDTH:
        return image
    scale = MAX_FRAME_WIDTH / float(width)
    return cv2.resize(image, (MAX_FRAME_WIDTH, max(1, int(height * scale))), interpolation=cv2.INTER_AREA)


# --------------------------------------------------------------------------
# Frame sampling
# --------------------------------------------------------------------------
def _sampling_interval(duration_hint):
    interval = SAMPLE_INTERVAL_SECONDS
    if duration_hint and duration_hint > 0:
        interval = max(interval, duration_hint / MAX_SAMPLED_FRAMES)
    return interval


def _sample_by_timestamp(video_path, interval):
    """Single pass using the timestamps stored in the file.

    Returns (samples, frames_seen, last_timestamp, timestamps_monotonic).
    """
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        capture.release()
        raise ValueError("The recorded video could not be opened.")
    samples, frames_seen, last_ts, monotonic = [], 0, None, True
    next_sample_at = 0.0
    try:
        while capture.grab():
            frames_seen += 1
            ts = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            if last_ts is not None and ts < last_ts - 1e-6:
                monotonic = False
            last_ts = ts
            if ts >= next_sample_at - 1e-9 and len(samples) < MAX_SAMPLED_FRAMES:
                ok, image = capture.retrieve()
                if ok and image is not None:
                    samples.append((round(ts, 3), _downscale(image)))
                while next_sample_at <= ts + 1e-9:
                    next_sample_at += interval
    finally:
        capture.release()
    return samples, frames_seen, last_ts, monotonic


def _sample_by_index(video_path, total_frames, duration, interval):
    """Second strategy: spread samples evenly over the frames that exist.

    Browser recordings (MediaRecorder WebM) often carry no usable frame rate
    or duration, so OpenCV's fps / timestamps can be wrong (a nonsense value
    such as 1000 fps). Choosing frames by index and the *real* recording
    duration does not depend on either.
    """
    wanted_count = int(max(1, min(MAX_SAMPLED_FRAMES, round(duration / interval))))
    wanted = sorted(set(np.linspace(0, total_frames - 1, wanted_count).astype(int).tolist()))
    wanted_set = set(wanted)
    seconds_per_frame = duration / float(total_frames)

    capture = cv2.VideoCapture(video_path)
    samples = []
    try:
        index = 0
        last_wanted = wanted[-1]
        while capture.grab():
            if index in wanted_set:
                ok, image = capture.retrieve()
                if ok and image is not None:
                    samples.append((round(index * seconds_per_frame, 3), _downscale(image)))
            index += 1
            if index > last_wanted:
                break
    finally:
        capture.release()
    return samples


def sample_video_frames(video_path, duration_hint=None):
    """Return a list of (timestamp_seconds, BGR image), about one per second."""
    interval = _sampling_interval(duration_hint)
    samples, frames_seen, last_ts, monotonic = _sample_by_timestamp(video_path, interval)
    if frames_seen == 0:
        return []

    timestamps_usable = monotonic and last_ts is not None and last_ts > 0
    if timestamps_usable and duration_hint and duration_hint > 0:
        # If the file's own timeline disagrees badly with the measured
        # recording duration, do not trust it.
        timestamps_usable = 0.5 * duration_hint <= last_ts <= 1.5 * duration_hint + 2

    if timestamps_usable:
        logger.info("[VISION] Sampled %s frames by timestamp (frames=%s, video_seconds=%.1f)",
                    len(samples), frames_seen, last_ts)
        return samples

    duration = duration_hint if duration_hint and duration_hint > 0 else frames_seen / FALLBACK_FPS
    logger.info("[VISION] Video timestamps unreliable (last=%s, frames=%s); sampling by frame index over %.1fs",
                last_ts, frames_seen, duration)
    return _sample_by_index(video_path, frames_seen, duration, interval)


# --------------------------------------------------------------------------
# Per-frame analysis + aggregation
# --------------------------------------------------------------------------
def _detect_face_box(gray):
    faces = _get_cascade().detectMultiScale(gray, scaleFactor=1.15, minNeighbors=5, minSize=(40, 40))
    if len(faces) == 0:
        return None
    return max(faces, key=lambda f: f[2] * f[3])  # largest face = presenter


def _motion_ratio(previous_small, current_small):
    diff = cv2.absdiff(previous_small, current_small)
    return float(np.mean(diff > MOTION_PIXEL_DELTA))


def analyze_frames(frames: list) -> dict:
    """`frames` is a list of (timestamp_seconds, BGR image)."""
    total = len(frames)
    detected = centered = 0
    motion_values = []
    previous_small = None

    for _, image in frames:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape

        box = _detect_face_box(gray)
        if box is not None:
            detected += 1
            x, _, box_w, _ = box
            offset = abs((x + box_w / 2.0) - width / 2.0) / (width / 2.0)
            if offset < CENTER_TOLERANCE:
                centered += 1

        small = cv2.GaussianBlur(cv2.resize(gray, (160, 120), interpolation=cv2.INTER_AREA), (5, 5), 0)
        if previous_small is not None:
            motion_values.append(_motion_ratio(previous_small, small))
        previous_small = small

    gesture = None
    if motion_values:
        movement = float(np.mean(motion_values))
        gesture = "low" if movement < MOTION_LOW_BELOW else ("high" if movement >= MOTION_HIGH_FROM else "medium")
        logger.info("[VISION] movement=%.4f -> gesture_activity=%s", movement, gesture)

    result = {
        "frames_analyzed": total,
        "face_detection": round(100 * detected / total) if total else None,
        # Only estimated when a face was seen at all; the denominator is every
        # sampled frame, so looking away lowers the value.
        "eye_contact": round(100 * centered / total) if detected else None,
        "gesture_activity": gesture,
    }
    logger.info("[VISION] frames=%s face=%s eye_contact=%s gesture=%s",
                total, result["face_detection"], result["eye_contact"], gesture)
    return result


def analyze_video(video_path: str, duration_hint=None) -> dict:
    """Sample the recorded video and analyse the sampled frames.

    ``duration_hint`` is the measured recording length in seconds (from the
    browser); it is only used to sanity-check / rebuild the video timeline.
    Raises ValueError if no frame could be read.
    """
    logger.info("[VISION] Video path=%s size=%s", video_path,
                os.path.getsize(video_path) if os.path.exists(video_path) else 0)
    frames = sample_video_frames(video_path, duration_hint)
    if not frames:
        raise ValueError("No frames could be read from the recorded video.")
    return analyze_frames(frames)
