"""Build a wheel and source archive with the compiled dashboard included.

Run with the project's Python environment: python scripts/build_release.py
Requires setuptools and wheel; Node/npm are needed only to build the frontend.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
subprocess.run(["npm", "run", "build", "--prefix", str(root / "frontend")], check=True)
release = root / "dist"
release.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="driftlab-release-") as directory:
    staging = Path(directory)
    shutil.copytree(root / "src", staging / "src", ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
    shutil.copytree(root / "frontend" / "dist", staging / "src" / "driftlab" / "api" / "static", dirs_exist_ok=True)
    for name in ("pyproject.toml", "README.md", "LICENSE"):
        shutil.copy2(root / name, staging / name)
    for name in ("docs", "examples"):
        shutil.copytree(root / name, staging / name)
    (staging / "MANIFEST.in").write_text("recursive-include src/driftlab/api/static *\nrecursive-include docs *\nrecursive-include examples *\n")
    subprocess.run([sys.executable, "-c", "from setuptools.build_meta import build_wheel, build_sdist; import sys; build_wheel(sys.argv[1]); build_sdist(sys.argv[1])", str(release)], cwd=staging, check=True)
print(f"Release artifacts: {release}")
