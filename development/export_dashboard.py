"""Export the dashboard for any static host, preserving marimo's relative CSS.

Run from the repository root: ``uv run python development/export_dashboard.py``.
Writes outputs/dashboard_site/ and outputs/dashboard_site.zip. The generated
site requires HTTP(S) and an internet connection for its WebAssembly runtime.
"""

from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    """Export from the app directory and validate required bundled assets."""
    destination = ROOT / "outputs/dashboard_site"
    # marimo 0.23.2's WASM exporter resolves CSS against a basename. Running
    # beside the notebook preserves normal portable css_file configuration.
    subprocess.run([
        sys.executable, "-m", "marimo", "export", "html-wasm", "app.py",
        "-o", str(destination), "--mode", "run", "--no-show-code", "--force",
    ], cwd=ROOT / "development/dashboard", check=True)
    content = (destination / "index.html").read_text()
    if ".atlas-metrics" not in content:
        raise ValueError("The static export is missing its custom stylesheet.")
    original = ROOT / "development/dashboard/public/sample.json"
    if (destination / "public/sample.json").read_bytes() != original.read_bytes():
        raise ValueError("The static export does not contain the current sample.")
    archive = shutil.make_archive(str(destination), "zip", destination)
    print(f"Portable site: {destination}")
    print(f"Upload bundle: {archive}")


if __name__ == "__main__":
    main()
