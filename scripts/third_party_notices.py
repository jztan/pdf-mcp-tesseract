"""Write THIRD-PARTY-NOTICES.md into a packaged build, and fail if any
statically linked library lacks its licence text or a known licence.

Usage: python third_party_notices.py <package dir>

The package dir holds PORTS.txt (`vcpkg list` output) and licenses/<port>.txt
(each port's copyright file). A new dependency with no entry below stops the
build instead of shipping unreviewed.
"""

import re
import sys
from pathlib import Path

# Build-time helpers; nothing of theirs is linked into the binary.
HELPERS = {
    "vcpkg-cmake",
    "vcpkg-cmake-config",
    "vcpkg-cmake-get-vars",
    "vcpkg-pkgconfig-get-modules",
}

# Reviewed 2026-09-12 against each port's copyright file in the package.
LICENSES = {
    "tesseract": "Apache-2.0",
    "leptonica": "BSD-2-Clause (Leptonica licence)",
    "giflib": "MIT",
    "libjpeg-turbo": "IJG, BSD-3-Clause and Zlib",
    "liblzma": "0BSD (XZ Utils)",
    "libpng": "libpng-2.0",
    "libwebp": "BSD-3-Clause",
    "openjpeg": "BSD-2-Clause",
    "tiff": "libtiff",
    "zlib": "Zlib",
}

# The IJG licence requires this statement in the documentation of any
# distribution that ships only executable code.
IJG = "This software is based in part on the work of the Independent JPEG Group."


def ports(pkg: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in (pkg / "PORTS.txt").read_text(encoding="utf-8-sig").splitlines():
        m = re.match(r"^([a-z0-9-]+)(?:\[[^\]]*\])?:\S+\s+(\S+)", line.strip())
        if m:
            found.setdefault(m.group(1), m.group(2))
    return found


def main(pkg_dir: str) -> int:
    pkg = Path(pkg_dir)
    linked = {n: v for n, v in ports(pkg).items() if n not in HELPERS}
    missing = [n for n in linked if not (pkg / "licenses" / f"{n}.txt").exists()]
    unknown = [n for n in linked if n not in LICENSES]
    if not (pkg / "licenses" / "tessdata.txt").exists():
        missing.append("tessdata")
    if missing or unknown:
        print(f"licence text missing for: {missing}; unreviewed licence: {unknown}")
        return 1

    rows = [
        f"| {n} | {v.split('#')[0]} | {LICENSES[n]} | `licenses/{n}.txt` |"
        for n, v in sorted(linked.items())
    ]
    text = "\n".join(
        [
            "# Third-party notices",
            "",
            "This package contains the Tesseract OCR engine, built from unmodified",
            "upstream source by https://github.com/jztan/pdf-mcp-tesseract and",
            "statically linked with the libraries below. The full licence text of",
            "each is in the `licenses` folder.",
            "",
            "| component | version | licence | text |",
            "|---|---|---|---|",
            *rows,
            "| tessdata (eng.traineddata) | 4.1.0 | Apache-2.0 | `licenses/tessdata.txt` |",
            "",
            IJG,
            "",
        ]
    )
    (pkg / "THIRD-PARTY-NOTICES.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
