#!/usr/bin/env python3
"""Build the bilingual portfolio with Python 3.9+ and the standard library.

Usage: python3 scripts/build.py [--base-url https://example.org/portfolio]
Only site/ is generated. Source content, static assets and docs stay editable.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import posixpath
import shutil
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def esc(value):
    return html.escape(str(value), quote=True)


def translated(value, lang):
    if isinstance(value, dict):
        return value.get(lang, value.get("en", ""))
    return value


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def paragraphs(lines):
    if isinstance(lines, str):
        lines = [lines]
    return "".join(f"<p>{esc(line)}</p>" for line in lines)


def bullet_list(lines, klass=""):
    return f'<ul class="{esc(klass)}">' + "".join(f"<li>{esc(line)}</li>" for line in lines) + "</ul>"


LABELS = {
    "en": {
        "home": "Home", "about": "About", "research": "Research", "projects": "Projects",
        "education": "Education", "coursework": "Coursework", "skills": "Skills", "contact": "Contact",
        "now": "Now", "cv": "CV", "validation": "Research notes", "privacy": "Privacy",
        "credential": "Degree certificate", "skip": "Skip to main content", "nav": "Primary navigation",
        "menu": "Open menu", "theme": "Change colour theme", "search": "Search this site",
        "search_placeholder": "Search pages, projects or skills…", "close": "Close search",
        "no_results": "No matching pages. Try a project name or a broader topic.",
        "view_project": "Read case study", "source": "View source on GitHub", "updated": "Updated 16 October 2026",
        "all_projects": "Explore all projects", "all_modules": "Explore coursework", "view_cv": "View CV",
        "download_cv": "Download CV (PDF)", "email": "Email", "copy": "Copy email", "copied": "Email copied",
        "print": "Print / save as PDF", "back_projects": "All projects", "status": "Status", "role": "Role",
        "period": "Period", "tools": "Tools & methods", "outputs": "Outputs & learning", "limits": "Scope & limitations",
        "evidence": "Evidence basis", "related": "Keep exploring", "all": "All", "research_cat": "Academic research",
        "software_cat": "Software engineering", "language_switch": "中文", "more": "Learn more",
        "profile_download": "Download public profile (JSON)", "notfound": "Page not found"
    },
    "zh": {
        "home": "首页", "about": "关于我", "research": "研究", "projects": "项目", "education": "教育",
        "coursework": "课程", "skills": "技能", "contact": "联系", "now": "近况", "cv": "简历",
        "validation": "研究笔记", "privacy": "隐私", "credential": "学位证书", "skip": "跳至主要内容",
        "nav": "主导航", "menu": "打开菜单", "theme": "切换配色主题", "search": "搜索本站",
        "search_placeholder": "搜索页面、项目或技能…", "close": "关闭搜索", "no_results": "没有匹配的页面，请尝试项目名称或更宽泛的关键词。",
        "view_project": "查看项目案例", "source": "在 GitHub 查看源码", "updated": "更新于 2026 年 10 月 16 日",
        "all_projects": "查看全部项目", "all_modules": "查看课程目录", "view_cv": "查看简历",
        "download_cv": "下载简历（PDF）", "email": "电子邮件", "copy": "复制邮箱", "copied": "邮箱已复制",
        "print": "打印 / 保存为 PDF", "back_projects": "全部项目", "status": "状态", "role": "个人角色",
        "period": "时间", "tools": "工具与方法", "outputs": "产出与收获", "limits": "适用范围与局限",
        "evidence": "资料依据", "related": "继续了解", "all": "全部", "research_cat": "学术研究",
        "software_cat": "软件工程", "language_switch": "English", "more": "了解更多",
        "profile_download": "下载公开个人资料（JSON）", "notfound": "页面未找到"
    }
}

ROUTES = [
    ("", "home"), ("about/", "about"), ("research/", "research"), ("projects/", "projects"),
    ("education/", "education"), ("coursework/", "coursework"), ("skills/", "skills"),
    ("now/", "now"), ("cv/", "cv"), ("contact/", "contact"),
    ("education/degree-credential/", "credential"), ("insights/research-validation/", "validation"),
    ("privacy.html", "privacy"), ("404.html", "notfound")
]

DIMENSIONS = {
    "zhongjie-huang-480.webp": (480, 640), "zhongjie-huang-720.webp": (720, 960),
    "zhongjie-huang-960.webp": (960, 1280), "zhongjie-huang-720.jpg": (720, 960)
}


class Page:
    def __init__(self, builder, lang, route):
        self.b = builder
        self.lang = lang
        self.route = route
        self.prefix = "zh/" if lang == "zh" else ""
        self.filepath = self.prefix + (route if route.endswith(".html") else route + "index.html")
        # Error pages are internally forwarded from arbitrary missing URLs by servers.
        # Their absolute resources make paths deterministic without affecting #main.
        self.link_from = "index.html" if route == "404.html" else self.filepath
        self.labels = LABELS[lang]

    def t(self, value):
        return translated(value, self.lang)

    def w(self, en, zh):
        return en if self.lang == "en" else zh

    def l(self, key):
        if key == 'updated':
            reviewed = date.fromisoformat(self.b.config['updated'])
            return f'Updated {reviewed.day} {reviewed.strftime("%B")} {reviewed.year}' if self.lang == 'en' else f'更新于 {reviewed.year} 年 {reviewed.month} 月 {reviewed.day} 日'
        return self.labels[key]

    def rel(self, target):
        target = str(target)
        parts = urlsplit(target)
        if parts.scheme:
            if parts.scheme not in ("https", "http", "mailto"):
                raise ValueError(f"Unsupported link scheme: {parts.scheme}")
            return target
        if target.startswith("#"):
            return target
        if parts.netloc:
            raise ValueError("Protocol-relative links are not permitted")
        path = parts.path.lstrip("/")
        if self.route == '404.html':
            return self.b.config['base_url'] + '/' + path + ('?' + parts.query if parts.query else '') + ('#' + parts.fragment if parts.fragment else '')
        rel = posixpath.relpath(path or ".", posixpath.dirname(self.link_from) or ".")
        if not path or path.endswith("/"):
            rel = ("./" if rel == "." else rel + "/")
        return urlunsplit(("", "", rel, parts.query, parts.fragment))

    def url(self, route=""):
        if urlsplit(route).scheme:
            return route
        return self.rel(self.prefix + route)

    def link(self, route, label, klass="text-link", external=False, **attrs):
        href = route if external else self.url(route)
        extra = ""
        if external and not href.startswith("mailto:"):
            extra = ' target="_blank" rel="noopener noreferrer"'
        extra += "".join(f' {esc(k.replace("_", "-"))}="{esc(v)}"' for k, v in attrs.items())
        return f'<a class="{esc(klass)}" href="{esc(href)}"{extra}>{esc(label)}</a>'

    def download(self, filename, label, klass="button"):
        return f'<a class="{esc(klass)}" href="{esc(self.rel("files/" + filename))}" download>{esc(label)}</a>'

    def tags(self, items):
        return '<div class="tag-list">' + "".join(f'<span class="tag">{esc(x)}</span>' for x in items) + "</div>"

    def img(self, filename, alt, eager=False, klass=""):
        width, height = DIMENSIONS[filename]
        return f'<img src="{esc(self.rel("assets/" + filename))}" alt="{esc(alt)}" width="{width}" height="{height}" loading="{"eager" if eager else "lazy"}" decoding="async" class="{esc(klass)}">'

    def section_head(self, label, title, intro="", action=""):
        return ('<div class="section-head"><div><p class="section-label">' + esc(label) + '</p>'
                + '<h2 class="section-title">' + esc(title) + '</h2>'
                + (f'<p class="section-intro">{esc(intro)}</p>' if intro else "") + '</div>' + action + '</div>')

    def page_hero(self, label, title, lead, actions=""):
        crumbs = self.link("", self.l("home"), klass="") + '<span aria-hidden="true">/</span><span>' + esc(label) + '</span>'
        return f'<section class="page-hero"><div class="container"><nav class="breadcrumbs" aria-label="{esc(self.w("Breadcrumb", "面包屑导航"))}">{crumbs}</nav><p class="eyebrow">{esc(label)}</p><h1 class="page-title">{esc(title)}</h1><p class="page-lead">{esc(lead)}</p>{actions}</div></section>'

    def card(self, title, body, number="", tags=None, link=""):
        return '<article class="card">' + (f'<span class="card-number" aria-hidden="true">{esc(number)}</span>' if number else '') + f'<h3 class="card-title">{esc(title)}</h3><p>{esc(body)}</p>' + (self.tags(tags) if tags else '') + link + '</article>'

    def project_card(self, project, index=0, filterable=False):
        category = project['category']
        cat_label = self.l("research_cat" if category == "research" else "software_cat")
        meta = self.t(project["subtitle"])
        attrs = ""
        if filterable:
            search = ' '.join([project['id'], self.t(project['title']), meta, self.t(project['summary']), *project['stack']])
            attrs = f' data-filter-item data-category="{esc(category)}" data-status="{esc(project["status"])}" data-search="{esc(search)}"'
        visual = ""
        if project.get('image'):
            visual = '<div class="project-image">' + self.img(project['image'], self.w('The academic facial-expression recognition application interface', '本科表情识别应用的界面截图')) + '</div>'
        else:
            glyph = {"histology-segmentation": "01 / VISION", "emotion-recognition": "02 / VISION", "marginloom": "03 / EVIDENCE", "investment-financial-management": "04 / SYSTEMS"}.get(project['id'], f'{index + 1:02d} / SOFTWARE')
            visual = f'<div class="project-visual" aria-hidden="true"><span class="project-glyph">{esc(glyph)}</span><span>{esc(cat_label)}</span></div>'
        actions = self.link("projects/"+project["id"]+"/", self.l("view_project") + " →", klass="project-link")
        if project.get('live_url'):
            actions = '<div class="actions">' + self.link(project['live_url'], self.w('Launch application ↗', '进入应用 ↗'), 'button primary', external=True) + actions + '</div>'
        return f'<article class="project-card"{attrs}>{visual}<div class="project-body"><p class="project-meta">{esc(meta)}</p><h3 class="card-title">{self.link("projects/"+project["id"]+"/", self.t(project["title"]), klass="")}</h3><p>{esc(self.t(project["summary"]))}</p><p class="project-meta">{esc(self.t(project["status_label"]))}</p>{self.tags(project["stack"][:4])}{actions}</div></article>'

    def timeline(self, items):
        return '<ol class="timeline">' + ''.join(f'<li class="timeline-item"><p class="timeline-date">{esc(self.t(item["date"]))}</p><div class="timeline-content"><h3>{esc(self.t(item["title"]))}</h3><p>{esc(self.t(item["body"]))}</p></div></li>' for item in items) + '</ol>'

    def navigation(self):
        p = self.b.profile
        items = [("about/", "about"), ("research/", "research"), ("projects/", "projects"), ("education/", "education"), ("coursework/", "coursework"), ("contact/", "contact")]
        nav = ""
        for route, key in items:
            active = self.route == route or (route in ("projects/", "education/") and self.route.startswith(route))
            attrs = ' aria-current="page"' if active else ''
            nav += f'<a href="{esc(self.url(route))}"{attrs}>{esc(self.l(key))}</a>'
        otherlang = "zh" if self.lang == "en" else "en"
        otherroute = ("zh/" if otherlang == "zh" else "") + self.route
        other_href = self.rel(otherroute)
        search_items = []
        for route, key in ROUTES:
            if key in ("notfound", "privacy"):
                continue
            search_items.append((route, self.l(key), self.w("Page", "页面"), key))
        for item in p['projects']:
            search_items.append((f'projects/{item["id"]}/', self.t(item['title']), self.t(item['status_label']), ' '.join(item['stack'])))
        entries = ''.join(f'<li data-search-entry data-search="{esc(key)}"><a href="{esc(self.url(route))}"><strong>{esc(title)}</strong><span>{esc(subtitle)}</span></a></li>' for route, title, subtitle, key in search_items)
        return f'''<a class="skip-link" href="#main">{esc(self.l('skip'))}</a>
<header class="site-header"><div class="container nav">
<a class="brand" href="{esc(self.url())}" aria-label="{esc(self.w('Zhongjie Huang — home', '黄中杰 — 首页'))}"><span class="brand-mark" aria-hidden="true">ZH<span>.</span></span><span class="brand-name">Zhongjie Huang</span></a>
<nav class="nav-links" id="primary-nav" data-nav-links aria-label="{esc(self.l('nav'))}">{nav}</nav>
<div class="nav-actions"><button class="icon-button search-button js-only" type="button" data-command-open aria-label="{esc(self.l('search'))}"><span aria-hidden="true">⌕</span></button><button class="icon-button theme-button js-only" type="button" data-theme-toggle aria-label="{esc(self.l('theme'))}"><span aria-hidden="true">◐</span></button><a class="language-link" href="{esc(other_href)}" hreflang="{'zh-CN' if otherlang == 'zh' else 'en-GB'}" lang="{'zh-CN' if otherlang == 'zh' else 'en-GB'}">{esc(self.l('language_switch'))}</a><button class="icon-button menu-button js-only" type="button" data-menu-button aria-controls="primary-nav" aria-expanded="false" aria-label="{esc(self.l('menu'))}"><span aria-hidden="true">☰</span></button></div>
</div></header>
<dialog class="command-dialog" data-command-dialog aria-label="{esc(self.l('search'))}"><div class="command-head"><label class="sr-only" for="command-input">{esc(self.l('search'))}</label><input id="command-input" type="search" data-command-input placeholder="{esc(self.l('search_placeholder'))}" autocomplete="off"><button class="icon-button" type="button" data-command-close aria-label="{esc(self.l('close'))}">×</button></div><p class="sr-only" data-command-status aria-live="polite"></p><ul class="command-list" data-command-list>{entries}</ul><p class="command-empty" data-command-empty hidden>{esc(self.l('no_results'))}</p></dialog>'''

    def footer(self):
        links = [("about/", "about"), ("skills/", "skills"), ("now/", "now"), ("cv/", "cv"), ("insights/research-validation/", "validation"), ("privacy.html", "privacy")]
        contact = self.b.profile['contact']
        return '<footer class="footer"><div class="container"><div class="footer-grid"><div><a class="brand" href="' + esc(self.url()) + '">Zhongjie Huang</a><p>' + esc(self.w('Research, software and the evidence behind them.', '研究、软件，以及支撑它们的证据。')) + '</p></div><nav class="footer-links" aria-label="' + esc(self.w('Footer navigation', '页脚导航')) + '">' + ''.join(self.link(route, self.l(key), klass='') for route, key in links) + '</nav><div class="footer-links">' + self.link('mailto:' + contact['email'], self.l('email'), klass='', external=True) + self.link(contact['github'], 'GitHub', klass='', external=True) + self.link(contact['linkedin'], 'LinkedIn', klass='', external=True) + '</div></div><p class="footer-note">' + esc(self.l('updated')) + ' · © 2026 Zhongjie Huang · ' + esc(self.w('English / 中文', '中文 / English')) + '</p></div></footer>'

    def render(self, title, description, body, cv=False):
        base = self.b.config['base_url']
        canonical = base + '/' + self.prefix + self.route
        en_url, zh_url = base + '/' + self.route, base + '/zh/' + self.route
        person = self.b.profile['person']
        profile = self.b.profile
        structured = {
            '@context': 'https://schema.org', '@type': 'ProfilePage',
            'name': title, 'url': canonical, 'dateModified': self.b.config['updated'],
            'inLanguage': 'zh-CN' if self.lang == 'zh' else 'en-GB',
            'mainEntity': {
                '@type': 'Person', '@id': base + '/#person', 'name': 'Zhongjie Huang',
                'alternateName': '黄中杰', 'url': base + '/',
                'description': self.t(person['summary']),
                'image': base + '/assets/zhongjie-huang-720.jpg',
                'sameAs': [profile['contact']['github'], profile['contact']['linkedin']],
                'alumniOf': {'@type': 'CollegeOrUniversity', 'name': 'University of Sheffield'},
                'knowsAbout': ['Computer vision', 'Machine learning evaluation', 'Software engineering']
            }
        }
        structured_json = json.dumps(structured, ensure_ascii=False).replace('<', '\\u003c')
        extra = ''
        if self.route == '404.html':
            extra += '<meta name="robots" content="noindex,follow">'
        classes = 'cv-page' if cv else ''
        return f'''<!doctype html>
<html lang="{'zh-CN' if self.lang == 'zh' else 'en-GB'}" data-theme="light"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">{extra}
<title>{esc(title)}</title><meta name="description" content="{esc(description)}"><meta name="portfolio-version" content="{esc(self.b.config['version'])}">
<link rel="canonical" href="{esc(canonical)}"><link rel="alternate" hreflang="en-GB" href="{esc(en_url)}"><link rel="alternate" hreflang="zh-CN" href="{esc(zh_url)}"><link rel="alternate" hreflang="x-default" href="{esc(en_url)}">
<meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}"><meta property="og:locale" content="{'zh_CN' if self.lang == 'zh' else 'en_GB'}"><meta property="og:image" content="{esc(base + '/assets/zhongjie-huang-720.jpg')}"><meta property="og:image:alt" content="Zhongjie Huang"><meta name="twitter:card" content="summary"><meta name="theme-color" content="#173f43">
<link rel="icon" href="{esc(self.rel('assets/favicon.svg'))}" type="image/svg+xml"><link rel="manifest" href="{esc(self.rel('manifest.webmanifest'))}"><link rel="stylesheet" href="{esc(self.rel('assets/' + self.b.css_name))}"><script defer src="{esc(self.rel('assets/' + self.b.js_name))}"></script><script type="application/ld+json">{structured_json}</script>
</head><body class="{classes}" data-page="{esc(self.route or 'home')}" data-lang="{self.lang}">
{self.navigation()}<main id="main">{body}</main>{self.footer()}
</body></html>'''


class Builder:
    def __init__(self, base_url=None):
        self.config = load_json(ROOT / 'content/site.json')
        self.profile = load_json(ROOT / 'content/profile.json')
        self.coursework = load_json(ROOT / 'content/coursework.json')
        if base_url:
            self.config['base_url'] = base_url.rstrip('/')
        origin = urlsplit(self.config['base_url'])
        if origin.scheme not in ('http', 'https') or not origin.netloc or origin.query or origin.fragment or origin.username or origin.password:
            raise ValueError('base_url must be an absolute HTTP(S) URL without credentials, query or fragment')
        if '..' in origin.path.split('/'):
            raise ValueError('base_url must not contain parent path segments')
        self.config['base_url'] = self.config['base_url'].rstrip('/')
        date.fromisoformat(self.config['updated'])
        if self.profile['updated'] != self.config['updated']:
            raise ValueError('Profile and site review dates must agree')
        self.projects = {p['id']: p for p in self.profile['projects']}
        if len(self.projects) != len(self.profile['projects']):
            raise ValueError('Project IDs must be unique')
        self.site = ROOT / 'site'
        self.css_name = self.asset_name('styles.css')
        self.js_name = self.asset_name('app.js')

    def asset_name(self, filename):
        path = ROOT / 'static/assets' / filename
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        return f'{path.stem}.{digest}{path.suffix}'

    def write(self, path, content):
        out = self.site / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding='utf-8')

    def home(self, p):
        data = self.profile
        person = data['person']
        email = data['contact']['email']
        portrait = p.img('zhongjie-huang-720.webp', 'Zhongjie Huang', eager=True)
        hero = f'''<section class="hero"><div class="container hero-grid"><div class="hero-copy"><p class="eyebrow">{esc(p.t(person['discipline']))} / {esc(p.t(person['location']))}</p><h1 class="hero-title">{esc(p.t(person['name']))}<span aria-hidden="true">.</span></h1><p class="hero-lead">{esc(p.t(person['headline']))}</p><p>{esc(p.t(person['summary']))}</p><div class="hero-meta"><span>{esc(p.w('Computer vision', '计算机视觉'))}</span><span>{esc(p.w('Reliable evaluation', '可靠评估'))}</span><span>{esc(p.w('Software systems', '软件系统'))}</span></div><div class="actions">{p.link('projects/', p.l('all_projects'), 'button primary')}{p.link('cv/', p.l('view_cv'), 'button')}</div></div><figure class="hero-portrait"><picture><source type="image/webp" srcset="{esc(p.rel('assets/zhongjie-huang-480.webp'))} 480w, {esc(p.rel('assets/zhongjie-huang-720.webp'))} 720w, {esc(p.rel('assets/zhongjie-huang-960.webp'))} 960w" sizes="(max-width: 760px) 80vw, 360px">{portrait}</picture><figcaption class="portrait-caption"><span>{esc(p.w('Zhongjie Huang / 黄中杰', '黄中杰 / Zhongjie Huang'))}</span><span>{esc(p.w('Research + engineering', '研究 + 工程'))}</span></figcaption></figure></div></section>'''
        status = '<div class="container"><div class="status-strip"><span class="status-dot" aria-hidden="true"></span><p>' + esc(p.t(data['current']['status_short'])) + '</p>' + p.link('now/', p.l('now') + ' →') + '</div></div>'
        intro_cards = ''.join(p.card(p.t(x['title']), p.t(x['description']), f'{i+1:02d}', link=p.link(x['path'], p.t(x['basis']) + ' →')) for i, x in enumerate(data['skills'][:3]))
        about = '<section class="section" id="about"><div class="container">' + p.section_head(p.l('about'), p.w('From model experiments to usable systems.', '从模型实验到可使用的系统。'), p.w('Academic work and practical software, with an emphasis on careful interpretation.', '通过学术研究与实际软件项目，关注实现过程和结果的审慎解读。'), p.link('about/', p.l('more') + ' →')) + '<div class="grid three">' + intro_cards + '</div></div></section>'
        msc = self.projects['histology-segmentation']
        steps = [p.w('Histology images', '组织学图像'), p.w('Four segmentation pipelines', '四条分割流程'), p.w('Cell measurements', '细胞测量'), p.w('Downstream evaluation', '下游评估')]
        flow = '<ol class="method-flow">' + ''.join(f'<li class="method-step"><span class="method-number" aria-hidden="true">{i+1:02d}</span><span>{esc(label)}</span></li>' for i, label in enumerate(steps)) + '</ol>'
        featured = '<section class="section alt" id="projects"><div class="container">' + p.section_head(p.l('projects'), p.w('Selected work.', '精选项目。'), p.w('The question, the implementation and the evidence for each project.', '逐项呈现研究问题、实现过程与已有证据。'), p.link('projects/', p.l('all_projects') + ' →'))
        featured += '<article class="feature-project"><div class="feature-copy"><p class="eyebrow">' + esc(p.t(msc['subtitle'])) + '</p><h3>' + esc(p.t(msc['title'])) + '</h3><p>' + esc(p.t(msc['summary'])) + '</p><p class="muted">' + esc(p.t(msc['status_label'])) + '</p>' + p.tags(msc['stack'][:4]) + p.link('projects/histology-segmentation/', p.l('view_project') + ' →', 'text-link') + '</div><div class="feature-visual">' + flow + '<p class="muted">' + esc(p.w('Segmentation quality, measurement reliability and predictive utility are separate questions.', '分割质量、测量可靠性和预测效用，是三个需要分别回答的问题。')) + '</p></div></article>'
        selected = [self.projects[key] for key in ('emotion-recognition', 'marginloom', 'investment-financial-management') if key in self.projects]
        featured += '<div class="grid three">' + ''.join(p.project_card(x, i+1) for i, x in enumerate(selected)) + '</div></div></section>'
        training = '<section class="section" id="skills"><div class="container">' + p.section_head(p.l('education'), p.w('A foundation in AI and computer science.', '人工智能与计算机科学的系统训练。'), '', p.link('education/', p.w('Academic background →', '了解教育背景 →'))) + '<div class="grid two">'
        for edu in data['education']:
            training += p.card(p.t(edu['degree']), p.t(edu['description']), tags=[p.t(edu['period']), p.t(edu['status_label'])], link=p.link('coursework/?programme=' + edu['id'], p.l('all_modules') + ' →'))
        training += '</div><div class="actions">' + p.link('skills/', p.w('See skills and supporting work →', '查看技能与项目依据 →')) + '</div></div></section>'
        current = '<section class="section alt"><div class="container">' + p.section_head(p.l('now'), p.w('The next chapter.', '下一阶段。'), p.w('A dated view of current study, applications and direction.', '以明确日期记录当前学习、申请进展和研究方向。'), p.link('now/', p.w('Read the current update →', '查看最新近况 →'))) + p.timeline(data['timeline'][:2]) + '</div></section>'
        contact = '<section class="section" id="contact"><div class="container">' + p.section_head(p.l('contact'), p.w('Let’s discuss a worthwhile problem.', '一起讨论值得解决的问题。'), p.t(data['contact']['message'])) + '<div class="actions">' + p.link('mailto:' + email, email, 'button primary', external=True) + p.link('contact/', p.w('Contact details', '联系方式'), 'button') + '</div></div></section>'
        return hero + status + about + featured + training + current + contact

    def about(self, p):
        person = self.profile['person']
        body = p.page_hero(p.l('about'), p.w('A profile built around the work.', '通过实际工作认识我。'), p.t(person['summary']))
        facts = [
            (p.w('Name', '姓名'), p.w('Zhongjie Huang / 黄中杰', '黄中杰 / Zhongjie Huang')),
            (p.w('Based in', '所在地'), p.t(person['location'])),
            (p.w('Academic background', '学术背景'), 'University of Sheffield'),
            (p.w('Current stage', '当前阶段'), p.t(self.profile['education'][0]['status_label'])),
            (p.w('Focus', '关注方向'), p.w('Computer vision · Evaluation · Software', '计算机视觉 · 评估 · 软件'))
        ]
        fact_html = '<dl class="fact-list">' + ''.join(f'<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>' for k, v in facts) + '</dl>'
        body += '<section class="section"><div class="container content-layout"><div class="content-main prose">' + paragraphs(p.t(person['biography'])) + '<div class="actions">' + p.link('cv/', p.l('view_cv'), 'button primary') + p.download('zhongjie-huang-profile.json', p.l('profile_download')) + '</div></div><aside class="side-note">' + fact_html + '</aside></div></section>'
        practices = [
            (p.w('Define the problem', '明确问题'), p.w('Start with a concrete question, the data available and the decision a result might support.', '从具体问题、可用数据及结果可能支持的决策出发。')),
            (p.w('Make the workflow inspectable', '让流程可以检查'), p.w('Keep assumptions, transformations and evaluation choices visible in code and documentation.', '通过代码与文档呈现假设、数据变换和评估选择。')),
            (p.w('Explain the boundary', '说明边界'), p.w('Distinguish what was built, what was measured and what still needs evidence.', '区分已实现的功能、已测量的结果和仍需要补充证据的部分。'))
        ]
        body += '<section class="section alt"><div class="container">' + p.section_head(p.w('Working approach', '工作方式'), p.w('Build, examine, explain.', '实现、检查、解释。')) + '<div class="grid three">' + ''.join(p.card(a, b, f'{i+1:02d}') for i, (a, b) in enumerate(practices)) + '</div></div></section>'
        body += '<section class="section"><div class="container">' + p.section_head(p.w('Communication', '交流'), p.w('Across disciplines and languages.', '跨越学科与语言。'), p.w('Technical reporting, project explanation and collaborative discussion are part of the work.', '技术报告、项目讲解与协作讨论，也是工作的一部分。')) + bullet_list(p.t(person['languages'])) + '<div class="actions">' + p.link('skills/', p.w('Skills and evidence →', '技能与证据 →')) + p.link('now/', p.w('Current direction →', '当前方向 →')) + '</div></div></section>'
        return body

    def education(self, p):
        body = p.page_hero(p.l('education'), p.w('Academic background, clearly stated.', '清晰、准确的教育背景。'), p.w('Degree study, project work and the distinction between a completed award and a pending result.', '完整呈现学位学习与项目实践，并区分已授予学位和仍待确认的结果。'))
        body += '<section class="section"><div class="container">'
        for edu in self.profile['education']:
            body += '<article class="card"><p class="eyebrow">' + esc(p.t(edu['institution'])) + ' · ' + esc(p.t(edu['period'])) + '</p><h2>' + esc(p.t(edu['degree'])) + '</h2><p><strong>' + esc(p.t(edu['status_label'])) + '</strong></p><p>' + esc(p.t(edu['description'])) + '</p><p class="muted">' + esc(p.t(edu['note'])) + '</p><div class="actions">' + p.link('projects/' + edu['project'] + '/', p.w('Dissertation project →', '查看毕业项目 →')) + p.link('coursework/?programme=' + edu['id'], p.w('Related coursework →', '相关课程 →')) + '</div></article>'
        body += '</div></section><section class="section alt"><div class="container">' + p.section_head(p.l('coursework'), p.w('32 modules. A map of the training.', '32 门课程，呈现学习脉络。'), p.w('Eight postgraduate modules and 24 undergraduate modules retained from the supplied records. The catalogue describes subject exposure rather than a graded transcript.', '保留资料中的 8 门研究生课程与 24 门本科课程，以主题说明学习经历。')) + '<div class="actions">' + p.link('coursework/', p.l('all_modules'), 'button primary') + p.link('education/degree-credential/', p.l('credential'), 'button') + '</div></div></section>'
        body += '<section class="section"><div class="container">' + p.section_head(p.w('Progression', '经历时间线'), p.w('From undergraduate study to the next research step.', '从本科学习迈向下一阶段研究。')) + p.timeline(self.profile['timeline']) + '</div></section>'
        return body

    def credential(self, p):
        body = p.page_hero(p.l('credential'), p.w('BSc degree certificate.', '本科学位证书。'), p.w('University of Sheffield · BSc Artificial Intelligence and Computer Science · Awarded 1 July 2025.', '谢菲尔德大学 · 人工智能与计算机科学理学学士 · 2025 年 7 月 1 日授予。'))
        href = p.rel('files/degree-certificate.pdf')
        label = p.w('Open original certificate (PDF)', '打开原始学位证书（PDF）')
        body += '<section class="section"><div class="container content-layout"><div class="content-main prose"><h2>' + esc(p.w('Official award', '正式学位')) + '</h2><p>' + esc(p.w('Class Two Division One Honours, commonly described as Upper Second-Class Honours (2:1). The original certificate is preserved from the supplied portfolio.', '学位等级为 Class Two Division One Honours，即二等一荣誉学位（2:1）。此处保留所提供作品集中的原始证书。')) + '</p><div class="actions"><a class="button primary" href="' + esc(href) + '" target="_blank" rel="noopener noreferrer">' + esc(label) + '</a>' + p.link('education/', p.w('Education overview', '教育背景'), 'button') + '</div></div><aside class="side-note"><h2>' + esc(p.w('Other academic records', '其他学术记录')) + '</h2><p>' + esc(p.w('The public site includes this degree certificate. Detailed transcripts and administrative records are not published here.', '网站提供这份学位证书；详细成绩单与行政资料不在此公开。')) + '</p><p>' + esc(p.w('The MSc degree award remains pending in the latest verified information.', '最新核实的资料中，硕士学位授予仍待确认。')) + '</p></aside></div></section>'
        return body

    def skills(self, p):
        body = p.page_hero(p.l('skills'), p.w('Capabilities, linked to evidence.', '用具体依据呈现能力。'), p.w('Projects show applied experience. Coursework shows academic grounding. Each group links to the work behind it.', '项目呈现实践经验，课程呈现学术基础；每组技能都链接到相应依据。'))
        body += '<section class="section"><div class="container"><div class="grid two">'
        for i, item in enumerate(self.profile['skills']):
            body += '<article class="card skill-group"><p class="card-number">' + f'{i+1:02d}' + '</p><h2>' + esc(p.t(item['title'])) + '</h2><p>' + esc(p.t(item['description'])) + '</p>' + p.tags(item['tools']) + '<p class="muted">' + esc(p.t(item['basis'])) + '</p>' + p.link(item['path'], p.w('See supporting work →', '查看支持材料 →')) + '</article>'
        body += '</div></div></section><section class="section alt"><div class="container">' + p.section_head(p.w('Academic breadth', '学术广度'), p.w('Explore the underlying coursework.', '查看支撑这些能力的课程。'), p.w('Search by module code, topic, programme or study level to find the relevant training.', '按课程代码、主题、学位阶段或学习年级查找对应的训练。')) + p.link('coursework/', p.l('all_modules'), 'button primary') + '</div></section>'
        return body

    def projects_page(self, p):
        body = p.page_hero(p.l('projects'), p.w('Research questions. Working software.', '研究问题，软件实践。'), p.w('Four projects, each with its own scope, contribution and evidence. Launch Marginloom or IAFM directly, or read the case studies.', '四个项目，分别说明范围、个人贡献与证据。可直接进入 Marginloom 或 IAFM，也可阅读项目案例。'))
        categories = [('', p.l('all')), ('research', p.l('research_cat')), ('software', p.l('software_cat'))]
        statuses = [('', p.l('all'))]
        seen = set()
        for item in self.profile['projects']:
            if item['status'] not in seen:
                seen.add(item['status'])
                statuses.append((item['status'], p.t(item['status_label'])))
        body += '<section class="section"><div class="container" data-filter-group="projects"><div class="filter-bar js-only">' + self.filter_input(p, 'project-search', p.w('Search projects', '搜索项目'), p.w('Title, tool or topic', '名称、工具或主题')) + self.filter_select(p, 'project-category', 'category', p.w('Area', '方向'), categories) + self.filter_select(p, 'project-status', 'status', p.l('status'), statuses) + '</div>'
        body += '<h2 class="sr-only">' + esc(p.w('Project directory', '项目目录')) + '</h2>' + self.filter_summary(p, len(self.profile['projects']), 'projects')
        body += '<div class="grid two">' + ''.join(p.project_card(item, i, True) for i, item in enumerate(self.profile['projects'])) + '</div><p class="notice" data-filter-empty hidden>' + esc(p.w('No projects match these filters. Try another term or clear the filters.', '没有符合条件的项目，请更换关键词或清除筛选。')) + '</p></div></section>'
        return body

    def project_detail(self, p, item):
        actions = '<div class="actions">' + p.link('projects/', '← ' + p.l('back_projects'), 'button')
        if item.get('live_url'):
            actions += p.link(item['live_url'], p.w('Launch application ↗', '进入应用 ↗'), 'button primary', external=True)
        if item.get('repository'):
            actions += p.link(item['repository'], p.l('source'), 'button', external=True)
        actions += '</div>'
        body = p.page_hero(p.t(item['subtitle']), p.t(item['title']), p.t(item['summary']), actions)
        body += '<section class="section"><div class="container content-layout"><div class="content-main prose">'
        if item.get('original_title'):
            body += '<p class="muted">' + esc(p.w('Dissertation title: ', '论文原题：')) + esc(p.t(item['original_title'])) + '</p>'
        for section in item['sections']:
            body += '<section><h2>' + esc(p.t(section['heading'])) + '</h2>' + paragraphs(p.t(section['body'])) + '</section>'
        body += '</div><aside class="side-note"><dl class="fact-list">'
        for name, value in [(p.l('status'), p.t(item['status_label'])), (p.l('role'), p.t(item['role'])), (p.l('period'), p.t(item['period']))]:
            body += '<div><dt>' + esc(name) + '</dt><dd>' + esc(value) + '</dd></div>'
        body += '</dl><h2>' + esc(p.l('tools')) + '</h2>' + p.tags(item['stack']) + '</aside></div></section>'
        body += '<section class="section alt"><div class="container grid two"><div class="prose"><h2>' + esc(p.l('outputs')) + '</h2>' + bullet_list(p.t(item['outcomes'])) + '</div><div class="prose"><h2>' + esc(p.l('limits')) + '</h2>' + bullet_list(p.t(item['limits'])) + '</div></div></section>'
        body += '<section class="section"><div class="container"><div class="notice"><h2>' + esc(p.l('evidence')) + '</h2><p>' + esc(p.t(item['evidence'])) + '</p>'
        if item.get('repository'):
            body += p.link(item['repository'], p.l('source') + ' ↗', external=True)
        body += '</div><div class="actions">' + p.link('skills/', p.w('Related capabilities →', '相关能力 →')) + p.link('projects/', p.l('all_projects') + ' →') + '</div></div></section>'
        return body

    @staticmethod
    def filter_input(p, identifier, label, placeholder):
        return f'<div class="filter-field"><label for="{esc(identifier)}">{esc(label)}</label><input id="{esc(identifier)}" data-filter-query type="search" placeholder="{esc(placeholder)}" autocomplete="off"></div>'

    @staticmethod
    def filter_select(p, identifier, name, label, options):
        choices = ''.join(f'<option value="{esc(value)}">{esc(label)}</option>' for value, label in options)
        return f'<div class="filter-field"><label for="{esc(identifier)}">{esc(label)}</label><select id="{esc(identifier)}" name="{esc(name)}" data-filter-select>{choices}</select></div>'

    @staticmethod
    def filter_summary(p, count, kind):
        template = p.w('Showing {count} of {total} ' + kind + '.', '显示 {count} / {total} ' + ('门课程' if kind == 'modules' else '个项目'))
        return '<div class="filter-summary"><p data-filter-count data-count-template="' + esc(template) + '" aria-live="polite">' + esc(template.replace('{count}', str(count)).replace('{total}', str(count))) + '</p><button type="button" class="button js-only" data-filter-reset>' + esc(p.w('Clear filters', '清除筛选')) + '</button></div>'

    def coursework_page(self, p):
        body = p.page_hero(p.l('coursework'), p.w('A searchable map of the curriculum.', '可检索的课程知识地图。'), p.w('32 modules from the supplied undergraduate and postgraduate records, grouped by programme, level and subject area.', '依据所提供的本科及研究生资料整理 32 门课程，按学位阶段、年级和主题分类。'))
        area_zh = {'Algorithms': '算法', 'Artificial intelligence': '人工智能', 'Collaboration': '团队协作', 'Computational modelling': '计算建模', 'Cybersecurity': '网络与系统安全', 'Data & statistics': '数据与统计', 'Distributed systems': '分布式系统', 'Foundations': '计算机基础', 'Language technology': '语言技术', 'Machine learning': '机器学习', 'Mobile engineering': '移动开发', 'Professional practice': '专业实践', 'Research project': '研究项目', 'Responsible computing': '负责任的计算', 'Robotics': '机器人', 'Scalable computing': '可扩展计算', 'Software engineering': '软件工程', 'Systems': '计算机系统', 'Theory': '计算理论', 'Web engineering': '网页工程'}
        level_zh = {'Postgraduate': '研究生', 'Year 1': '本科一年级', 'Year 2': '本科二年级', 'Year 3': '本科三年级'}
        areas = sorted({item['area'] for item in self.coursework})
        programmes = [('', p.w('All programmes', '全部学位阶段')), ('msc', p.w('MSc AI', '人工智能硕士课程')), ('bsc', p.w('BSc AI & CS', '人工智能与计算机科学本科'))]
        levels = [('', p.w('All levels', '全部年级'))] + [(x, p.w(x, level_zh[x])) for x in ('Postgraduate', 'Year 1', 'Year 2', 'Year 3')]
        area_choices = [('', p.w('All areas', '全部主题'))] + [(x, p.w(x, area_zh.get(x, x))) for x in areas]
        body += '<section class="section"><div class="container" data-filter-group="coursework"><div class="filter-bar js-only">' + self.filter_input(p, 'module-search', p.w('Search modules', '搜索课程'), p.w('Code, title, topic or skill', '课程代码、名称、主题或技能')) + self.filter_select(p, 'module-programme', 'programme', p.w('Programme', '学位阶段'), programmes) + self.filter_select(p, 'module-level', 'level', p.w('Level', '年级'), levels) + self.filter_select(p, 'module-area', 'area', p.w('Subject area', '主题'), area_choices) + '</div>' + self.filter_summary(p, len(self.coursework), 'modules')
        body += '<div class="grid two">'
        for item in self.coursework:
            programme = p.w('MSc Artificial Intelligence', '人工智能硕士课程') if item['programme'] == 'msc' else p.w('BSc AI & Computer Science', '人工智能与计算机科学本科')
            area = p.w(item['area'], area_zh.get(item['area'], item['area']))
            level = p.w(item['level'], level_zh.get(item['level'], item['level']))
            search = ' '.join([item['code'], item['title']['en'], item['title']['zh'], p.t(item['description']), item['area'], area, level])
            body += f'<article class="card" id="{esc(item["code"].lower())}" data-filter-item data-programme="{esc(item["programme"])}" data-level="{esc(item["level"])}" data-area="{esc(item["area"])}" data-search="{esc(search)}"><p class="card-number">{esc(item["code"])}</p><h2 class="card-title">{esc(p.t(item["title"]))}</h2><p>{esc(p.t(item["description"]))}</p>{p.tags([programme, level, area])}'
            source = item['source']
            if source.startswith('/'):
                body += p.link(source.lstrip('/'), p.w('Related project →', '相关项目 →'))
            else:
                body += p.link(source, p.w('Course reference ↗', '课程参考来源 ↗'), external=True)
            body += '</article>'
        body += '</div><p class="notice" data-filter-empty hidden>' + esc(p.w('No modules match these filters. Try a wider search or clear the filters.', '没有匹配课程，请尝试更宽泛的搜索或清除筛选。')) + '</p><div class="notice"><h2>' + esc(p.w('How to read this catalogue', '如何理解这份课程目录')) + '</h2><p>' + esc(p.w('Descriptions and course references are retained from the supplied portfolio and paraphrase subject coverage. University curricula and page URLs can change. This is a map of academic study, not a current programme specification or a detailed transcript.', '课程描述与参考链接保留自所提供的作品集，用于概括学习主题。大学课程设置和网页地址可能变化；此处展示个人学习经历，不作为现行培养方案或详细成绩单。')) + '</p></div></div></section>'
        return body

    def research(self, p):
        body = p.page_hero(p.l('research'), p.w('Reliable visual AI, examined carefully.', '审慎评估可靠的视觉人工智能。'), p.w('Current interests connect visual segmentation, uncertainty, contextual interpretation and the evidence needed to trust a result.', '当前研究兴趣连接视觉分割、不确定性、语境解读，以及判断结果是否可信所需的证据。'))
        direction = self.profile['current'].get('doctoral_direction')
        if direction:
            body += '<section class="section"><div class="container"><article class="feature-project"><div class="feature-copy"><p class="eyebrow">' + esc(p.t(direction['status_label'])) + '</p><h2>' + esc(p.t(direction['title'])) + '</h2><p>' + esc(p.t(direction['summary'])) + '</p>' + p.link('now/', p.w('Application status and next steps →', '申请状态与下一步 →')) + '</div><div class="feature-visual"><ol class="method-flow">'
            for i, (en, zh) in enumerate([('Data conditions change', '数据条件发生变化'), ('Inspect reliability signals', '检查可靠性信号'), ('Identify uncertain predictions', '识别不确定预测'), ('Evaluate against held-out evidence', '用独立证据进行评估')]):
                body += f'<li class="method-step"><span class="method-number" aria-hidden="true">{i+1:02d}</span><span>{esc(p.w(en, zh))}</span></li>'
            body += '</ol><p class="muted">' + esc(p.w('A proposed research workflow; these are not completed experimental results.', '拟探索的研究流程，目前并非已完成的实验结果。')) + '</p></div></article></div></section>'
        body += '<section class="section alt"><div class="container">' + p.section_head(p.w('Questions and interests', '问题与方向'), p.w('The questions I want to investigate.', '希望继续研究的问题。')) + '<div class="grid two">'
        for i, item in enumerate(self.profile['interests']):
            body += '<article class="card"><p class="card-number">' + f'{i+1:02d}' + '</p><h3>' + esc(p.t(item['title'])) + '</h3><p><strong>' + esc(p.t(item['question'])) + '</strong></p><p>' + esc(p.t(item['body'])) + '</p></article>'
        body += '</div></div></section><section class="section"><div class="container">' + p.section_head(p.w('Existing research work', '已有研究工作'), p.w('Dissertations and practical evidence.', '论文项目与实际证据。'), p.w('Academic project outputs are presented with their actual submission or completion status.', '按真实的提交或完成状态呈现学术项目产出。')) + '<div class="grid two">' + p.project_card(self.projects['histology-segmentation']) + p.project_card(self.projects['emotion-recognition']) + '</div><div class="actions">' + p.link('insights/research-validation/', p.w('Read my validation notes →', '阅读验证方法笔记 →')) + '</div></div></section>'
        return body

    def now(self, p):
        current = self.profile['current']
        body = p.page_hero(p.l('now'), p.w('What I’m working towards.', '当前进展与下一步。'), p.t(current['updated_label']) + ' · ' + p.t(current['status_short']))
        body += '<section class="section"><div class="container"><h2 class="sr-only">' + esc(p.w('Current milestones', '当前里程碑')) + '</h2>' + p.timeline(self.profile['timeline'][:2]) + '<div class="grid two"><section class="card"><h2>' + esc(p.w('Current focus', '当前重点')) + '</h2>' + bullet_list(p.t(current['focus'])) + '</section><section class="card"><h2>' + esc(p.w('Opportunities of interest', '关注的机会')) + '</h2>' + bullet_list(p.t(current['opportunities'])) + '</section></div></div></section>'
        body += '<section class="section alt"><div class="container">' + p.section_head(p.w('Research direction', '研究方向'), p.t(current['doctoral_direction']['title']), p.t(current['doctoral_direction']['summary'])) + '<div class="actions">' + p.link('research/', p.w('Explore research interests', '查看研究兴趣'), 'button primary') + p.link('contact/', p.l('contact'), 'button') + '</div></div></section><section class="section"><div class="container"><p class="muted">' + esc(p.w('This is a dated update, not an automatic feed. Application outcomes and availability should be confirmed directly when relevant.', '此页面是有明确日期的近况记录，不会自动抓取更新。如涉及申请结果或具体时间安排，请直接联系确认。')) + '</p></div></section>'
        return body

    def cv(self, p):
        profile = self.profile
        filename = 'zhongjie-huang-cv-' + p.lang + '.pdf'
        actions = '<div class="actions cv-actions">' + p.download(filename, p.l('download_cv'), 'button primary') + '<button class="button js-only" data-print type="button">' + esc(p.l('print')) + '</button>' + p.download('zhongjie-huang-profile.json', p.l('profile_download')) + '</div>'
        body = '<section class="section"><article class="container"><header class="cv-header"><p class="eyebrow">' + esc(p.w('Research & engineering CV', '研究与工程简历')) + '</p><h1>' + esc(p.t(profile['person']['name'])) + '</h1><p>' + esc(p.t(profile['person']['discipline'])) + ' · ' + esc(p.t(profile['person']['location'])) + '</p><div class="footer-links">' + p.link('mailto:' + profile['contact']['email'], profile['contact']['email'], klass='', external=True) + p.link(profile['contact']['github'], 'GitHub', klass='', external=True) + p.link(profile['contact']['linkedin'], 'LinkedIn', klass='', external=True) + '</div><p class="muted">' + esc(p.t(profile['current']['updated_label'])) + '</p>' + actions + '</header>'
        body += '<section class="cv-section"><h2>' + esc(p.w('Profile', '个人简介')) + '</h2><p>' + esc(p.t(profile['person']['summary'])) + '</p></section><section class="cv-section"><h2>' + esc(p.l('education')) + '</h2>'
        for item in profile['education']:
            body += '<div class="cv-entry"><h3>' + esc(p.t(item['degree'])) + '</h3><p>' + esc(p.t(item['institution'])) + ' · ' + esc(p.t(item['period'])) + '</p><p><strong>' + esc(p.t(item['status_label'])) + '</strong></p><p>' + esc(p.t(item['description'])) + '</p></div>'
        body += '</section><section class="cv-section"><h2>' + esc(p.w('Research & engineering projects', '研究与工程项目')) + '</h2>'
        for item in profile['projects']:
            body += '<div class="cv-entry"><h3>' + p.link('projects/' + item['id'] + '/', p.t(item['title']), klass='') + '</h3><p class="muted">' + esc(p.t(item['period'])) + ' · ' + esc(p.t(item['status_label'])) + ' · ' + esc(p.t(item['role'])) + '</p><p>' + esc(p.t(item['summary'])) + '</p>' + bullet_list(p.t(item['outcomes'])[:2]) + '<p class="muted">' + esc(' / '.join(item['stack'][:6])) + '</p></div>'
        body += '</section><section class="cv-section"><h2>' + esc(p.w('Skills and academic grounding', '技能与学术基础')) + '</h2>'
        for item in profile['skills']:
            body += '<p><strong>' + esc(p.t(item['title'])) + '</strong> — ' + esc(', '.join(item['tools'])) + '. ' + esc(p.t(item['basis'])) + '.</p>'
        body += '</section><section class="cv-section"><h2>' + esc(p.w('Research direction & communication', '研究方向与交流')) + '</h2><p>' + esc(p.t(profile['current']['doctoral_direction']['summary'])) + '</p>' + bullet_list(p.t(profile['person']['languages'])) + '</section></article></section>'
        return body

    def contact(self, p):
        contact = self.profile['contact']
        body = p.page_hero(p.l('contact'), p.w('Start a conversation.', '开始交流。'), p.t(contact['message']))
        body += '<section class="section"><div class="container content-layout"><div class="content-main"><article class="card"><p class="eyebrow">' + esc(p.w('Professional & academic contact', '职业与学术联系')) + '</p><h2>' + esc(p.l('email')) + '</h2><p>' + p.link('mailto:' + contact['email'], contact['email'], klass='text-link', external=True) + '</p><div class="actions">' + p.link('mailto:' + contact['email'], p.w('Write an email', '撰写邮件'), 'button primary', external=True) + '<button type="button" class="button js-only" data-copy="' + esc(contact['email']) + '" data-copied="' + esc(p.l('copied')) + '">' + esc(p.l('copy')) + '</button></div><p data-copy-status role="status" aria-live="polite"></p></article><div class="grid two">' + p.card('GitHub', p.w('Public source code and research software prototypes.', '公开源码与研究软件原型。'), link=p.link(contact['github'], p.w('Open GitHub ↗', '打开 GitHub ↗'), external=True)) + p.card('LinkedIn', p.w('Professional background and a place to connect.', '职业背景与建立联系的入口。'), link=p.link(contact['linkedin'], p.w('Open LinkedIn ↗', '打开 LinkedIn ↗'), external=True)) + '</div></div><aside class="side-note"><h2>' + esc(p.w('Helpful context', '便于沟通的信息')) + '</h2>' + bullet_list(p.w(['A short description of the research topic or role.', 'The organisation, project and any useful background links.', 'Any relevant timeline and what you would like to discuss.'], ['研究主题或岗位的简要说明。', '机构、项目名称及相关背景链接。', '相关时间安排，以及希望讨论的具体事项。'])) + '<p>' + esc(p.w('A current CV and detailed project pages are available here.', '可在本站查看最新简历及详细项目页面。')) + '</p>' + p.link('cv/', p.l('view_cv') + ' →') + '</aside></div></section>'
        return body

    def validation(self, p):
        body = p.page_hero(p.l('validation'), p.w('How I examine model evidence.', '如何检查模型证据。'), p.w('A practical framework for distinguishing a model score from evidence that supports an intended use.', '用实用的检查框架，区分一个模型分数与能够支持实际用途的证据。'))
        notes = [
            ('Data and independence', '数据与独立性', 'What produced each observation? Which samples share a person, source, time period or collection process? Decide what must be kept separate before choosing a split.', '每条观测如何产生？哪些样本共享同一人、来源、时间段或采集过程？先明确哪些数据必须分开，再选择划分方式。', 'https://scikit-learn.org/stable/modules/cross_validation.html', 'scikit-learn: cross-validation'),
            ('A fair comparison', '公平的比较', 'Choose a baseline, isolate the change being tested and keep final evaluation separate from model and preprocessing choices. Fit learned transformations on the appropriate training data.', '选择基线、明确待比较的改变，并将最终评估与模型及预处理选择分开。需要学习的变换应在适当的训练数据上拟合。', 'https://scikit-learn.org/stable/common_pitfalls.html', 'scikit-learn: common pitfalls'),
            ('Useful measures', '有意义的指标', 'Read aggregate scores alongside class-level errors, uncertainty and the cost of mistakes. Ask whether the metric actually represents the question the system is intended to answer.', '将整体分数与类别错误、不确定性及错误代价共同解读，并判断指标是否对应系统实际要回答的问题。', 'https://scikit-learn.org/stable/modules/model_evaluation.html', 'scikit-learn: model evaluation'),
            ('Transfer and scope', '迁移与范围', 'Check performance under relevant changes in data conditions. A good internal result does not by itself establish performance in a new environment; deployment claims require additional evidence.', '检查数据条件发生相关变化时的表现。内部结果良好，并不能单独证明新环境中的表现；部署层面的判断还需要额外证据。', 'https://proceedings.mlr.press/v139/koh21a.html', 'WILDS: in-the-wild distribution shifts (ICML 2021)')
        ]
        body += '<section class="section"><div class="container"><div class="grid two">'
        for i, (en, zh, en_body, zh_body, link, ref) in enumerate(notes):
            body += '<article class="card"><p class="card-number">' + f'{i+1:02d}' + '</p><h2>' + esc(p.w(en, zh)) + '</h2><p>' + esc(p.w(en_body, zh_body)) + '</p>' + p.link(link, ref + ' ↗', external=True) + '</article>'
        body += '</div></div></section><section class="section alt"><div class="container">' + p.section_head(p.w('From the projects', '从项目中得到的认识'), p.w('Different outputs need different evidence.', '不同产出，需要不同证据。')) + '<div class="grid two">' + p.card(p.w('Visible expression is not internal emotion', '可见表情不等于内在情绪'), p.w('A facial-expression classifier learns dataset labels. Claims about a person’s internal state need a different evidential basis.', '表情分类器学习的是数据集标签。关于一个人内在状态的判断，需要不同的证据基础。'), link=p.link('projects/emotion-recognition/', p.l('view_project') + ' →')) + p.card(p.w('Segmentation quality is not downstream value', '分割质量不等于下游价值'), p.w('The MSc work separates boundary quality, cell measurements and prediction. Improvement in one does not automatically establish improvement in another.', '硕士研究分别讨论边界质量、细胞测量和预测表现。其中一项改善，不会自动证明另一项也改善。'), link=p.link('projects/histology-segmentation/', p.l('view_project') + ' →')) + '</div></div></section>'
        return body

    def privacy(self, p):
        body = p.page_hero(p.l('privacy'), p.w('A small, transparent public website.', '清晰透明的个人公开网站。'), p.w('What this site stores, what its links do and which materials are made public.', '说明本站保存什么、链接如何工作，以及哪些材料可以公开查看。'))
        sections = [
            ('Local preferences', '本地偏好', 'The theme preference is stored in your browser when storage is available. Course and project filters can appear in the current page URL so a view can be shared. This build contains no analytics scripts, advertising trackers, account system or contact-form backend.', '浏览器存储可用时，网站会在本地保存主题偏好。课程与项目筛选可以出现在当前页面网址中，便于分享。本版本不包含分析脚本、广告追踪、账号系统或联系表单后端。'),
            ('Email and external links', '邮件与外部链接', 'Email links open your chosen email application. GitHub, LinkedIn and reference links open external sites with their own policies. No contact form submits a message through this website.', '邮件链接打开所选邮件应用。GitHub、LinkedIn 及参考资料链接会进入各自网站，适用相应网站的规则。本站没有通过联系表单代为发送消息的功能。'),
            ('Public materials', '公开材料', 'The professional profile, project summaries, portrait, public CV and original BSc certificate are included. Detailed transcripts, account information, private repositories and raw research data are not part of the public build.', '公开内容包括职业简介、项目摘要、个人照片、公开简历及原始本科学位证书。详细成绩单、账号信息、私有仓库及原始研究数据不在公开构建内。'),
            ('Hosting', '网站托管', 'The site is static. A hosting provider or server administrator may keep ordinary request logs; the contents and retention of those logs depend on the eventual server configuration.', '网站采用静态页面。托管提供方或服务器管理员可能保留常规请求日志；具体记录内容和保存期限取决于最终服务器配置。'),
            ('Attribution', '名称与归属', 'University, dataset, framework and software names identify the subjects discussed and do not imply endorsement or affiliation. Project status and limitations appear on each case study. Rights in third-party material remain with their owners.', '大学、数据集、框架及软件名称仅用于准确识别所讨论的对象，不表示背书或隶属关系。各案例说明项目状态与局限；第三方材料的权利属于其相应所有者。')
        ]
        body += '<section class="section"><div class="container prose">' + ''.join('<section><h2>' + esc(p.w(en, zh)) + '</h2><p>' + esc(p.w(text_en, text_zh)) + '</p></section>' for en, zh, text_en, text_zh in sections) + '<p>' + esc(p.l('updated')) + '</p>' + p.link('contact/', p.w('Contact about this website →', '就本站内容联系 →')) + '</div></section>'
        return body

    def notfound(self, p):
        body = p.page_hero('404', p.w('This page could not be found.', '没有找到这个页面。'), p.w('The address may have changed. Start from the homepage or explore the project directory.', '页面地址可能已变化，可以返回首页或浏览项目目录。'))
        return body + '<section class="section"><div class="container actions">' + p.link('', p.l('home'), 'button primary') + p.link('projects/', p.l('projects'), 'button') + p.link('contact/', p.l('contact'), 'button') + '</div></section>'

    def build(self):
        if self.site.is_symlink():
            raise ValueError('Refusing to replace a symlinked site directory')
        if self.site.exists():
            shutil.rmtree(self.site)
        shutil.copytree(ROOT / 'static', self.site)
        for source, hashed in [('styles.css', self.css_name), ('app.js', self.js_name)]:
            (self.site / 'assets' / source).rename(self.site / 'assets' / hashed)
        # Public exports only: profile.json deliberately contains no private source identifiers.
        self.write('files/zhongjie-huang-profile.json', json.dumps(self.profile, ensure_ascii=False, indent=2) + '\n')
        self.write('files/coursework.json', json.dumps(self.coursework, ensure_ascii=False, indent=2) + '\n')
        pages = []
        renderers = {'home': self.home, 'about': self.about, 'education': self.education, 'credential': self.credential, 'skills': self.skills, 'projects': self.projects_page, 'coursework': self.coursework_page, 'research': self.research, 'now': self.now, 'cv': self.cv, 'contact': self.contact, 'validation': self.validation, 'privacy': self.privacy, 'notfound': self.notfound}
        for lang in ('en', 'zh'):
            for route, key in ROUTES:
                page = Page(self, lang, route)
                title = ('Zhongjie Huang | ' + page.t(self.profile['person']['discipline'])) if key == 'home' else page.l(key) + ' | Zhongjie Huang'
                descriptions = {
                    'home': page.t(self.config['description']),
                    'about': page.t(self.profile['person']['summary']),
                    'research': page.t(self.profile['current']['doctoral_direction']['summary']),
                    'now': page.t(self.profile['current']['status_short']),
                    'contact': page.t(self.profile['contact']['message']),
                    'education': page.w('University of Sheffield education, the awarded BSc, submitted MSc dissertation and current academic status.', '谢菲尔德大学教育经历、已授予的本科学位、已提交的硕士论文及当前学术状态。'),
                    'credential': page.w('The original BSc degree certificate: Artificial Intelligence and Computer Science, University of Sheffield, awarded 1 July 2025.', '原始本科学位证书：谢菲尔德大学人工智能与计算机科学，2025 年 7 月 1 日授予。'),
                    'skills': page.w('Research and engineering capabilities linked to projects, practical outputs and coursework.', '研究与工程能力，与实际项目、产出和课程学习相互对应。'),
                    'projects': page.w('Six academic and software projects with clear contributions, project status and evidence boundaries.', '六个学术与软件项目，说明个人贡献、项目状态及证据边界。'),
                    'coursework': page.w('Search 32 undergraduate and postgraduate modules by programme, level, topic or skill.', '按学位阶段、年级、主题或技能搜索 32 门本科及研究生课程。'),
                    'cv': page.w('A current public research and engineering CV with printable and PDF versions.', '最新公开研究与工程简历，提供可打印页面及 PDF 版本。'),
                    'validation': page.w('Practical notes on data independence, fair comparison, useful metrics and evaluation under shift.', '关于数据独立性、公平比较、有意义的指标及分布变化评估的实用笔记。'),
                    'privacy': page.w('Local preferences, public materials, email links and privacy information for this static site.', '本站本地偏好、公开材料、邮件链接及静态网站隐私说明。'),
                    'notfound': page.w('The requested page is unavailable. Return to Zhongjie Huang’s portfolio.', '请求的页面不可用，请返回黄中杰的作品集。')
                }
                self.write(page.filepath, page.render(title, descriptions[key], renderers[key](page), cv=(key == 'cv')))
                if key != 'notfound':
                    pages.append(self.config['base_url'] + '/' + page.prefix + route)
            for project in self.profile['projects']:
                route = 'projects/' + project['id'] + '/'
                page = Page(self, lang, route)
                self.write(page.filepath, page.render(page.t(project['title']) + ' | Zhongjie Huang', page.t(project['summary']), self.project_detail(page, project)))
                pages.append(self.config['base_url'] + '/' + page.prefix + route)
        namespace = 'http://www.sitemaps.org/schemas/sitemap/0.9'
        ET.register_namespace('', namespace)
        sitemap = ET.Element('{' + namespace + '}urlset')
        for url in sorted(pages):
            node = ET.SubElement(sitemap, '{' + namespace + '}url')
            ET.SubElement(node, '{' + namespace + '}loc').text = url
            ET.SubElement(node, '{' + namespace + '}lastmod').text = self.config['updated']
        self.write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(sitemap, encoding='unicode') + '\n')
        self.write('robots.txt', 'User-agent: *\nAllow: /\nSitemap: ' + self.config['base_url'] + '/sitemap.xml\n')
        manifest = {'name': 'Zhongjie Huang — Research & Engineering', 'short_name': 'Zhongjie Huang', 'start_url': './', 'scope': './', 'display': 'browser', 'background_color': '#f7f6f2', 'theme_color': '#173f43', 'icons': [{'src': 'assets/favicon.svg', 'sizes': 'any', 'type': 'image/svg+xml', 'purpose': 'any'}]}
        self.write('manifest.webmanifest', json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        self.write('VERSION.txt', self.config['version'] + '\n')
        self.write('WEB-INF/web.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<web-app xmlns="http://xmlns.jcp.org/xml/ns/javaee" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://xmlns.jcp.org/xml/ns/javaee http://xmlns.jcp.org/xml/ns/javaee/web-app_3_1.xsd" version="3.1">
  <display-name>Zhongjie Huang Portfolio</display-name>
  <welcome-file-list><welcome-file>index.html</welcome-file></welcome-file-list>
  <error-page><error-code>404</error-code><location>/404.html</location></error-page>
  <mime-mapping><extension>webp</extension><mime-type>image/webp</mime-type></mime-mapping>
  <mime-mapping><extension>webmanifest</extension><mime-type>application/manifest+json</mime-type></mime-mapping>
</web-app>
''')
        self.write('build-info.json', json.dumps({'version': self.config['version'], 'reviewed': self.config['updated'], 'base_url': self.config['base_url'], 'html_pages': len(pages) + 2, 'projects': len(self.profile['projects']), 'modules': len(self.coursework), 'assets': {'css': self.css_name, 'js': self.js_name}}, ensure_ascii=False, indent=2) + '\n')
        print(f'Built {len(pages) + 2} HTML pages, {len(self.profile["projects"])} projects and {len(self.coursework)} modules.')
        print(f'Output: {self.site}')
        print(f'Canonical base URL: {self.config["base_url"]}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', help='Set and persist the canonical base URL before building, including a context path if needed.')
    args = parser.parse_args()
    builder = Builder(args.base_url)
    if args.base_url:
        (ROOT / 'content/site.json').write_text(json.dumps(builder.config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    builder.build()


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as exc:
        print('Build failed: ' + str(exc), file=sys.stderr)
        sys.exit(1)

