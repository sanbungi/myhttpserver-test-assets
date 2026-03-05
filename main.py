from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from scripts import generate_test_images as image_generator
from scripts import generate_test_pdf as pdf_generator
from scripts import generate_test_video as video_generator
from scripts import generate_test_zip_files as zip_generator


REPO_ROOT = Path(__file__).resolve().parent


def prompt_text(label: str, default: str) -> str:
    while True:
        suffix = f" [{default}]" if default else " [empty]"
        value = input(f"{label}{suffix}: ").strip()
        if value:
            return value
        return default


def prompt_int(label: str, default: int) -> int:
    while True:
        value = prompt_text(label, str(default))
        try:
            return int(value)
        except ValueError:
            print("整数を入力してください。")


def prompt_float(label: str, default: float) -> float:
    while True:
        value = prompt_text(label, str(default))
        try:
            return float(value)
        except ValueError:
            print("数値を入力してください。")


def prompt_bool(label: str, default: bool) -> bool:
    default_hint = "Y/n" if default else "y/N"
    while True:
        value = input(f"{label} [{default_hint}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("y か n で入力してください。")


def prompt_path(label: str, default: Path) -> Path:
    value = prompt_text(label, str(default))
    return Path(value).expanduser().resolve()


def prompt_size(default: tuple[int, int]) -> tuple[int, int]:
    default_text = f"{default[0]}x{default[1]}"
    while True:
        value = prompt_text("解像度 WIDTHxHEIGHT", default_text)
        try:
            return video_generator.parse_size(value)
        except Exception as exc:
            print(f"入力エラー: {exc}")


def prompt_sizes_mb(defaults: tuple[int, ...]) -> list[int]:
    default_text = " ".join(str(size) for size in defaults)
    while True:
        value = prompt_text("ZIP サイズ(MB, 空白区切り)", default_text)
        tokens = value.replace(",", " ").split()
        try:
            sizes = sorted(set(int(token) for token in tokens))
        except ValueError:
            print("MB サイズは整数で入力してください。")
            continue

        if not sizes or any(size <= 0 for size in sizes):
            print("正の整数を 1 つ以上入力してください。")
            continue
        return sizes


def confirm_overwrite(path: Path) -> bool:
    if not path.exists():
        return True
    return prompt_bool(f"{path} は既に存在します。上書きしますか", False)


def run_images() -> None:
    print(f"\n画像を生成します: {image_generator.OUTPUT_DIR}")
    if not prompt_bool("生成を開始しますか", True):
        print("画像生成をスキップしました。")
        return

    image_generator.main()
    print(f"画像生成が完了しました: {image_generator.OUTPUT_DIR}")


def run_video() -> None:
    print("\n動画ジェネレータ")
    output_path = prompt_path("出力ファイル", video_generator.DEFAULT_OUTPUT_PATH)
    size = prompt_size(video_generator.DEFAULT_SIZE)
    duration_seconds = prompt_float("再生時間(秒)", video_generator.DEFAULT_DURATION_SECONDS)
    fps = prompt_int("FPS", video_generator.DEFAULT_FPS)
    codec_input = prompt_text("Codec(空欄で自動判定)", "")
    codec = codec_input or video_generator.infer_codec(output_path)
    video_generator.validate_args(
        SimpleNamespace(size=size, duration_seconds=duration_seconds, fps=fps),
        codec,
    )

    if not confirm_overwrite(output_path):
        print("動画生成をスキップしました。")
        return

    video_generator.generate_video(
        output_path=output_path,
        size=size,
        duration_seconds=duration_seconds,
        fps=fps,
        codec=codec,
    )
    print(
        "動画生成が完了しました: "
        f"{output_path} ({size[0]}x{size[1]}, {duration_seconds:.2f}s, {fps}fps, codec={codec})"
    )


def run_zip_files() -> None:
    print("\nZIP ジェネレータ")
    output_dir = prompt_path("出力ディレクトリ", zip_generator.DEFAULT_OUTPUT_DIR)
    sizes_mb = prompt_sizes_mb(zip_generator.DEFAULT_SIZES_MB)
    chunk_size_mb = prompt_int(
        "チャンクサイズ(MiB)",
        zip_generator.DEFAULT_CHUNK_SIZE // (1024 * 1024),
    )
    seed = prompt_int("乱数シード", 20260305)
    force = prompt_bool("既存 ZIP を上書きしますか", False)

    chunk_size_bytes = chunk_size_mb * 1024 * 1024
    if chunk_size_bytes <= 0:
        raise ValueError("チャンクサイズは 1 以上で指定してください。")

    output_dir.mkdir(parents=True, exist_ok=True)

    for size_mb in sizes_mb:
        output_path = output_dir / f"test{size_mb}mb.zip"
        if output_path.exists() and not force:
            print(f"skip {output_path.name}: already exists (use overwrite to replace)")
            continue

        print(f"generating {output_path.name} with {size_mb}MB random payload")
        zip_generator.generate_zip_archive(
            output_path=output_path,
            payload_size_bytes=size_mb * zip_generator.BYTES_PER_MB,
            chunk_size_bytes=chunk_size_bytes,
            seed=seed + size_mb,
        )
        archive_size = output_path.stat().st_size
        print(f"done {output_path.name}: {archive_size / zip_generator.BYTES_PER_MB:.2f}MB on disk")


def run_pdf() -> None:
    print("\nPDF ジェネレータ")
    output_path = prompt_path("出力ファイル", pdf_generator.DEFAULT_OUTPUT_PATH)
    title = prompt_text("タイトル", pdf_generator.DEFAULT_TITLE)
    pages = prompt_int("ページ数", pdf_generator.DEFAULT_PAGES)
    force = prompt_bool("既存 PDF を上書きしますか", False)

    if output_path.exists() and not force:
        print(f"skip {output_path.name}: already exists (use overwrite to replace)")
        return

    pdf_bytes = pdf_generator.build_pdf(title, pages)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pdf_bytes)
    print(f"wrote {output_path} ({len(pdf_bytes)} bytes, {pages} pages)")


def run_all() -> None:
    run_images()
    run_video()
    run_zip_files()
    run_pdf()


def print_menu() -> None:
    print("\n=== Fixture Generator Menu ===")
    print("1. 画像を生成")
    print("2. 動画を生成")
    print("3. ZIP を生成")
    print("4. PDF を生成")
    print("5. すべて実行")
    print("q. 終了")


def main() -> None:
    actions = {
        "1": run_images,
        "2": run_video,
        "3": run_zip_files,
        "4": run_pdf,
        "5": run_all,
    }

    print(f"作業ディレクトリ: {REPO_ROOT}")
    while True:
        print_menu()
        choice = input("選択してください: ").strip().lower()

        if choice in {"q", "quit", "exit"}:
            print("終了します。")
            return

        action = actions.get(choice)
        if action is None:
            print("無効な選択です。")
            continue

        try:
            action()
        except KeyboardInterrupt:
            print("\n入力を中断しました。メニューに戻ります。")
        except Exception as exc:
            print(f"実行に失敗しました: {exc}")

        if not prompt_bool("続けて別のジェネレータを実行しますか", True):
            print("終了します。")
            return


if __name__ == "__main__":
    main()
