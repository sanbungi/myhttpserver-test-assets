from __future__ import annotations

import argparse
import math
from pathlib import Path

import cv2
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "html" / "videos"
DEFAULT_OUTPUT_PATH = DEFAULT_OUTPUT_DIR / "geometric-demo.webm"
DEFAULT_SIZE = (1280, 720)
DEFAULT_DURATION_SECONDS = 5.0
DEFAULT_FPS = 30
BACKGROUND_TOP = np.array((18, 28, 52), dtype=np.float32)
BACKGROUND_BOTTOM = np.array((6, 112, 160), dtype=np.float32)
TEXT_COLOR = (245, 248, 255)
TEXT_SHADOW = (24, 28, 40)
PANEL_COLOR = (16, 18, 28)
PANEL_BORDER = (210, 225, 255)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a simple geometric animation video fixture."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output video path. Default: html/videos/geometric-demo.webm",
    )
    parser.add_argument(
        "--size",
        type=parse_size,
        default=DEFAULT_SIZE,
        metavar="WIDTHxHEIGHT",
        help="Video resolution. Example: 1920x1080",
    )
    parser.add_argument(
        "--duration-seconds",
        type=float,
        default=DEFAULT_DURATION_SECONDS,
        help=f"Video duration in seconds. Default: {DEFAULT_DURATION_SECONDS}",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=DEFAULT_FPS,
        help=f"Frames per second. Default: {DEFAULT_FPS}",
    )
    parser.add_argument(
        "--codec",
        type=str,
        default=None,
        help="FourCC codec for cv2.VideoWriter. Default is inferred from the output extension.",
    )
    return parser.parse_args()


def parse_size(value: str) -> tuple[int, int]:
    parts = value.lower().split("x", maxsplit=1)
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("size must use WIDTHxHEIGHT format")

    try:
        width, height = (int(part) for part in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("size must contain integers") from exc

    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("size values must be positive")

    return width, height


def infer_codec(output_path: Path) -> str:
    suffix = output_path.suffix.lower()
    if suffix == ".webm":
        return "VP90"
    if suffix == ".mp4":
        return "mp4v"
    if suffix == ".avi":
        return "MJPG"
    return "VP90"


def build_background(width: int, height: int) -> np.ndarray:
    gradient = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    colors = BACKGROUND_TOP * (1.0 - gradient) + BACKGROUND_BOTTOM * gradient
    frame = np.repeat(colors[:, None, :], width, axis=1)

    x_wave = np.linspace(0.0, math.tau * 3.0, width, dtype=np.float32)
    wave = ((np.sin(x_wave) + 1.0) * 18.0).astype(np.float32)
    frame[:, :, 1] = np.clip(frame[:, :, 1] + wave[None, :], 0, 255)
    frame[:, :, 2] = np.clip(frame[:, :, 2] + wave[None, :] * 0.5, 0, 255)
    return frame.astype(np.uint8)


def draw_background_shapes(frame: np.ndarray, progress: float, width: int, height: int) -> None:
    band_y = int(height * (0.2 + 0.08 * math.sin(progress * math.tau * 1.5)))
    band_h = max(18, height // 12)
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, band_y), (width, min(height - 1, band_y + band_h)), (240, 160, 64), thickness=-1)
    cv2.addWeighted(overlay, 0.14, frame, 0.86, 0.0, dst=frame)

    for offset in range(5):
        wave_progress = progress + offset * 0.08
        center_x = int(width * (0.12 + 0.18 * offset + 0.08 * math.sin(wave_progress * math.tau)))
        center_y = int(height * (0.72 + 0.07 * math.cos(wave_progress * math.tau * 1.7)))
        radius = max(10, int(min(width, height) * (0.03 + offset * 0.003)))
        color = (
            min(255, 60 + offset * 28),
            min(255, 210 - offset * 18),
            min(255, 120 + offset * 22),
        )
        cv2.circle(frame, (center_x, center_y), radius, color, thickness=2, lineType=cv2.LINE_AA)


