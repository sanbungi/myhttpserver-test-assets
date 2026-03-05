from __future__ import annotations

import colorsys
import math
import random
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont, features


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "html" / "images"
EXIF_ORIENTATION_TAG = 274


def lerp_color(start: tuple[int, int, int], end: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(
        int(round(channel_start + (channel_end - channel_start) * t))
        for channel_start, channel_end in zip(start, end, strict=True)
    )


def palette_from_seed(seed: int, count: int, *, saturation: float = 0.72, value: float = 0.95) -> list[tuple[int, int, int]]:
    rng = random.Random(seed)
    base_hue = rng.random()
    palette: list[tuple[int, int, int]] = []
    for index in range(count):
        hue = (base_hue + index / count + rng.uniform(-0.035, 0.035)) % 1.0
        red, green, blue = colorsys.hsv_to_rgb(hue, saturation, value)
        palette.append((int(red * 255), int(green * 255), int(blue * 255)))
    return palette


def draw_gradient_background(image: Image.Image, top_color: tuple[int, int, int], bottom_color: tuple[int, int, int]) -> None:
    width, height = image.size
    drawer = ImageDraw.Draw(image)
    for y in range(height):
        t = y / max(height - 1, 1)
        drawer.line((0, y, width, y), fill=lerp_color(top_color, bottom_color, t))


def regular_polygon(cx: float, cy: float, radius: float, sides: int, rotation: float) -> list[tuple[float, float]]:
    return [
        (
            cx + math.cos(rotation + (math.tau * step / sides)) * radius,
            cy + math.sin(rotation + (math.tau * step / sides)) * radius,
        )
        for step in range(sides)
    ]


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


def add_label(image: Image.Image, title: str, subtitle: str | None = None) -> Image.Image:
    labeled = image.convert("RGBA")
    drawer = ImageDraw.Draw(labeled, "RGBA")
    width, height = labeled.size

    title_font = load_font(max(18, min(width, height) // 14))
    subtitle_font = load_font(max(14, min(width, height) // 28))

    title_box = drawer.textbbox((0, 0), title, font=title_font)
    subtitle_text = subtitle or ""
    subtitle_box = drawer.textbbox((0, 0), subtitle_text, font=subtitle_font) if subtitle_text else None

    padding_x = max(14, width // 40)
    padding_y = max(12, height // 40)
    box_width = (title_box[2] - title_box[0]) + padding_x * 2
    if subtitle_box is not None:
        box_width = max(box_width, (subtitle_box[2] - subtitle_box[0]) + padding_x * 2)

    box_height = (title_box[3] - title_box[1]) + padding_y * 2
    if subtitle_box is not None:
        box_height += (subtitle_box[3] - subtitle_box[1]) + max(8, padding_y // 2)

    x1 = max(10, width // 24)
    y1 = max(10, height // 24)
    x2 = min(width - x1, x1 + box_width)
    y2 = min(height - y1, y1 + box_height)

    drawer.rounded_rectangle((x1, y1, x2, y2), radius=max(10, min(width, height) // 40), fill=(12, 18, 30, 180), outline=(255, 255, 255, 160), width=max(1, min(width, height) // 500))
    drawer.text((x1 + padding_x, y1 + padding_y), title, font=title_font, fill=(255, 255, 255, 235))

    if subtitle_box is not None:
        subtitle_y = y1 + padding_y + (title_box[3] - title_box[1]) + max(6, padding_y // 3)
        drawer.text((x1 + padding_x, subtitle_y), subtitle_text, font=subtitle_font, fill=(232, 240, 255, 210))

    return labeled if image.mode == "RGBA" else labeled.convert("RGB")


def create_geometric_art(
    size: tuple[int, int],
    *,
    seed: int,
    title: str,
    subtitle: str | None = None,
    transparent: bool = False,
    overlay_alpha: int = 210,
) -> Image.Image:
    width, height = size
    mode = "RGBA" if transparent else "RGB"
    background = (0, 0, 0, 0) if transparent else (255, 255, 255)
    image = Image.new(mode, size, background)

    palette = palette_from_seed(seed, 8)
    if not transparent:
        draw_gradient_background(image, palette[0], palette[3])

    rng = random.Random(seed)
    shapes = max(18, min(64, (width * height) // 120_000))
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    drawer = ImageDraw.Draw(layer, "RGBA")
    stroke_color = palette[-1] + (110,)

    for index in range(shapes):
        color = palette[index % len(palette)]
        alpha = max(60, min(overlay_alpha, int(overlay_alpha * (0.55 + 0.45 * rng.random()))))
        shape_type = index % 4

        if shape_type == 0:
            x1 = rng.uniform(0, width * 0.72)
            y1 = rng.uniform(0, height * 0.72)
            x2 = x1 + rng.uniform(width * 0.08, width * 0.32)
            y2 = y1 + rng.uniform(height * 0.08, height * 0.32)
            drawer.rounded_rectangle((x1, y1, x2, y2), radius=max(width, height) * 0.02, fill=color + (alpha,), outline=stroke_color, width=max(1, width // 500))
        elif shape_type == 1:
            radius = rng.uniform(min(width, height) * 0.04, min(width, height) * 0.18)
            cx = rng.uniform(radius, width - radius)
            cy = rng.uniform(radius, height - radius)
            drawer.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=color + (alpha,), outline=stroke_color, width=max(1, width // 500))
        elif shape_type == 2:
            radius = rng.uniform(min(width, height) * 0.05, min(width, height) * 0.16)
            points = regular_polygon(
                rng.uniform(radius, width - radius),
                rng.uniform(radius, height - radius),
                radius,
                rng.randint(3, 8),
                rng.uniform(0, math.tau),
            )
            drawer.polygon(points, fill=color + (alpha,), outline=stroke_color)
        else:
            band_height = rng.uniform(height * 0.035, height * 0.08)
            y = rng.uniform(-band_height, height)
            drawer.polygon(
                [
                    (0, y),
                    (width, y + rng.uniform(-height * 0.05, height * 0.05)),
                    (width, y + band_height),
                    (0, y + band_height + rng.uniform(-height * 0.05, height * 0.05)),
                ],
                fill=color + (alpha,),
            )

    for line_index in range(6):
        y = (line_index + 1) * height / 7
        drawer.line((0, y, width, y + rng.uniform(-height * 0.06, height * 0.06)), fill=palette[line_index % len(palette)] + (90,), width=max(2, width // 240))

    combined = Image.alpha_composite(image.convert("RGBA"), layer)
    return add_label(combined if transparent else combined.convert("RGB"), title, subtitle)


def save_jpeg(path: Path, image: Image.Image, *, quality: int, progressive: bool = True, exif: Image.Exif | None = None) -> None:
    kwargs = {"quality": quality, "progressive": progressive, "optimize": True}
    if exif is not None:
        kwargs["exif"] = exif
    image.convert("RGB").save(path, format="JPEG", **kwargs)


def save_png(path: Path, image: Image.Image) -> None:
    image.save(path, format="PNG", optimize=True)


def save_webp(path: Path, image: Image.Image) -> None:
    image.save(path, format="WEBP", quality=90, method=6)


def try_save_avif(path: Path, image: Image.Image) -> bool:
    if not features.check("avif"):
        return False
    image.save(path, format="AVIF", quality=82, speed=6)
    return True


def write_svg(path: Path, width: int, height: int, palette: Iterable[tuple[int, int, int]]) -> None:
    colors = [f"rgb({red},{green},{blue})" for red, green, blue in palette]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Geometric gradient test asset">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{colors[0]}"/>
      <stop offset="100%" stop-color="{colors[3]}"/>
    </linearGradient>
  </defs>
  <rect width="{width}" height="{height}" fill="url(#bg)"/>
  <circle cx="{width * 0.22:.1f}" cy="{height * 0.3:.1f}" r="{min(width, height) * 0.14:.1f}" fill="{colors[1]}" fill-opacity="0.72"/>
  <circle cx="{width * 0.72:.1f}" cy="{height * 0.24:.1f}" r="{min(width, height) * 0.12:.1f}" fill="{colors[2]}" fill-opacity="0.62"/>
  <polygon points="{width * 0.5:.1f},{height * 0.12:.1f} {width * 0.86:.1f},{height * 0.48:.1f} {width * 0.6:.1f},{height * 0.9:.1f} {width * 0.18:.1f},{height * 0.72:.1f}" fill="{colors[4]}" fill-opacity="0.7"/>
  <rect x="{width * 0.08:.1f}" y="{height * 0.72:.1f}" width="{width * 0.84:.1f}" height="{height * 0.1:.1f}" rx="{width * 0.025:.1f}" fill="{colors[5]}" fill-opacity="0.68"/>
  <path d="M0,{height * 0.56:.1f} C{width * 0.24:.1f},{height * 0.38:.1f} {width * 0.48:.1f},{height * 0.8:.1f} {width:.1f},{height * 0.56:.1f} L{width:.1f},{height:.1f} L0,{height:.1f} Z" fill="{colors[6]}" fill-opacity="0.42"/>
  <rect x="{width * 0.06:.1f}" y="{height * 0.07:.1f}" width="{width * 0.38:.1f}" height="{height * 0.16:.1f}" rx="{width * 0.018:.1f}" fill="rgb(12,18,30)" fill-opacity="0.72"/>
  <text x="{width * 0.09:.1f}" y="{height * 0.15:.1f}" fill="white" font-family="DejaVu Sans, Arial, sans-serif" font-size="{width * 0.035:.1f}" font-weight="700">SVG test</text>
  <text x="{width * 0.09:.1f}" y="{height * 0.205:.1f}" fill="rgb(232,240,255)" font-family="DejaVu Sans, Arial, sans-serif" font-size="{width * 0.018:.1f}">content-type / CSP / XSS check</text>
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    small = create_geometric_art((320, 240), seed=11, title="Small JPEG test", subtitle="basic image rendering")
    save_jpeg(OUTPUT_DIR / "small-basic-320x240.jpg", small, quality=88)

    large = create_geometric_art((4096, 3072), seed=22, title="Big image test", subtitle="bandwidth / compression")
    save_jpeg(OUTPUT_DIR / "large-bandwidth-4096x3072.jpg", large, quality=92)

    transparent = create_geometric_art((1400, 1400), seed=33, title="PNG alpha test", subtitle="transparent overlay", transparent=True, overlay_alpha=180)
    save_png(OUTPUT_DIR / "transparent-alpha-overlay.png", transparent)

    write_svg(OUTPUT_DIR / "vector-safe-geometric.svg", 1200, 900, palette_from_seed(44, 8))

    webp = create_geometric_art((1600, 900), seed=55, title="WebP / AVIF test", subtitle="modern image formats")
    save_webp(OUTPUT_DIR / "modern-format-geometric.webp", webp)
    try_save_avif(OUTPUT_DIR / "modern-format-geometric.avif", webp)

    portrait = create_geometric_art((900, 1600), seed=66, title="Portrait image test", subtitle="object-fit / thumbnails")
    save_jpeg(OUTPUT_DIR / "portrait-900x1600.jpg", portrait, quality=90)

    square = create_geometric_art((1200, 1200), seed=77, title="Square image test", subtitle="cropping behavior")
    save_jpeg(OUTPUT_DIR / "square-1200x1200.jpg", square, quality=90)

    exif_oriented = create_geometric_art((1600, 900), seed=88, title="EXIF orientation test", subtitle="filename encoding too")
    exif = Image.Exif()
    exif[EXIF_ORIENTATION_TAG] = 6
    save_jpeg(OUTPUT_DIR / "日本語 スペース exif-orientation.jpg", exif_oriented, quality=89, exif=exif)

    print(f"Generated image fixtures in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
