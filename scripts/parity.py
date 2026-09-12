# /// script
# requires-python = ">=3.10"
# dependencies = ["pypdfium2==5.13.0", "pillow==12.3.0"]
# ///
"""Compare our static tesseract.exe against a reference build.

Both binaries read the SAME traineddata, so any word difference comes
from the build, not the model. Pages are rendered once (grayscale, like
pdf-mcp does) and fed to each binary as PNG. Timing is wall clock per
page with OMP_THREAD_LIMIT=1, so a build that lost its SIMD paths shows
up as a ratio well above 1.

Usage:
  uv run parity.py --pdf gao-cloud.pdf --pages 3,4,5 \
      --ours C:/x/tesseract.exe --ref "C:/Program Files/Tesseract-OCR/tesseract.exe" \
      --tessdata C:/x/tessdata
"""

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pypdfium2 as pdfium

MIN_JACCARD = 0.97
MAX_TIME_RATIO = 2.0


def render(pdf: str, pages: list[int], dpi: int, out: Path) -> list[Path]:
    doc = pdfium.PdfDocument(pdf)
    paths = []
    for p in pages:
        image = doc[p - 1].render(scale=dpi / 72, grayscale=True).to_pil()
        path = out / f"p{p}.png"
        image.save(path)
        paths.append(path)
    doc.close()
    return paths


def ocr(exe: str, image: Path, tessdata: str) -> tuple[str, float]:
    env = dict(os.environ, OMP_THREAD_LIMIT="1")
    env.pop("TESSDATA_PREFIX", None)
    cmd = [exe, str(image), "stdout", "-l", "eng", "--tessdata-dir", tessdata]
    start = time.perf_counter()
    done = subprocess.run(cmd, capture_output=True, text=True, env=env, check=True)
    return done.stdout, time.perf_counter() - start


def words(text: str) -> set[str]:
    return {w.lower() for w in text.split() if len(w) > 3}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--ours", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--tessdata", required=True)
    ap.add_argument("--dpi", type=int, default=300)
    args = ap.parse_args()

    for exe in (args.ours, args.ref):
        version = subprocess.run([exe, "--version"], capture_output=True, text=True)
        print(f"{exe}: {(version.stdout or version.stderr).splitlines()[0]}")

    pages = [int(p) for p in args.pages.split(",")]
    rows, failed = [], False
    with tempfile.TemporaryDirectory() as tmp:
        for page, image in zip(pages, render(args.pdf, pages, args.dpi, Path(tmp))):
            ocr(args.ours, image, args.tessdata)  # warm the file cache
            ours_text, ours_s = ocr(args.ours, image, args.tessdata)
            ref_text, ref_s = ocr(args.ref, image, args.tessdata)
            a, b = words(ours_text), words(ref_text)
            jaccard = len(a & b) / len(a | b) if a | b else 0.0
            ratio = ours_s / ref_s
            ok = jaccard >= MIN_JACCARD and ratio <= MAX_TIME_RATIO and len(b) > 50
            failed |= not ok
            rows.append((page, len(a), len(b), jaccard, ours_s, ref_s, ratio, ok))

    lines = [
        "| page | words ours | words ref | jaccard | ours s | ref s | ratio | ok |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for page, na, nb, j, os_, rs, r, ok in rows:
        lines.append(
            f"| {page} | {na} | {nb} | {j:.3f} | {os_:.2f} | {rs:.2f} "
            f"| {r:.2f} | {'yes' if ok else 'NO'} |"
        )
    lines.append(
        f"\nGate: jaccard >= {MIN_JACCARD}, time ratio <= {MAX_TIME_RATIO}, "
        "ref words > 50."
    )
    report = "\n".join(lines)
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## Parity vs reference build\n\n" + report + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
