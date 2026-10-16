#!/usr/bin/env python3
"""Validate generated portfolio files without a web server or third-party packages.

This is structural validation, not a substitute for a browser or server smoke test.
Run from any working directory: python3 scripts/validate.py
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from urllib.parse import unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile


ROOT = Path(__file__).resolve().parents[1]
CERTIFICATE_SHA256 = "3a1c5afda69264df17715098d05bb5ad24d8888676857c1a0ccff1b04f486087"
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
LANGUAGES = {"en-GB", "zh-CN"}
EXCLUDED_NAMES = {".git", ".aws", ".ssh", ".env", ".env.local", ".env.production", ".DS_Store", "__MACOSX", "__pycache__", ".pytest_cache", ".cache", "node_modules", "venv", ".venv", "id_rsa", "id_ed25519", "credentials.json", "credentials.yaml", "credentials.yml", "credentials.ini", "secrets.json", "secrets.yaml", "secrets.yml"}
SECRET_SHAPES = (
    ("private-key block", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("AWS access-key shape", re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("GitHub token shape", re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b")),
    ("API secret-key shape", re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b")),
    ("populated credential field", re.compile(rb"[\"'](?:password|passwd|api[_-]?key|client[_-]?secret|access[_-]?token|refresh[_-]?token)[\"']\s*:\s*[\"'][^\"']{4,}[\"']", re.I)),
    ("URL with embedded credentials", re.compile(rb"https?://[^\s/<>\"']+:[^\s/<>\"']+@", re.I)),
)
TEXT_EXTENSIONS = {".html", ".css", ".js", ".json", ".webmanifest", ".xml", ".svg", ".txt"}


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def is_inside(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False


def public_route(relative: Path) -> str:
    route = relative.as_posix()
    if route == "index.html":
        return ""
    if route.endswith("/index.html"):
        return route[:-len("index.html")]
    return route


class Page(HTMLParser):
    """Collect the HTML structures relevant to the checks below."""

    def __init__(self, path: Path, relative: Path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.relative = relative
        self.lang = ""
        self.ids: Counter[str] = Counter()
        self.meta: dict[str, list[str]] = defaultdict(list)
        self.charsets: list[str] = []
        self.title_parts: list[str] = []
        self.title_count = 0
        self.in_title = False
        self.in_head = False
        self.h1_count = 0
        self.images: list[dict] = []
        self.references: list[tuple[str, str, str, bool, dict]] = []
        self.head_links: list[dict] = []
        self.language_links: list[dict] = []
        self.labels: set[str] = set()
        self.controls: list[tuple[str, dict, bool]] = []
        self.label_depth = 0
        self.base_hrefs: list[str] = []
        self.json_ld: list[str] = []
        self.script_attrs: list[dict] = []
        self._json_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {key: value if value is not None else "" for key, value in attrs}
        if a.get("id"):
            self.ids[a["id"]] += 1
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "head":
            self.in_head = True
        elif tag == "title" and self.in_head:
            self.title_count += 1
            self.in_title = True
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "meta" and self.in_head:
            if "charset" in a:
                self.charsets.append(a["charset"].lower())
            key = a.get("name", a.get("property", "")).lower()
            if key:
                self.meta[key].append(a.get("content", ""))
        elif tag == "link" and self.in_head:
            self.head_links.append(a)
        elif tag == "img":
            self.images.append(a)
        elif tag == "label":
            self.label_depth += 1
            if a.get("for"):
                self.labels.add(a["for"])
        elif tag in {"input", "select", "textarea"}:
            self.controls.append((tag, a, self.label_depth > 0))
        elif tag == "base":
            self.base_hrefs.append(a.get("href", ""))
        elif tag == "script":
            self.script_attrs.append(a)
            if a.get("type", "").lower() == "application/ld+json":
                self._json_parts = []
        if tag == "a" and a.get("hreflang"):
            self.language_links.append(a)
        metadata = tag == "link" and bool({"canonical", "alternate"} & set(a.get("rel", "").split()))
        for attribute in ("href", "src", "action", "poster"):
            if attribute in a and tag != "base":
                self.references.append((tag, attribute, a[attribute], metadata, a))
        if a.get("srcset"):
            # The site uses file-based srcset candidates, not comma-containing data URIs.
            for candidate in a["srcset"].split(","):
                parts = candidate.strip().split()
                if parts:
                    self.references.append((tag, "srcset", parts[0], False, a))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self._json_parts is not None:
            self._json_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "head":
            self.in_head = False
        elif tag == "title":
            self.in_title = False
        elif tag == "label":
            self.label_depth = max(0, self.label_depth - 1)
        elif tag == "script" and self._json_parts is not None:
            self.json_ld.append("".join(self._json_parts))
            self._json_parts = None


class Validation:
    def __init__(self, site: Path, report: Path, check_deploy: bool):
        self.site = site.resolve()
        self.report = report.resolve()
        self.check_deploy = check_deploy
        self.results: dict[str, Counter] = defaultdict(Counter)
        self.errors: list[str] = []
        self.pages: dict[Path, Page] = {}
        self.external_urls: set[str] = set()
        self.metrics: Counter = Counter()
        self.base_url = ""

    def require(self, condition: bool, category: str, message: str) -> None:
        self.results[category]["checks"] += 1
        if condition:
            self.results[category]["passed"] += 1
        else:
            self.results[category]["failed"] += 1
            self.errors.append(f"{category}: {message}")

    def page_url(self, relative: Path) -> str:
        return self.base_url + "/" + public_route(relative)

    def load_inputs(self) -> bool:
        configuration = ROOT / "content/site.json"
        try:
            config = json.loads(configuration.read_text(encoding="utf-8"))
            self.base_url = str(config["base_url"]).rstrip("/")
        except (OSError, ValueError, KeyError, TypeError):
            self.require(False, "Configuration", "content/site.json must contain a valid base_url")
            return False
        split = urlsplit(self.base_url)
        valid_base = split.scheme in {"https", "http"} and bool(split.netloc) and not split.query and not split.fragment and not split.username and not split.password
        self.require(valid_base, "Configuration", "base_url must be an absolute HTTP(S) URL without credentials, query or fragment")
        self.require(self.site.is_dir(), "Configuration", "generated site directory is missing; run build.py first")
        self.require((self.site / "index.html").is_file(), "Configuration", "site/index.html is missing")
        return valid_base and self.site.is_dir()

    def collect_pages(self) -> None:
        for path in sorted(self.site.rglob("*.html")):
            relative = path.relative_to(self.site)
            try:
                page = Page(path, relative)
                page.feed(path.read_text(encoding="utf-8"))
                page.close()
                self.pages[path.resolve()] = page
                self.require(True, "HTML parsing", "")
            except (OSError, UnicodeError, ValueError):
                self.require(False, "HTML parsing", f"{relative.as_posix()} could not be parsed as UTF-8 HTML")
        self.metrics["HTML pages"] = len(self.pages)
        self.require(bool(self.pages), "HTML parsing", "no HTML pages were found")

    def inspect_page(self, page: Page) -> None:
        name = page.relative.as_posix()
        chinese = name.startswith("zh/")
        english_relative = Path(name[3:] if chinese else name)
        counterparts = {
            "en-GB": self.page_url(english_relative),
            "zh-CN": self.page_url(Path("zh") / english_relative),
            "x-default": self.page_url(english_relative),
        }
        self.require(page.lang == ("zh-CN" if chinese else "en-GB"), "Language and equivalents", f"{name} has an unexpected html lang")
        self.require(page.title_count == 1 and bool("".join(page.title_parts).strip()), "Head metadata", f"{name} needs one non-empty title")
        self.require(page.charsets == ["utf-8"], "Head metadata", f"{name} needs one UTF-8 charset declaration")
        self.require(page.h1_count == 1, "Heading and IDs", f"{name} must contain exactly one h1")
        duplicates = sum(1 for count in page.ids.values() if count > 1)
        self.require(duplicates == 0, "Heading and IDs", f"{name} contains {duplicates} duplicate ID values")
        self.metrics["HTML ID values"] += len(page.ids)
        for key in ("description", "viewport", "og:type", "og:title", "og:description", "og:url", "twitter:card"):
            values = page.meta.get(key, [])
            self.require(len(values) == 1 and bool(values[0].strip()), "Head metadata", f"{name} needs exactly one non-empty {key} value")
        self.require("width=device-width" in "".join(page.meta.get("viewport", [])).replace(" ", ""), "Head metadata", f"{name} needs a responsive viewport")
        canonical = [a.get("href", "") for a in page.head_links if "canonical" in a.get("rel", "").split()]
        expected_url = self.page_url(page.relative)
        self.require(canonical == [expected_url], "Head metadata", f"{name} canonical does not match configured base_url and page route")
        self.require(page.meta.get("og:url", []) == [expected_url], "Head metadata", f"{name} og:url does not match its canonical")
        for lang, expected in counterparts.items():
            links = [a.get("href", "") for a in page.head_links if "alternate" in a.get("rel", "").split() and a.get("hreflang") == lang]
            self.require(links == [expected], "Language and equivalents", f"{name} hreflang {lang} must refer to the equivalent page")
        counterpart = self.site / (english_relative if chinese else Path("zh") / english_relative)
        self.require(counterpart.is_file(), "Language and equivalents", f"{name} has no equivalent file in the other language")
        language = "en-GB" if chinese else "zh-CN"
        visible = [a for a in page.language_links if a.get("hreflang") == language]
        self.require(bool(visible), "Language and equivalents", f"{name} needs a visible link to its other-language equivalent")
        for link in page.language_links:
            expected = counterparts.get(link.get("hreflang", ""))
            actual = urljoin(page.base_hrefs[0] if page.base_hrefs else expected_url, link.get("href", ""))
            self.require(expected is not None and actual == expected, "Language and equivalents", f"{name} has a language switch that does not preserve the current page")
        if page.relative.name == "404.html":
            self.require("noindex" in " ".join(page.meta.get("robots", [])).lower(), "Head metadata", f"{name} must be noindex")
            self.require(not page.base_hrefs, "404 routing", f"{name} must not change the document base, so fragment-only skip links stay on the error document")
            self.inspect_404_dispatch(page)
        else:
            self.require(not page.base_hrefs, "Relative browser URLs", f"{name} should not change the document base")
        for i, attrs in enumerate(page.images, 1):
            self.metrics["Image elements"] += 1
            self.require("alt" in attrs, "Image accessibility and sizing", f"{name} image {i} has no alt attribute")
            for dimension in ("width", "height"):
                value = attrs.get(dimension, "")
                self.require(value.isdigit() and int(value) > 0, "Image accessibility and sizing", f"{name} image {i} needs a positive {dimension}")
        for tag, attrs, implicit in page.controls:
            if tag == "input" and attrs.get("type", "text").lower() in {"hidden", "submit", "button", "reset", "image"}:
                continue
            self.metrics["Form controls requiring labels"] += 1
            labelledby = attrs.get("aria-labelledby", "").split()
            labelled = implicit or attrs.get("id") in page.labels or bool(attrs.get("aria-label", "").strip()) or (bool(labelledby) and all(identifier in page.ids for identifier in labelledby))
            self.require(labelled, "Form labels", f"{name} has an unlabelled {tag} control")
        for raw in page.json_ld:
            try:
                json.loads(raw)
                valid = True
            except (ValueError, TypeError):
                valid = False
            self.metrics["JSON-LD blocks"] += 1
            self.require(valid, "Structured data", f"{name} contains invalid JSON-LD")
        for tag, attribute, raw, metadata, attrs in page.references:
            self.inspect_reference(page.path, page.relative, raw, metadata, page.base_hrefs[0] if page.base_hrefs else None, tag, attribute)

    def inspect_404_dispatch(self, page: Page) -> None:
        """Model an internal error-page dispatch without starting a server.

        The browser retains the unknown request URL. Absolute configured URLs must
        still reach the same asset/page; a fragment-only skip link must stay on the
        error document and point to one of its IDs.
        """
        configured = urlsplit(self.base_url)
        missing_urls = (
            self.base_url + "/__missing__/arbitrary/deep/page",
            self.base_url + "/__missing__/arbitrary/deep/",
        )
        for tag, attribute, raw, metadata, attrs in page.references:
            if metadata:
                continue
            value = raw.strip()
            split = urlsplit(value)
            if split.scheme in {"mailto", "tel", "data", "blob"}:
                continue
            if split.netloc and split.netloc != configured.netloc:
                continue
            for missing in missing_urls:
                resolved = urlsplit(urljoin(missing, value))
                if value.startswith("#"):
                    requested = urlsplit(missing)
                    valid = resolved.scheme == requested.scheme and resolved.netloc == requested.netloc and resolved.path == requested.path and unquote(resolved.fragment) in page.ids
                else:
                    valid = value.startswith(self.base_url + "/") and resolved.geturl() == value
                self.metrics["404 references simulated at missing URLs"] += 1
                self.require(valid, "404 routing", f"{page.relative.as_posix()} {attribute} fails simulated arbitrary-depth error routing")

    def inspect_reference(self, source: Path, relative: Path, raw: str, metadata: bool = False, base_href: str | None = None, tag: str = "", attribute: str = "url") -> None:
        name = relative.as_posix()
        value = raw.strip()
        if not metadata:
            self.require(not value.startswith("/"), "Relative browser URLs", f"{name} contains a root-relative {attribute}")
        split = urlsplit(value)
        self.require(split.scheme.lower() not in {"javascript", "vbscript", "file"}, "URL safety", f"{name} contains a disallowed {attribute} URL scheme")
        if split.scheme in {"mailto", "tel", "data", "blob", "javascript", "vbscript", "file"}:
            return
        context_url = base_href or self.page_url(relative)
        absolute = urlsplit(urljoin(context_url, value))
        configured = urlsplit(self.base_url)
        if absolute.scheme not in {"http", "https"} or absolute.netloc != configured.netloc:
            if absolute.scheme in {"http", "https"}:
                self.external_urls.add(absolute.geturl())
            return
        if not metadata:
            if relative.name == "404.html":
                self.require(value.startswith(self.base_url + "/") or value.startswith("#"), "404 routing", f"{name} browser links must use configured absolute URLs or local fragments")
            else:
                self.require(not split.scheme and not split.netloc, "Relative browser URLs", f"{name} has a same-site absolute browser URL instead of a document-relative URL")
        prefix = unquote(configured.path.rstrip("/"))
        url_path = unquote(absolute.path)
        in_prefix = not prefix or url_path == prefix or url_path.startswith(prefix + "/")
        self.require(in_prefix, "Local paths and resources", f"{name} reference escapes the configured deployment path")
        if not in_prefix:
            return
        local = url_path[len(prefix):].lstrip("/")
        self.require("\\" not in local and "\x00" not in local, "URL safety", f"{name} contains an unsafe path character")
        target = self.site / local
        if absolute.path.endswith("/") or target.is_dir():
            target /= "index.html"
        safe = is_inside(target, self.site)
        self.require(safe, "Local paths and resources", f"{name} reference leaves the generated site directory")
        if not safe:
            return
        self.metrics["Local URL references"] += 1
        exists = target.is_file()
        self.require(exists, "Local paths and resources", f"{name} references missing {target.relative_to(self.site).as_posix()}")
        if exists and absolute.fragment and target.suffix.lower() == ".html":
            self.metrics["HTML anchor references"] += 1
            destination = self.pages.get(target.resolve())
            self.require(destination is not None and unquote(absolute.fragment) in destination.ids, "Internal anchors", f"{name} has a missing anchor in {target.relative_to(self.site).as_posix()}")

    def inspect_files(self) -> None:
        files = sorted(p for p in self.site.rglob("*") if p.is_file())
        self.metrics["Generated site files"] = len(files)
        self.metrics["Generated site bytes"] = sum(p.stat().st_size for p in files)
        for path in sorted(self.site.rglob("*")):
            relative = path.relative_to(self.site)
            self.require(not path.is_symlink(), "Public file safety", f"{relative.as_posix()} is a symlink")
            blocked = any(part in EXCLUDED_NAMES or part.startswith("._") or part.startswith(".env.") for part in relative.parts) or path.suffix.lower() in {".pem", ".key", ".p12", ".pfx", ".pyc"}
            self.require(not blocked, "Public file safety", f"{relative.as_posix()} has a private, cache or OS-metadata filename")
        for path in files:
            relative = path.relative_to(self.site)
            if path.suffix.lower() in TEXT_EXTENSIONS:
                data = path.read_bytes()
                for label, pattern in SECRET_SHAPES:
                    # Report only the file and pattern class, never the matching text.
                    self.require(pattern.search(data) is None, "Public file safety", f"{relative.as_posix()} contains a {label}")
            if path.suffix.lower() in {".css", ".js"}:
                match = re.search(r"[.-]([a-f0-9]{8,64})\.(?:css|js)$", path.name)
                self.require(bool(match), "Asset versioning", f"{relative.as_posix()} lacks a content hash in its filename")
                if match:
                    self.require(digest(path).startswith(match.group(1)), "Asset versioning", f"{relative.as_posix()} filename hash differs from its content")
            if path.suffix.lower() == ".css":
                text = re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.S)
                for match in re.finditer(r"url\(\s*(['\"]?)(.*?)\1\s*\)", text, flags=re.I):
                    value = match.group(2).strip()
                    if value.startswith("#"):
                        continue  # CSS fragment URLs are interpreted against the using document.
                    self.inspect_reference(path, relative, value, tag="css", attribute="url()")
        for certificate in (self.site / "files/degree-certificate.pdf", ROOT / "static/files/degree-certificate.pdf"):
            exists = certificate.is_file()
            self.require(exists, "Original certificate integrity", "the preserved original degree-certificate.pdf is missing")
            if exists:
                self.require(digest(certificate) == CERTIFICATE_SHA256, "Original certificate integrity", "degree-certificate.pdf does not match the supplied original SHA-256")

    def inspect_data(self) -> None:
        json_files = sorted(set((ROOT / "content").rglob("*.json")) | set(self.site.rglob("*.json")) | set(self.site.rglob("*.webmanifest")))
        self.metrics["JSON and webmanifest files"] = len(json_files)
        for path in json_files:
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
                valid = True
            except (OSError, UnicodeError, ValueError):
                document = None
                valid = False
            self.require(valid, "Structured data", f"{path.name} is not valid UTF-8 JSON")
            if valid and path.suffix == ".webmanifest" and isinstance(document, dict):
                relative = path.relative_to(self.site)
                for field in ("start_url", "scope"):
                    if isinstance(document.get(field), str):
                        self.inspect_reference(path, relative, document[field], tag="manifest", attribute=field)
                for icon in document.get("icons", []):
                    if isinstance(icon, dict) and isinstance(icon.get("src"), str):
                        self.inspect_reference(path, relative, icon["src"], tag="manifest", attribute="icon.src")
        coursework = ROOT / "content/coursework.json"
        try:
            modules = json.loads(coursework.read_text(encoding="utf-8"))
            valid = isinstance(modules, list) and len(modules) == 32
        except (OSError, ValueError):
            modules, valid = [], False
        self.require(valid, "Coursework completeness", "coursework.json must preserve all 32 supplied modules")
        if isinstance(modules, list):
            codes = [m.get("code") for m in modules if isinstance(m, dict)]
            self.require(len(codes) == len(set(codes)) == len(modules), "Coursework completeness", "coursework module codes must be unique")
            for module in modules:
                if not isinstance(module, dict):
                    self.require(False, "Coursework completeness", "a coursework item is not an object")
                    continue
                fields = all(isinstance(module.get(k), str) and module[k].strip() for k in ("code", "programme", "level", "area", "source"))
                bilingual = all(isinstance(module.get(k), dict) and all(isinstance(module[k].get(lang), str) and module[k][lang].strip() for lang in ("en", "zh")) for k in ("title", "description"))
                self.require(fields and bilingual, "Coursework completeness", f"module {module.get('code', '(unknown)')} is missing its bilingual fields")
        for path in sorted(self.site.rglob("*.xml")):
            try:
                tree = ET.parse(path)
                self.require(True, "XML configuration", "")
            except (OSError, ET.ParseError):
                self.require(False, "XML configuration", f"{path.relative_to(self.site).as_posix()} is invalid XML")
                continue
            if path.name == "web.xml":
                local = lambda e: e.tag.split("}")[-1]
                error_pages = [e for e in tree.getroot() if local(e) == "error-page"]
                matches = []
                for entry in error_pages:
                    values = {local(e): (e.text or "").strip() for e in entry}
                    if values.get("error-code") == "404":
                        matches.append(values.get("location"))
                self.require(matches == ["/404.html"], "404 routing", "WEB-INF/web.xml must map 404 to context-relative /404.html")
        self.require((self.site / "WEB-INF/web.xml").is_file(), "XML configuration", "site/WEB-INF/web.xml is required for the Tomcat package")
        self.require((self.site / "robots.txt").is_file(), "Search discovery", "robots.txt is missing")
        self.require((self.site / "sitemap.xml").is_file(), "Search discovery", "sitemap.xml is missing")
        robots = self.site / "robots.txt"
        if robots.is_file():
            declared = [line.split(":", 1)[1].strip() for line in robots.read_text(encoding="utf-8").splitlines() if line.lower().startswith("sitemap:")]
            self.require(self.base_url + "/sitemap.xml" in declared, "Search discovery", "robots.txt does not declare the configured sitemap URL")
        sitemap = self.site / "sitemap.xml"
        if sitemap.is_file():
            try:
                tree = ET.parse(sitemap)
                urls = [(e.text or "").strip() for e in tree.iter() if e.tag.split("}")[-1] == "loc"]
                self.metrics["Sitemap URLs"] = len(urls)
                expected = {self.page_url(p.relative) for p in self.pages.values() if p.relative.name != "404.html" and "noindex" not in " ".join(p.meta.get("robots", [])).lower()}
                self.require(set(urls) == expected and len(urls) == len(set(urls)), "Search discovery", "sitemap must list every indexable page exactly once using configured canonical URLs")
            except ET.ParseError:
                pass  # Already recorded by the XML check above.

    def inspect_cv(self) -> None:
        checker = ROOT / "scripts/build_cv.py"
        self.require(checker.is_file(), "CV source and output integrity", "scripts/build_cv.py is missing")
        if checker.is_file():
            try:
                result = subprocess.run([sys.executable, str(checker), "--check"], cwd=ROOT, capture_output=True, text=True, timeout=30)
                passed = result.returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                passed = False
            # The checker validates profile, script, font and PDF fingerprints without
            # importing PDF-generation dependencies. Do not echo source data on failure.
            self.require(passed, "CV source and output integrity", "CV source/PDF fingerprints are stale or invalid; run python3 scripts/build_cv.py --check for details and regenerate both PDFs if required")
            self.metrics["CV source fingerprint check invocations"] += 1
        for language in ("en", "zh"):
            name = f"zhongjie-huang-cv-{language}.pdf"
            original = ROOT / "static/files" / name
            generated = self.site / "files" / name
            both = original.is_file() and generated.is_file()
            self.require(both, "CV source and output integrity", f"{name} must exist in both static/files and site/files")
            if both:
                self.require(digest(original) == digest(generated), "CV source and output integrity", f"site/files/{name} is stale; rebuild the site before packaging")
                self.metrics["Verified source/generated CV pairs"] += 1

    def inspect_deploy(self) -> None:
        mirror = ROOT / "deploy/ROOT"
        archive = ROOT / "deploy/ROOT.war"
        self.require(mirror.is_dir(), "Deployment archive integrity", "deploy/ROOT is missing")
        self.require(archive.is_file(), "Deployment archive integrity", "deploy/ROOT.war is missing")
        site_files = {p.relative_to(self.site).as_posix(): digest(p) for p in self.site.rglob("*") if p.is_file()}
        if mirror.is_dir():
            mirror_files = {p.relative_to(mirror).as_posix(): digest(p) for p in mirror.rglob("*") if p.is_file()}
            self.require(mirror_files == site_files, "Deployment archive integrity", "deploy/ROOT files differ from site files")
            self.metrics["Verified exploded deployment files"] = len(mirror_files)
        if archive.is_file():
            try:
                with ZipFile(archive) as war:
                    names = [i.filename for i in war.infolist() if not i.is_dir()]
                    safe = all(not n.startswith(("/", "\\")) and ".." not in PurePosixPath(n).parts and "\\" not in n for n in names)
                    self.require(safe and len(names) == len(set(names)), "Deployment archive integrity", "WAR has unsafe or duplicate archive paths")
                    self.require(war.testzip() is None, "Deployment archive integrity", "WAR CRC verification failed")
                    hashes = {n: sha256(war.read(n)).hexdigest() for n in names}
                    self.require(hashes == site_files, "Deployment archive integrity", "WAR contents differ from site files")
                    self.metrics["Verified WAR members"] = len(names)
            except (OSError, BadZipFile):
                self.require(False, "Deployment archive integrity", "ROOT.war is not a readable ZIP/WAR")

    def write_report(self) -> None:
        total = sum(v["checks"] for v in self.results.values())
        failures = len(self.errors)
        lines = [
            "# Static validation report", "",
            f"**Result: {'PASS' if not failures else 'FAIL'}** — {total - failures} of {total} structural checks passed.", "",
            "Generated by `python3 scripts/validate.py" + (" --check-deploy" if self.check_deploy else "") + "` using the Python standard library.", "",
            "This report records inspection of the generated files. No browser, HTTP server, Tomcat instance or nginx instance was started for these checks.", "",
            "## Scope and counts", "", "| Item | Observed count |", "| --- | ---: |",
        ]
        for key, value in sorted(self.metrics.items()):
            lines.append(f"| {key} | {value:,} |")
        lines.extend([f"| Distinct external HTTP(S) references, not network-tested | {len(self.external_urls):,} |", "", "## Check results", "", "| Category | Checks | Passed | Failed |", "| --- | ---: | ---: | ---: |"])
        for category, result in sorted(self.results.items()):
            lines.append(f"| {category} | {result['checks']} | {result['passed']} | {result['failed']} |")
        lines.extend(["", "## Evidence and limits", "", f"- The preserved degree certificate was compared with the original upload SHA-256: `{CERTIFICATE_SHA256}`.", "- File-backed links, local resources, HTML anchors, bilingual equivalents, metadata, ID uniqueness, form labels, image attributes, content hashes and JSON/XML syntax were inspected.", "- Public-output safety checks cover suspicious file names and selected high-confidence secret patterns. They are not a proof that every possible personal or confidential detail has been identified.", "- The HTML checks use `html.parser.HTMLParser`; they are not a complete HTML standards validator or an accessibility conformance audit.", "- JavaScript execution, browser layout, keyboard interactions, responsive rendering, assistive-technology behaviour and external-link availability were not verified by this script.", "- Server response status, MIME types, cache/security headers, TLS, domain configuration, redirects and actual 404 dispatch require checks on the eventual server.", "- Only 404 documents use configured absolute URLs for internal navigation and resources; their fragment-only skip links retain the current error document. Resolution was statically simulated at deeply nested missing URLs, with and without a trailing slash. This is URL analysis, not an HTTP/browser test. Rebuild for the real domain and context path before deployment."])
        lines.append("- The CV source checker was invoked with the current Python interpreter in its standard-library-only `--check` mode, checking profile, builder, font and saved PDF fingerprints. Both published CVs were also compared by SHA-256 with static/files; stale PDFs require regeneration and a fresh site build.")
        if self.check_deploy:
            lines.append("- `site/`, `deploy/ROOT/` and every file inside `deploy/ROOT.war` were compared by SHA-256, including `WEB-INF/web.xml`; archive path safety and CRCs were checked.")
        else:
            lines.append("- Deployment archive equality was not included in this run. `scripts/package.py` invokes validation with `--check-deploy` before creating the delivery ZIP.")
        lines.extend(["", "## Failures", ""])
        lines.extend([f"- {message}" for message in self.errors] if self.errors else ["None found by the checks above."])
        lines.append("")
        self.report.parent.mkdir(parents=True, exist_ok=True)
        self.report.write_text("\n".join(lines), encoding="utf-8")

    def run(self) -> int:
        if self.load_inputs():
            self.collect_pages()
            for page in self.pages.values():
                self.inspect_page(page)
            self.inspect_files()
            self.inspect_data()
            self.inspect_cv()
            if self.check_deploy:
                self.inspect_deploy()
        self.write_report()
        total = sum(v["checks"] for v in self.results.values())
        print(f"{'PASS' if not self.errors else 'FAIL'}: {total - len(self.errors)}/{total} structural checks; {len(self.pages)} HTML pages.")
        for message in self.errors[:40]:
            print(f"  - {message}")
        if len(self.errors) > 40:
            print(f"  - {len(self.errors) - 40} further failures are listed in the report.")
        try:
            shown = self.report.relative_to(ROOT)
        except ValueError:
            shown = self.report
        print(f"Report: {shown}")
        return 1 if self.errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=ROOT / "site", help="generated static directory (default: site/)")
    parser.add_argument("--report", type=Path, default=ROOT / "docs/TEST_REPORT.md", help="Markdown report destination")
    parser.add_argument("--check-deploy", action="store_true", help="also compare site, deploy/ROOT and deploy/ROOT.war")
    args = parser.parse_args()
    return Validation(args.site, args.report, args.check_deploy).run()


if __name__ == "__main__":
    sys.exit(main())
