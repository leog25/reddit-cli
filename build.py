"""Local Nuitka build helper. Run: python build.py"""

import platform
import subprocess
import sys

COMMON_FLAGS = [
    sys.executable, "-m", "nuitka",
    "--mode=onefile",
    "--output-dir=dist",
    "--python-flag=no_site",
    # Dynamic / lazy imports that Nuitka can't detect statically
    "--include-module=browser_cookie3",
    "--include-module=rookiepy",
    "--include-module=yaml",
    "--include-module=rich.panel",
    "--include-module=rich.table",
    "--include-module=rich.console",
    "--include-module=annotated_types",
    "--include-module=typing_extensions",
    "--include-module=typing_inspection",
    # Full packages with C extensions
    "--include-package=Cryptodome",
    "--include-package=pydantic",
    "--include-package=pydantic_core",
    "--include-package=typer",
    "--include-package=click",
    "--include-package=httpx",
    "--include-package=httpcore",
    "--include-package=rich",
    "--include-package=lz4",
    # Exclude dev dependencies
    "--nofollow-import-to=pytest",
    "--nofollow-import-to=ruff",
    "--nofollow-import-to=_pytest",
    # Optimization
    "--lto=yes",
    "--assume-yes-for-downloads",
]

PLATFORM_FLAGS = {
    "Windows": ["--output-filename=reddit.exe", "--mingw64"],
    "Linux": ["--output-filename=reddit", "--include-module=jeepney"],
    "Darwin": ["--output-filename=reddit"],
}


def main():
    system = platform.system()
    flags = COMMON_FLAGS + PLATFORM_FLAGS.get(system, ["--output-filename=reddit"])
    flags.append("src/reddit_cli/main.py")

    print(f"Building for {system} ({platform.machine()})...")
    print(f"Command: {' '.join(flags)}\n")
    subprocess.run(flags, check=True)
    print(f"\nBinary written to dist/")


if __name__ == "__main__":
    main()
