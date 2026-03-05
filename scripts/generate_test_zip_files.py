from __future__ import annotations

import argparse
import random
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "html"
DEFAULT_SIZES_MB = (10, 100, 1000)
BYTES_PER_MB = 1_000_000
DEFAULT_CHUNK_SIZE = 4 * 1024 * 1024
PROGRESS_INTERVAL = 64 * 1024 * 1024
ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate large ZIP fixtures backed by random payload data."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory where the ZIP files are written. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--sizes-mb",
        nargs="+",
        type=int,
        default=list(DEFAULT_SIZES_MB),
        help="Payload sizes to generate in decimal megabytes. Default: 10 100 1000",
    )
    parser.add_argument(
        "--chunk-size-mb",
        type=int,
        default=DEFAULT_CHUNK_SIZE // (1024 * 1024),
        help="Chunk size used while streaming random data into the ZIP entry. Default: 4",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260305,
        help="Base seed for reproducible pseudo-random payloads.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing ZIP files.",
    )
    return parser.parse_args()


def build_zip_info(member_name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(filename=member_name, date_time=ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = 0o644 << 16
    return info


def generate_zip_archive(
    *,
    output_path: Path,
    payload_size_bytes: int,
    chunk_size_bytes: int,
    seed: int,
) -> None:
    rng = random.Random(seed)
    member_name = f"{output_path.stem}.bin"
    info = build_zip_info(member_name)

    written = 0
    next_progress = PROGRESS_INTERVAL

    with zipfile.ZipFile(output_path, mode="w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        with archive.open(info, mode="w", force_zip64=True) as member:
            while written < payload_size_bytes:
                remaining = payload_size_bytes - written
                chunk_length = min(chunk_size_bytes, remaining)
                member.write(rng.randbytes(chunk_length))
                written += chunk_length

                if written >= next_progress or written == payload_size_bytes:
                    print(f"  wrote {written / BYTES_PER_MB:.0f}MB / {payload_size_bytes / BYTES_PER_MB:.0f}MB")
                    next_progress += PROGRESS_INTERVAL


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    chunk_size_bytes = args.chunk_size_mb * 1024 * 1024

    if chunk_size_bytes <= 0:
        raise ValueError("--chunk-size-mb must be greater than zero")

    output_dir.mkdir(parents=True, exist_ok=True)

    sizes_mb = sorted(set(args.sizes_mb))
    invalid_sizes = [size for size in sizes_mb if size <= 0]
    if invalid_sizes:
        raise ValueError(f"--sizes-mb must contain positive integers: {invalid_sizes}")

    for size_mb in sizes_mb:
        output_path = output_dir / f"test{size_mb}mb.zip"
        if output_path.exists() and not args.force:
            print(f"skip {output_path.name}: already exists (use --force to overwrite)")
            continue

        payload_size_bytes = size_mb * BYTES_PER_MB
        print(f"generating {output_path.name} with {size_mb}MB random payload")
        generate_zip_archive(
            output_path=output_path,
            payload_size_bytes=payload_size_bytes,
            chunk_size_bytes=chunk_size_bytes,
            seed=args.seed + size_mb,
        )
        archive_size = output_path.stat().st_size
        print(f"done {output_path.name}: {archive_size / BYTES_PER_MB:.2f}MB on disk")


if __name__ == "__main__":
    main()
