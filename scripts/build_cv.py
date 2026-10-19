#!/usr/bin/env python3
"""Build concise, bilingual public CVs from content/profile.json.

The static website build does not need these optional dependencies. To regenerate:
    python3 -m pip install -r requirements-optional.txt
    python3 scripts/build_cv.py

Check existing outputs using the standard library only:
    python3 scripts/build_cv.py --check

The bundled OFL fonts are small, embedded subsets covering the current public
profile. If new content introduces unsupported characters, pass full TrueType
fonts with --font-regular and --font-semibold, or extend the font subsets before
rebuilding. Unsupported characters fail explicitly instead of becoming boxes.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import tempfile
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "content/profile.json"
OUTPUT = ROOT / "static/files"
MANIFEST = ROOT / "content/cv-build.json"
FONTS = ROOT / "scripts/fonts"
LANGUAGES = ("en", "zh")
NAMES = {lang: f"zhongjie-huang-cv-{lang}.pdf" for lang in LANGUAGES}

LABELS = {
    "en": {
        "eyebrow": "RESEARCH + SOFTWARE",
        "profile": "Profile",
        "education": "Education",
        "research": "Selected academic projects",
        "software": "Selected software projects",
        "more": "Additional project work",
        "skills": "Technical toolkit",
        "direction": "Proposed doctoral direction",
        "languages": "Communication",
        "programming": "Programming & interfaces",
        "vision": "Machine learning & vision",
        "data": "Data & engineering",
        "mobile": "Mobile & systems",
        "practice": "Research practice",
        "source": "Public source",
        "case": "Project summary",
        "reviewed": "Profile reviewed",
        "page": "Page",
        "continued": "RESEARCH + SOFTWARE / CONTINUED",
    },
    "zh": {
        "eyebrow": "研究与软件工程",
        "profile": "个人简介",
        "education": "教育背景",
        "research": "精选学术项目",
        "software": "精选软件项目",
        "more": "更多项目实践",
        "skills": "技术工具与方法",
        "direction": "拟开展的博士研究方向",
        "languages": "交流语言",
        "programming": "编程与界面",
        "vision": "机器学习与视觉",
        "data": "数据与工程",
        "mobile": "移动端与系统",
        "practice": "研究方法",
        "source": "公开源码",
        "case": "项目介绍",
        "reviewed": "资料核对",
        "page": "第",
        "continued": "研究与软件工程 / 续页",
    },
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    return sha256(path.read_bytes())


def localise(value, lang: str) -> str:
    return str(value.get(lang, value.get("en", ""))) if isinstance(value, dict) else str(value)


def clean(value: str) -> str:
    replacements = {
        "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-",
        "\u2014": "-", "\u2212": "-", "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"', "\u00a0": " ",
    }
    return "".join(replacements.get(char, char) for char in value)


def text(value: str) -> str:
    return html.escape(clean(value), quote=False)


def first_sentences(value: str, lang: str, count: int = 2) -> str:
    separator = r"(?<=[。！？])" if lang == "zh" else r"(?<=[.!?])\s+"
    return ("" if lang == "zh" else " ").join(re.split(separator, value)[:count]).strip()


def section_body(project: dict, heading: str, lang: str, fallback: str = "") -> str:
    for section in project.get("sections", []):
        if localise(section.get("heading", {}), "en") == heading:
            return localise(section["body"], lang)
    return fallback


def source_state(profile_path: Path, regular: Path, semibold: Path) -> dict:
    for path in (profile_path, regular, semibold):
        if not path.is_file():
            raise ValueError(f"Required source is missing: {path}")
    return {
        "profile_sha256": digest_file(profile_path),
        "builder_sha256": digest_file(Path(__file__)),
        "fonts_sha256": {
            "regular": digest_file(regular),
            "semibold": digest_file(semibold),
        },
    }


def load_profile(path: Path) -> dict:
    profile = json.loads(path.read_text(encoding="utf-8"))
    required = ("person", "contact", "education", "projects", "skills", "updated")
    if any(key not in profile for key in required):
        raise ValueError("profile.json is missing a required public-profile section")
    date.fromisoformat(profile["updated"])
    for key in ("website", "linkedin", "github"):
        parsed = urlparse(profile["contact"].get(key, ""))
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"contact.{key} must be a complete HTTPS public URL")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", profile["contact"].get("email", "")):
        raise ValueError("contact.email is not a valid public email address")
    identifiers = [item["id"] for item in profile["projects"]]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Duplicate project IDs in profile.json")
    for project_id in ("histology-segmentation", "emotion-recognition", "marginloom",
                       "investment-financial-management", "outcomelab"):
        if project_id not in identifiers:
            raise ValueError(f"The selected CV project is missing: {project_id}")
    pending = next((item for item in profile["education"] if item["id"] == "msc"), None)
    if pending and pending.get("status") == "award_pending":
        if "pending" not in localise(pending["status_label"], "en").lower():
            raise ValueError("MSc status is award_pending but its public label omits pending")
    return profile


def check_existing(state: dict) -> int:
    if not MANIFEST.is_file():
        raise ValueError("CV build record is missing. Run scripts/build_cv.py to regenerate.")
    record = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if record.get("source") != state:
        raise ValueError("Public profile, CV builder or fonts changed. Regenerate both CV PDFs before packaging.")
    for lang in LANGUAGES:
        output = OUTPUT / NAMES[lang]
        expected = record.get("outputs", {}).get(lang, {})
        if not output.is_file() or digest_file(output) != expected.get("sha256"):
            raise ValueError(f"CV output is missing or changed: {output.name}")
        if expected.get("pages") not in (1, 2):
            raise ValueError(f"Invalid saved CV page count for {lang}")
    print("CV source check passed: public profile, builder, fonts and both PDF files match.")
    return 0


def build_one(profile: dict, lang: str, destination: Path, regular: Path,
              semibold: Path, state: dict) -> None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT, TA_RIGHT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import (
            Flowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
            Table, TableStyle,
        )
    except ImportError as exc:
        raise ValueError("PDF regeneration needs requirements-optional.txt (ReportLab and pypdf).") from exc

    pdfmetrics.registerFont(TTFont("CVRegular", str(regular)))
    pdfmetrics.registerFont(TTFont("CVSemibold", str(semibold)))
    pdfmetrics.registerFontFamily("CVRegular", normal="CVRegular", bold="CVSemibold",
                                  italic="CVRegular", boldItalic="CVSemibold")

    labels = LABELS[lang]
    ink = colors.HexColor("#19323C")
    teal = colors.HexColor("#16675E")
    muted = colors.HexColor("#536972")
    line = colors.HexColor("#D9E3E4")
    width, height = A4
    margin = 44
    # SimpleDocTemplate's frame has six-point padding on each side.
    # Match custom rules and tables to the actual paragraph width.
    inner = width - 2 * margin - 12
    body_size = 9.5 if lang == "en" else 9.5
    body_leading = 13.4 if lang == "en" else 14.4
    common = {"fontName": "CVRegular", "textColor": ink,
              "wordWrap": "CJK" if lang == "zh" else None,
              "allowWidows": 0, "allowOrphans": 0}
    styles = {
        "name": ParagraphStyle("Name", fontName="CVSemibold", fontSize=27,
                               leading=32, textColor=ink, spaceAfter=4),
        "subhead": ParagraphStyle("Subhead", fontSize=11.1, leading=15, spaceAfter=7, **common),
        "body": ParagraphStyle("Body", fontSize=body_size, leading=body_leading,
                               spaceAfter=5.6, **common),
        "small": ParagraphStyle("Small", fontSize=8.5, leading=11.7, spaceAfter=3.5, **common),
        "meta": ParagraphStyle("Meta", fontSize=8.3, leading=11.5, spaceAfter=4,
                               **{**common, "textColor": muted}),
        "title": ParagraphStyle("Title", fontSize=10.5, leading=14.5, spaceAfter=3.5,
                                **{**common, "fontName": "CVSemibold"}),
        "bullet": ParagraphStyle("Bullet", fontSize=body_size, leading=body_leading,
                                 leftIndent=9, firstLineIndent=0, bulletIndent=0,
                                 spaceAfter=4.5, **common),
        "right": ParagraphStyle("Right", fontSize=8.6, leading=12.0, alignment=TA_RIGHT,
                                **{**common, "textColor": muted}),
        "skill": ParagraphStyle("Skill", fontSize=8.9, leading=12.5, spaceAfter=5, **common),
        "direction": ParagraphStyle("Direction", fontSize=9.0, leading=12.8, spaceAfter=0, **common),
    }

    # Collect every rendered character and fail before the output is accepted if
    # a future edit needs a glyph not covered by the bundled font subset.
    rendered = []

    def para(value: str, style: str = "body", markup: bool = False, bullet: bool = False):
        rendered.append(clean(re.sub(r"<[^>]*>", "", html.unescape(value)) if markup else value))
        return Paragraph(value if markup else text(value), styles[style], bulletText="-" if bullet else None)

    def link(url: str, label: str) -> str:
        return f'<link href="{html.escape(url, quote=True)}" color="#16675E">{text(label)}</link>'

    def project_url(project_id: str) -> str:
        language_prefix = "zh/" if lang == "zh" else ""
        return profile["contact"]["website"].rstrip("/") + "/" + language_prefix + "projects/" + project_id + "/"

    class SectionLabel(Flowable):
        def __init__(self, label: str):
            super().__init__()
            self.label = clean(label.upper() if lang == "en" else label)
            self.height = 28
            rendered.append(self.label)

        def draw(self):
            self.canv.setStrokeColor(line)
            self.canv.setLineWidth(0.65)
            self.canv.line(0, 23, inner, 23)
            self.canv.setFillColor(teal)
            self.canv.setFont("CVSemibold", 9.0 if lang == "en" else 10.0)
            self.canv.drawString(0, 8, self.label)

    def section(label: str):
        return SectionLabel(labels[label])

    def dated_title(title: str, period: str):
        row = Table([[para(title, "title"), para(period, "right")]], colWidths=[inner - 126, 126])
        row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return row

    def project_block(project: dict, bodies: list[str], compact: bool = False):
        pieces = [dated_title(localise(project["title"], lang), localise(project["period"], lang))]
        if not compact:
            pieces.append(para(localise(project["role"], lang), "meta"))
        for body in bodies:
            pieces.append(para(body, "small" if compact else "bullet", bullet=not compact))
        if not compact and project["stack"]:
            pieces.append(para(" / ".join(project["stack"][:6]), "meta"))
        destinations = [link(project_url(project["id"]), labels["case"])]
        if project.get("live_url"):
            destinations.append(link(project["live_url"], "Live demo" if lang == "en" else "在线演示"))
        if project.get("repository"):
            destinations.append(link(project["repository"], "GitHub" if project["id"] in {"outcomelab", "marginloom"} else labels["source"]))
        pieces.append(para(" &nbsp; | &nbsp; ".join(destinations), "small", markup=True))
        pieces.append(Spacer(1, 6 if compact else 8))
        return KeepTogether(pieces)

    person = profile["person"]
    contact = profile["contact"]
    projects = {item["id"]: item for item in profile["projects"]}
    story = []
    story.append(para(labels["eyebrow"], "meta"))
    name = person["name_latin"].upper() if lang == "en" else person["name_chinese"] + "  |  " + person["name_latin"]
    story.append(para(name, "name"))
    story.append(para(localise(person["discipline"], lang), "subhead"))
    location = localise(person["location"], lang)
    site_label = contact["website"].replace("https://", "").rstrip("/")
    story.append(para(text(location) + " &nbsp; | &nbsp; " + link("mailto:" + contact["email"], contact["email"])
                      + " &nbsp; | &nbsp; " + link(contact["website"], site_label), "small", markup=True))
    github_label = "GitHub / " + contact["github"].rstrip("/").split("/")[-1]
    story.append(para(link(contact["github"], github_label) + " &nbsp; | &nbsp; "
                      + link(contact["linkedin"], "LinkedIn / " + person["name_latin"]), "small", markup=True))
    story.append(Spacer(1, 8))

    story.append(section("profile"))
    story.append(para(localise(person["summary"], lang)))
    story.append(Spacer(1, 4))

    story.append(section("education"))
    for edu in profile["education"]:
        entry = [dated_title(localise(edu["institution"], lang), localise(edu["period"], lang)),
                 para(localise(edu["degree"], lang), "body")]
        if edu.get("status") == "award_pending":
            status = ("Dissertation submitted; final results and degree award pending." if lang == "en"
                      else "论文已提交；最终成绩及学位授予仍待确认。")
            entry.append(para(status, "meta"))
        else:
            entry.append(para(localise(edu["status_label"], lang), "meta"))
        entry.append(Spacer(1, 6))
        story.append(KeepTogether(entry))

    story.append(section("research"))
    msc = projects["histology-segmentation"]
    story.append(project_block(msc, [section_body(msc, "What I did", lang),
                                    section_body(msc, "What the result supports", lang)]))
    bsc = projects["emotion-recognition"]
    bsc_result = first_sentences(section_body(bsc, "Reported result", lang), lang, 1)
    story.append(project_block(bsc, [localise(bsc["summary"], lang),
                                    bsc_result]))

    direction = profile.get("current", {}).get("doctoral_direction")
    if direction:
        story.append(KeepTogether([section("direction"),
                                  para(localise(direction["title"], lang), "title"),
                                  para(localise(direction["summary"], lang), "direction")]))

    story.append(PageBreak())
    story.append(para(labels["continued"], "meta"))
    story.append(para(person["name_latin"] if lang == "en" else person["name_chinese"], "title"))
    story.append(Spacer(1, 7))
    story.append(section("software"))
    outcomelab = projects["outcomelab"]
    story.append(project_block(outcomelab, [localise(outcomelab["summary"], lang)]))
    marginloom = projects["marginloom"]
    story.append(project_block(marginloom, [localise(marginloom["summary"], lang)]))
    investment = projects["investment-financial-management"]
    story.append(project_block(investment, [localise(investment["summary"], lang),
                                           section_body(investment, "Application engineering", lang)]))

    story.append(section("skills"))
    available_tools = {tool for project in profile["projects"] for tool in project["stack"]}
    available_tools.update(tool for skill in profile["skills"] for tool in skill["tools"])
    groups = [
        ("programming", ["Python", "Java 21", "Servlet 4", "HTML / CSS / JavaScript"]),
        ("vision", ["PyTorch", "Swin Transformer", "OpenCV", "QuPath", "Cellpose-DINO", "Cyto R-CNN", "CSGO", "scikit-learn"]),
        ("data", ["NumPy", "pandas", "Matplotlib", "SQL", "JDBC / MySQL", "Maven", "Git", "Docker", "Linux", "Tomcat 9", "GitHub Actions"]),
    ]
    for label, candidates in groups:
        tools = [item for item in candidates if item in available_tools]
        story.append(para("<b>" + text(labels[label]) + ":</b> " + text(", ".join(tools)), "skill", markup=True))
    evaluation = next((item for item in profile["skills"] if item["id"] == "evaluation"), None)
    if evaluation:
        story.append(para("<b>" + text(labels["practice"]) + ":</b> " + text(localise(evaluation["description"], lang)), "skill", markup=True))
    languages = person.get("languages", {}).get(lang, [])
    if languages:
        story.append(para("<b>" + text(labels["languages"]) + ":</b> " + text("; ".join(languages)), "skill", markup=True))

    reviewed = date.fromisoformat(profile["updated"])
    reviewed_text = reviewed.strftime("%d %B %Y").lstrip("0") if lang == "en" else f"{reviewed.year} 年 {reviewed.month} 月 {reviewed.day} 日"
    footer = labels["reviewed"] + ": " + reviewed_text
    rendered.extend([footer, person["name_latin"], labels["page"], "1 / 2", "2 / 2", "-", "/"])
    for name in ("CVRegular", "CVSemibold"):
        glyphs = pdfmetrics.getFont(name).face.charToGlyph
        missing = sorted({char for value in rendered for char in clean(value)
                          if not char.isspace() and ord(char) not in glyphs})
        if missing:
            display = " ".join(f"{char} (U+{ord(char):04X})" for char in missing[:18])
            raise ValueError(f"{name} lacks characters from the current profile: {display}. Supply complete TrueType fonts before rebuilding.")

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setTitle(person["name_latin"] + (" - Public research and engineering CV" if lang == "en" else " - 公开研究与工程简历"))
        canvas.setAuthor(person["name_latin"])
        canvas.setSubject("Public professional profile, reviewed " + profile["updated"])
        canvas.setCreator("Zhongjie portfolio CV builder")
        canvas.setKeywords("profile-sha256=" + state["profile_sha256"])
        canvas.setStrokeColor(teal)
        canvas.setLineWidth(2.3)
        canvas.line(margin + 6, height - 21, margin + 44, height - 21)
        canvas.setStrokeColor(line)
        canvas.setLineWidth(0.6)
        canvas.line(margin + 6, 35, width - margin - 6, 35)
        canvas.setFillColor(muted)
        canvas.setFont("CVRegular", 7.6)
        canvas.drawString(margin + 6, 22, clean(footer))
        page_label = f"{labels['page']} {doc.page} / 2" + (" 页" if lang == "zh" else "")
        canvas.drawRightString(width - margin - 6, 22, page_label)
        canvas.restoreState()

    doc = SimpleDocTemplate(str(destination), pagesize=A4, rightMargin=margin,
                            leftMargin=margin, topMargin=34, bottomMargin=48,
                            pageCompression=1, invariant=1)
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check staleness and hashes without PDF dependencies.")
    parser.add_argument("--font-regular", type=Path, default=FONTS / "PortfolioSansSC-Regular.ttf")
    parser.add_argument("--font-semibold", type=Path, default=FONTS / "PortfolioSansSC-Semibold.ttf")
    args = parser.parse_args()
    profile = load_profile(PROFILE)
    state = source_state(PROFILE, args.font_regular, args.font_semibold)
    if args.check:
        return check_existing(state)
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("PDF regeneration needs pypdf from requirements-optional.txt.") from exc
    OUTPUT.mkdir(parents=True, exist_ok=True)
    outputs = {}
    with tempfile.TemporaryDirectory(prefix="portfolio-cv-") as temporary:
        staging = Path(temporary)
        for lang in LANGUAGES:
            target = staging / NAMES[lang]
            build_one(profile, lang, target, args.font_regular, args.font_semibold, state)
            reader = PdfReader(target)
            if len(reader.pages) != 2:
                raise ValueError(f"{lang} layout produced {len(reader.pages)} pages; expected 2. Review content density before release.")
            extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
            if profile["contact"]["email"] not in extracted:
                raise ValueError(f"The public contact email is missing from the {lang} PDF text.")
            if "\ufffd" in extracted or "\u25a0" in extracted:
                raise ValueError(f"The {lang} PDF contains a replacement glyph; review the embedded font.")
            if any(edu.get("id") == "msc" and edu.get("status") == "award_pending" for edu in profile["education"]):
                expected = "pending" if lang == "en" else "待确认"
                if expected not in extracted:
                    raise ValueError(f"The {lang} PDF lost the MSc award-pending status.")
            outputs[lang] = {"file": "static/files/" + target.name,
                             "sha256": digest_file(target), "bytes": target.stat().st_size,
                             "pages": len(reader.pages)}
        # Avoid publishing a half-updated pair or a pair generated from changing data.
        if source_state(PROFILE, args.font_regular, args.font_semibold) != state:
            raise ValueError("Profile, builder or fonts changed during generation. Regenerate from one stable source state.")
        for lang in LANGUAGES:
            (OUTPUT / NAMES[lang]).write_bytes((staging / NAMES[lang]).read_bytes())
    record = {"profile_reviewed": profile["updated"], "source": state, "outputs": outputs}
    MANIFEST.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(outputs, indent=2, ensure_ascii=False))
    return check_existing(state)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"CV build error: {exc}", file=sys.stderr)
        raise SystemExit(1)
