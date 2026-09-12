# pdf-mcp-tesseract

Static [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) builds for
[pdf-mcp](https://github.com/jztan/pdf-mcp)'s zero-install OCR fallback.

This repo holds no Tesseract source. It pins a
[vcpkg](https://github.com/microsoft/vcpkg) commit, builds upstream Tesseract
unmodified as a single static `tesseract.exe`, and packages it with
`eng.traineddata` and the licence notices of everything linked in. A
Tesseract you installed yourself always takes precedence in pdf-mcp.

## Status

Spike. The Windows build workflow answers one question before anything
ships: does the static build compile, run with no DLLs beside it, pass
pdf-mcp's OCR tests, and read the same words as the official Windows build?
No release has been published yet.

## What the workflow checks

1. **Build:** `vcpkg install tesseract:x64-windows-static-release` at the
   pinned vcpkg commit (static libraries, static CRT, release only).
2. **Self-contained:** `dumpbin /dependents` must list only Windows system
   DLLs, with the Visual C++ runtime rejected by name.
3. **Smoke:** `--version` and `--list-langs` with a bare `PATH` and no
   `TESSDATA_PREFIX`, so `tessdata\` beside the exe must be found on its own.
4. **pdf-mcp OCR tests:** pdf-mcp's OCR tests run with this exe on `PATH`
   and fail if any of them skips instead of running.
5. **Parity:** the same pages OCRed by this exe and by the UB Mannheim build,
   on the same traineddata: word-set Jaccard and wall-clock ratio.

## Licences

The build scripts in this repo are MIT. The packaged binary is Tesseract
(Apache-2.0) statically linked with Leptonica (BSD-2-Clause) and its image
and compression libraries; every notice ships in the zip under `licenses/`,
and `eng.traineddata` is Apache-2.0 from
[tesseract-ocr/tessdata](https://github.com/tesseract-ocr/tessdata).
