# pdf-mcp-tesseract

Static [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) builds for
[pdf-mcp](https://github.com/jztan/pdf-mcp)'s zero-install OCR fallback:
Windows x64, macOS Apple Silicon and macOS Intel, one zip per platform.

This repo holds no Tesseract source. It pins a
[vcpkg](https://github.com/microsoft/vcpkg) commit, builds upstream Tesseract
unmodified as a single static `tesseract.exe`, and packages it with
`eng.traineddata` and the licence notices of everything linked in. A
Tesseract you installed yourself always takes precedence in pdf-mcp.

## Status

All three builds pass every check below. A release is cut git-flow style:
a release branch merges into `master`, which is tagged
`tesseract-<tesseract version>-pdfmcp<n>`. The tag runs `release.yml`, which
rebuilds all three zips with every check, compares their hashes, attests
their build provenance and publishes them. pdf-mcp pins each zip's SHA-256.
Running `release.yml` by hand is a dry run that publishes nothing.

To release, from a clean `develop` whose builds are green:

```
python3 scripts/release.py --dry-run   # the plan, nothing changed
python3 scripts/release.py             # asks, then releases
```

It picks the next tag, checks everything before changing anything, rolls
back on any failure, and pushes `master`, `develop` and the tag in one
atomic push.

## What the workflows check

`build-windows.yml` and `build-macos.yml` run on every branch push and again
inside each release.

1. **Build:** `vcpkg install tesseract` at the pinned vcpkg commit, static
   and release only (`x64-windows-static-release` with the static CRT;
   `arm64-osx-release` and `x64-osx-release` for macOS 12 and later), using
   the overlay in `ports/tesseract`: the stock port built without curl and
   libarchive, which pdf-mcp never reaches (it hands Tesseract image files).
2. **Self-contained:** on Windows `dumpbin /dependents` must list only
   system DLLs, with the Visual C++ runtime rejected by name; on macOS
   `otool -L` must list only `/usr/lib` and `/System` libraries, and the
   binary is ad-hoc signed and verified with `codesign`.
3. **Smoke:** `--version` and `--list-langs` with a bare `PATH` and no
   `TESSDATA_PREFIX`, so the `tessdata` folder beside the binary must be
   found on its own.
4. **pdf-mcp OCR tests:** pdf-mcp's OCR tests run with this binary on `PATH`
   and fail if any of them skips instead of running.
5. **Parity:** the same pages OCRed by this binary and by a reference build
   (UB Mannheim on Windows, Homebrew on macOS), on the same traineddata:
   word-set Jaccard and wall-clock ratio.
6. **Defender (Windows):** Microsoft Defender, with freshly updated
   signatures, scans the unpacked package and the zip; any detection fails
   the build.

## Licences

The build scripts in this repo are MIT. The packaged binary is Tesseract
(Apache-2.0) statically linked with Leptonica (BSD-2-Clause) and its image
and compression libraries. Each zip carries `THIRD-PARTY-NOTICES.md` (every
linked library, its version and licence, and the attribution the IJG licence
requires) and the full licence texts under `licenses/`; `eng.traineddata` is
Apache-2.0 from [tesseract-ocr/tessdata](https://github.com/tesseract-ocr/tessdata).
The build fails if a linked library has no licence text or a licence that
`scripts/third_party_notices.py` has not been reviewed for.
