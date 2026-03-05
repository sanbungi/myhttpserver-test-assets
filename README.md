# myhttpserver-test-assets

HTTP server behavior checks for static assets.

## Interactive runner

Run the generators from a single interactive menu with:

```bash
uv run python main.py
```

## Image fixtures

Generate the image fixtures with:

```bash
uv sync
uv run python scripts/generate_test_images.py
```

The script writes eight test assets to `html/images/` and will also emit an optional AVIF file when the local Pillow build supports it.

## Video fixtures

Generate a simple rights-safe animation fixture with:

```bash
uv sync
uv run python scripts/generate_test_video.py --size 1280x720 --duration-seconds 5
```

The script writes a browser-friendly WebM file to `html/videos/` by default. You can override the resolution with `--size WIDTHxHEIGHT`, the length with `--duration-seconds`, the frame rate with `--fps`, and the container path with `--output`. Each frame includes its current frame number as on-screen text. If you want another container, the script infers a default codec from the extension, for example `.webm -> VP90` and `.mp4 -> mp4v`.

## Large ZIP fixtures

Generate large ZIP response fixtures with:

```bash
uv run python scripts/generate_test_zip_files.py
```

The script writes `test10mb.zip`, `test100mb.zip`, and `test1000mb.zip` to `html/`.
Each archive contains a single random-data member and is streamed in chunks, so it can generate the 1000MB fixture without holding the payload in memory.

## PDF fixtures

Generate a deterministic PDF test fixture with:

```bash
uv run python scripts/generate_test_pdf.py
```

The script writes `test-document.pdf` to `html/` by default. You can override the destination with `--output`, change the visible title with `--title`, change the page count with `--pages`, and use `--force` to overwrite an existing file.
