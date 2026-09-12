# Static libraries and a static CRT, so tesseract.exe needs no Visual C++
# redistributable and no DLLs beside it. Release only: the debug half of a
# stock static triplet doubles build time and is never shipped.
set(VCPKG_TARGET_ARCHITECTURE x64)
set(VCPKG_CRT_LINKAGE static)
set(VCPKG_LIBRARY_LINKAGE static)
set(VCPKG_BUILD_TYPE release)