def draw_animated_shapes(frame: np.ndarray, frame_index: int, total_frames: int, width: int, height: int) -> None:
    progress = frame_index / max(total_frames - 1, 1)
    angle = progress * math.tau

    rect_w = max(80, width // 6)
    rect_h = max(56, height // 7)
    rect_x = int((width - rect_w) * (0.5 + 0.42 * math.sin(angle)))
    rect_y = int(height * (0.18 + 0.1 * math.cos(angle * 1.4)))
    cv2.rectangle(
        frame,
        (rect_x, rect_y),
        (rect_x + rect_w, rect_y + rect_h),
        (72, 200, 255),
        thickness=-1,
        lineType=cv2.LINE_AA,
    )
    cv2.rectangle(
        frame,
        (rect_x, rect_y),
        (rect_x + rect_w, rect_y + rect_h),
        (255, 255, 255),
        thickness=max(2, width // 640),
        lineType=cv2.LINE_AA,
    )

    circle_radius = max(24, min(width, height) // 12)
    circle_x = int(width * (0.2 + 0.6 * progress))
    circle_y = int(height * (0.52 + 0.16 * math.sin(angle * 2.0)))
    cv2.circle(frame, (circle_x, circle_y), circle_radius, (255, 170, 64), thickness=-1, lineType=cv2.LINE_AA)
    cv2.circle(
        frame,
        (circle_x, circle_y),
        circle_radius,
        (255, 250, 245),
        thickness=max(2, width // 640),
        lineType=cv2.LINE_AA,
    )

    triangle_center_x = int(width * (0.72 + 0.08 * math.sin(angle * 1.3)))
    triangle_center_y = int(height * (0.62 + 0.14 * math.cos(angle * 1.1)))
    triangle_radius = max(30, min(width, height) // 10)
    triangle_rotation = angle * 1.8
    points = []
    for vertex in range(3):
        theta = triangle_rotation + vertex * (math.tau / 3.0)
        points.append(
            (
                int(triangle_center_x + math.cos(theta) * triangle_radius),
                int(triangle_center_y + math.sin(theta) * triangle_radius),
            )
        )
    triangle = np.array(points, dtype=np.int32)
    cv2.fillConvexPoly(frame, triangle, (96, 245, 168), lineType=cv2.LINE_AA)
    cv2.polylines(
        frame,
        [triangle],
        isClosed=True,
        color=(255, 255, 255),
        thickness=max(2, width // 640),
        lineType=cv2.LINE_AA,
    )

    draw_background_shapes(frame, progress, width, height)


def draw_frame_label(frame: np.ndarray, frame_index: int, total_frames: int, fps: int, width: int, height: int) -> None:
    panel_x = max(18, width // 32)
    panel_y = max(18, height // 28)
    panel_w = max(280, width // 3)
    panel_h = max(84, height // 8)
    thickness = max(1, min(width, height) // 400)
    cv2.rectangle(
        frame,
        (panel_x, panel_y),
        (panel_x + panel_w, panel_y + panel_h),
        PANEL_COLOR,
        thickness=-1,
        lineType=cv2.LINE_AA,
    )
    cv2.rectangle(
        frame,
        (panel_x, panel_y),
        (panel_x + panel_w, panel_y + panel_h),
        PANEL_BORDER,
        thickness=thickness,
        lineType=cv2.LINE_AA,
    )

    font = cv2.FONT_HERSHEY_SIMPLEX
    title_scale = max(0.7, min(width, height) / 900)
    subtitle_scale = max(0.55, min(width, height) / 1200)
    baseline_x = panel_x + max(14, width // 64)
    title_y = panel_y + max(30, height // 18)
    subtitle_y = title_y + max(28, height // 16)
    seconds = frame_index / fps
    current_frame = frame_index + 1

    title = "Generated test video"
    subtitle = f"frame {current_frame:05d} / {total_frames:05d}   t={seconds:06.2f}s"

    cv2.putText(frame, title, (baseline_x + 2, title_y + 2), font, title_scale, TEXT_SHADOW, thickness + 2, cv2.LINE_AA)
    cv2.putText(frame, title, (baseline_x, title_y), font, title_scale, TEXT_COLOR, thickness + 1, cv2.LINE_AA)
    cv2.putText(frame, subtitle, (baseline_x + 2, subtitle_y + 2), font, subtitle_scale, TEXT_SHADOW, thickness + 2, cv2.LINE_AA)
    cv2.putText(frame, subtitle, (baseline_x, subtitle_y), font, subtitle_scale, TEXT_COLOR, thickness + 1, cv2.LINE_AA)


def validate_args(args: argparse.Namespace, codec: str) -> None:
    width, height = args.size
    if width < 64 or height < 64:
        raise ValueError("--size must be at least 64x64")
    if args.duration_seconds <= 0:
        raise ValueError("--duration-seconds must be greater than zero")
    if args.fps <= 0:
        raise ValueError("--fps must be greater than zero")
    if len(codec) != 4:
        raise ValueError("--codec must be a 4-character FourCC code")


def generate_video(output_path: Path, size: tuple[int, int], duration_seconds: float, fps: int, codec: str) -> None:
    width, height = size
    total_frames = max(1, int(round(duration_seconds * fps)))
    background = build_background(width, height)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*codec),
        float(fps),
        (width, height),
    )
    if not writer.isOpened():
        raise RuntimeError(f"failed to open video writer for {output_path} with codec {codec!r}")

    try:
        for frame_index in range(total_frames):
            frame = background.copy()
            draw_animated_shapes(frame, frame_index, total_frames, width, height)
            draw_frame_label(frame, frame_index, total_frames, fps, width, height)
            writer.write(frame)
    finally:
        writer.release()


def main() -> None:
    args = parse_args()
    output_path = args.output.resolve()
    codec = args.codec or infer_codec(output_path)
    validate_args(args, codec)
    generate_video(
        output_path=output_path,
        size=args.size,
        duration_seconds=args.duration_seconds,
        fps=args.fps,
        codec=codec,
    )
    print(
        "Generated video fixture "
        f"{output_path} ({args.size[0]}x{args.size[1]}, {args.duration_seconds:.2f}s, {args.fps}fps, codec={codec})"
    )


if __name__ == "__main__":
    main()
