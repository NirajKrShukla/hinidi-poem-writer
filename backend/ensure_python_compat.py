"""
Simple preinstall check to ensure a compatible Python version is used for installing
backend dependencies. This repository expects Python 3.11 for development so prebuilt
wheels for binary packages like pydantic-core are available.

Usage: python backend/ensure_python_compat.py
Exits with code 0 if compatible, otherwise prints a helpful message and exits 1.
"""
import sys

REQUIRED_MAJOR = 3
REQUIRED_MINOR = 11

def main():
    v = sys.version_info
    if (v.major, v.minor) != (REQUIRED_MAJOR, REQUIRED_MINOR):
        print(
            f"ERROR: Unsupported Python version {v.major}.{v.minor}.\n"
            f"This project requires Python {REQUIRED_MAJOR}.{REQUIRED_MINOR} for local development.\n"
            "Prebuilt wheels (pydantic-core) are not available for newer Python versions and building\n"
            "from source requires Rust and the MSVC toolchain on Windows.\n\n"
            "Options:\n"
            f"  1) Install Python {REQUIRED_MAJOR}.{REQUIRED_MINOR} and re-run in a virtualenv.\n"
            "  2) Install Rust (rustup) and Visual C++ Build Tools (Windows) then retry (advanced).\n"
        )
        sys.exit(1)
    print(f"Python {v.major}.{v.minor} OK")

if __name__ == '__main__':
    main()
