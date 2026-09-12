"""Fail unless pdf-mcp's OCR tests actually ran against a Tesseract.

pdf-mcp's OCR tests skip themselves when no `tesseract` is on PATH, so a
green pytest run can mean nothing was tested. This reads the JUnit XML
and fails on any Tesseract-related skip, or when nothing passed.

Usage: python assert_ocr_ran.py results.xml
"""

import sys
import xml.etree.ElementTree as ET


def main(path: str) -> int:
    passed, bad_skips, failed = [], [], []
    for case in ET.parse(path).getroot().iter("testcase"):
        name = f"{case.get('classname')}::{case.get('name')}"
        skipped = case.find("skipped")
        if case.find("failure") is not None or case.find("error") is not None:
            failed.append(name)
        elif skipped is not None:
            # The message attribute only: the element text carries the test
            # file path, and this repo's checkout path contains "tesseract".
            reason = skipped.get("message") or ""
            if "tesseract not installed" in reason.lower():
                bad_skips.append(f"{name}: {reason.strip()}")
            else:
                print(f"skipped (unrelated): {name}: {reason.strip()}")
        else:
            passed.append(name)

    print(f"passed {len(passed)}, failed {len(failed)}, "
          f"tesseract skips {len(bad_skips)}")
    for name in passed:
        print(f"  ok  {name}")
    for line in bad_skips:
        print(f"  SKIP  {line}")
    for name in failed:
        print(f"  FAIL  {name}")
    if bad_skips or failed or not passed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
