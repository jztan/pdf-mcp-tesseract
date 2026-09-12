# Static libraries, release only, for a self-contained macOS tesseract that
# links nothing outside /usr/lib and /System. Targets macOS 12 and later.
set(VCPKG_TARGET_ARCHITECTURE x64)
set(VCPKG_CRT_LINKAGE dynamic)
set(VCPKG_LIBRARY_LINKAGE static)
set(VCPKG_CMAKE_SYSTEM_NAME Darwin)
set(VCPKG_OSX_ARCHITECTURES x86_64)
set(VCPKG_OSX_DEPLOYMENT_TARGET "12.0")
set(VCPKG_BUILD_TYPE release)
