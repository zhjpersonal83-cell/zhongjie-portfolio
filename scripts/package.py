#!/usr/bin/env python3
"""Create a checked static/Tomcat delivery ZIP using the Python standard library.

Run build.py first. This command makes no network requests and performs no deployment.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DATE = "2026-10-19"
ARCHIVE_TIMESTAMP = (2026, 10, 19, 0, 0, 0)
DEFAULT_OUTPUT = ROOT.parent / "zhongjie-portfolio.zip"
TOP_DIRECTORIES = {"content", "sources", "src", "static", "scripts", "docs", "site", "deploy"}
TOP_FILES = {"README.md", "build.py", "requirements-optional.txt", "VERSION.txt", "LICENSE", "LICENSE.txt", "LICENSE.md"}
EXCLUDED_PARTS = {".git", ".agents", ".codex", ".aws", ".ssh", "__MACOSX", ".DS_Store", "__pycache__", ".pytest_cache", ".cache", "node_modules", "venv", ".venv", "qa", "QA", "screenshots", "tmp", "temp"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp", ".bak", ".swp", ".zip"}
PRIVATE_NAMES = {".env", "id_rsa", "id_ed25519", "credentials.json", "credentials.yaml", "credentials.yml", "secrets.json", "secrets.yaml", "secrets.yml"}
MANIFEST_PATH = Path("docs/BUILD_MANIFEST.json")


def contained(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def archive_bytes(destination: Path, members: list[tuple[str, bytes]]) -> None:
    """Write sorted, normalized entries so unchanged inputs produce identical bytes."""
    with ZipFile(destination, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(members):
            pure = PurePosixPath(name)
            if name.startswith(("/", "\\")) or ".." in pure.parts or "\\" in name:
                raise ValueError("Unsafe archive member path")
            info = ZipInfo(name, date_time=ARCHIVE_TIMESTAMP)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, data, compress_type=ZIP_DEFLATED, compresslevel=9)


def site_members(site: Path) -> list[tuple[str, bytes]]:
    result = []
    for path in sorted(site.rglob("*")):
        if path.is_symlink() or not contained(path, site):
            raise ValueError("Generated site must not contain symlinks or escaping paths")
        if path.is_file():
            result.append((path.relative_to(site).as_posix(), path.read_bytes()))
    if not result or not (site / "index.html").is_file():
        raise ValueError("No built site found. Run python3 build.py first.")
    if not (site / "WEB-INF/web.xml").is_file():
        raise ValueError("Build must include site/WEB-INF/web.xml before packaging.")
    return result


def create_deployment(site: Path) -> None:
    members = site_members(site)
    deploy = ROOT / "deploy"
    deploy.mkdir(parents=True, exist_ok=True)
    target = deploy / "ROOT"
    if target.is_symlink():
        raise ValueError("Refusing to replace a symlink at deploy/ROOT")
    with tempfile.TemporaryDirectory(prefix=".package-", dir=deploy) as working:
        staging = Path(working)
        exploded = staging / "ROOT"
        exploded.mkdir()
        for name, data in members:
            path = exploded / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        archive_bytes(staging / "ROOT.war", members)
        # Only the generated local deployment copy is replaced; no server is contacted.
        if target.exists():
            shutil.rmtree(target)
        exploded.replace(target)
        (staging / "ROOT.war").replace(deploy / "ROOT.war")


def include(relative: Path) -> bool:
    parts = relative.parts
    if not parts or any(part in EXCLUDED_PARTS or part.startswith("._") or part.startswith(".package-") for part in parts):
        return False
    if relative.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if len(parts) == 1:
        return parts[0] in TOP_FILES
    if parts[0] not in TOP_DIRECTORIES:
        return False
    if parts[0] == "deploy":
        return parts[1] in {"ROOT", "ROOT.war", "nginx.conf.example"}
    if relative.suffix.lower() == ".war":
        return False
    return True


def delivery_members() -> list[tuple[str, bytes]]:
    members = []
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if relative == MANIFEST_PATH or not include(relative):
            continue
        if path.is_symlink():
            raise ValueError(f"Refusing to package symlink: {relative.as_posix()}")
        if not path.is_file():
            continue
        private = any(part in PRIVATE_NAMES or part.startswith(".env.") for part in relative.parts) or path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}
        if private:
            raise ValueError(f"Refusing private-key or credential-shaped filename: {relative.as_posix()}")
        members.append((relative.as_posix(), path.read_bytes()))
    required = {"README.md", "build.py", "requirements-optional.txt", "content/site.json", "content/profile.json", "content/coursework.json", "content/cv-build.json", "scripts/build_cv.py", "scripts/validate.py", "scripts/package.py", "docs/TEST_REPORT.md", "docs/DEPLOYMENT_TOMCAT.md", "docs/DEPLOYMENT_STATIC.md", "docs/CONTENT_GUIDE_ZH.md", "docs/RELEASE_REVIEW_ZH.md", "docs/VERIFICATION_NOTES.md", "deploy/ROOT.war", "site/index.html"}
    missing = sorted(required - {name for name, _ in members})
    if missing:
        raise ValueError("Required delivery files are missing: " + ", ".join(missing))
    return members


def create_manifest(members: list[tuple[str, bytes]]) -> bytes:
    config = json.loads((ROOT / "content/site.json").read_text(encoding="utf-8"))
    manifest = {
        "format_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "base_url": config["base_url"],
        "hash_algorithm": "SHA-256",
        "archive_member_timestamp": "2026-10-17T00:00:00 (ZIP timestamp; no timezone field)",
        "reproducibility": "Sorted paths, normalized permissions, fixed member timestamps and deterministic JSON. Identical file bytes and the same Python/zlib runtime produce identical archives.",
        "integrity_scope": "Every delivery file except this manifest; the outer delivery ZIP is not an input. site, deploy/ROOT and ROOT.war equality is checked by scripts/validate.py --check-deploy.",
        "source_file_count": len(members),
        "files": [{"path": name, "bytes": len(data), "sha256": sha256(data).hexdigest()} for name, data in sorted(members)],
    }
    return (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def package(output: Path) -> None:
    site = ROOT / "site"
    if contained(output, ROOT):
        raise ValueError("Choose a ZIP destination outside the project directory to avoid recursive packaging.")
    # Refuse stale CV inputs before constructing a new deployment bundle. This mode
    # uses only the standard library and does not regenerate or silently copy PDFs.
    subprocess.run([sys.executable, str(ROOT / "scripts/build_cv.py"), "--check"], cwd=ROOT, check=True)
    create_deployment(site)
    # This single gate checks both the current site and the newly constructed WAR/mirror.
    # The user-facing ZIP is not replaced if validation fails.
    subprocess.run([sys.executable, str(ROOT / "scripts/validate.py"), "--check-deploy"], cwd=ROOT, check=True)
    members = delivery_members()
    manifest_data = create_manifest(members)
    (ROOT / MANIFEST_PATH).write_bytes(manifest_data)
    members.append((MANIFEST_PATH.as_posix(), manifest_data))
    archive_members = [(f"{ROOT.name}/{name}", data) for name, data in members]
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".portfolio-delivery-", dir=output.parent) as working:
        temporary = Path(working) / output.name
        archive_bytes(temporary, archive_members)
        if temporary.stat().st_size > 10 * 1024 * 1024:
            raise ValueError("The delivery ZIP exceeds the intended 10 MiB limit; review included artifacts.")
        with ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise ValueError("Delivery ZIP CRC verification failed")
            expected = {name: sha256(data).hexdigest() for name, data in archive_members}
            actual = {info.filename: sha256(archive.read(info)).hexdigest() for info in archive.infolist()}
            if actual != expected or len(archive.infolist()) != len(expected):
                raise ValueError("Delivery ZIP contents differ from the captured source snapshot")
        temporary.replace(output)
    print(f"Created: {output}")
    print(f"Size: {output.stat().st_size:,} bytes")
    print(f"SHA-256: {sha256(output.read_bytes()).hexdigest()}")
    print(f"Entries: {len(archive_members)}; top-level directory: {ROOT.name}/")
    print("Deployment performed: no")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="ZIP path outside the project directory")
    args = parser.parse_args()
    try:
        package(args.output.expanduser().resolve())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Packaging stopped: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
