# Zhongjie Huang Portfolio · v4.0.5

**Website updated: 19 October 2026. Original academic materials reviewed: 16 October 2026.** A bilingual personal research and engineering portfolio, including editable source, ready-to-host static pages, a Tomcat WAR, and English and Chinese public CVs.

## Start here

| Task | File or directory |
| --- | --- |
| Open the English homepage | `site/index.html` |
| Open the Chinese homepage | `site/zh/index.html` |
| Deploy at the Tomcat root context | `deploy/ROOT.war` |
| Deploy on a static server | Contents of `site/` |
| Read the English and Chinese CVs | `site/files/zhongjie-huang-cv-en.pdf` / `site/files/zhongjie-huang-cv-zh.pdf` |
| Edit public profile content | `content/profile.json` |
| Edit the coursework catalogue | `content/coursework.json` |
| Set the website address or version | `content/site.json` |
| Review validation results | `docs/TEST_REPORT.md` |
| Review content decisions and outstanding confirmations | `docs/RELEASE_REVIEW_ZH.md` |

The live portfolio is at https://www.zhongjiehuang.com. Version 4.0.2 was deployed on 17 October 2026; its homepage, IAFM and Marginloom case studies, and both application entry points returned HTTP 200. Statements about the undeployed v4.0.0 delivery describe historical file-preparation work. Ready-built `site/` files and WARs need no Python, Node.js, database or frontend build environment to serve.

## v4.0.5 · 19 October 2026

Updated OutcomeLab and Marginloom project descriptions, technology lists and both PDF CVs for the deployed Java Web stack. Live-demo and GitHub links are retained. See docs/JAVA_WEB_PROFILE_UPDATE.md.

## v4.0.4 · 19 October 2026

Both two-page PDF CVs now include OutcomeLab, a concise project description, and clickable live-demo and GitHub links.

## v4.0.3 · 19 October 2026

Added OutcomeLab to the bilingual homepage, project directory and detail pages, with live-demo and public-source links. PDF exports were regenerated and checked against the selected-project scope used at that release.

## Included content

- 38 HTML pages: 19 sections or project pages, each in English and Chinese.
- Five project studies: MSc histology research, BSc emotion recognition, OutcomeLab, Marginloom, and IAFM.
- Direct application and source links for [OutcomeLab](https://outcomelab.zhongjiehuang.com), [Marginloom](https://marginloom.zhongjiehuang.com), and [IAFM](https://iafm.zhongjiehuang.com).
- Public source: [OutcomeLab](https://github.com/zhjpersonal83-cell/outcomelab), [Marginloom](https://github.com/zhjpersonal83-cell/marginloom), and [IAFM](https://github.com/zhjpersonal83-cell/Investment_and_Financial_Management).
- An IAFM case study covering ten-currency reporting, paired internal transfers and server-controlled inflation maintenance, without claiming independent security certification.
- Seven evidence-backed skill groups and 32 modules: eight postgraduate and 24 undergraduate modules.
- Separate education, research, skills, current-status, projects, coursework, contact, CV and research-validation sections.
- Bilingual PDF CVs, printable CV pages and a downloadable public-profile JSON file.
- Page-matched language switching, light/dark themes, command search, combined filters and shareable filter URLs.
- The original undergraduate degree certificate and portrait; emotion recognition is presented through text only.

## Education and project status

BSc: University of Sheffield, Artificial Intelligence and Computer Science, September 2021–July 2025; awarded 1 July 2025, Upper Second Class (2:1).

MSc: Artificial Intelligence, 2025–2026; dissertation submitted, final results and degree award pending. Earlier documents contain different expected completion and submission dates, so no unsupported precise award date or classification is asserted.

PhD: Durham interview completed, outcome pending. January 2027 is a proposed entry date. Proposed research is distinguished from completed projects.

## Rebuild

Python 3.9 or later is sufficient. Core building and validation use the standard library.

```bash
python3 build.py
python3 scripts/validate.py
python3 scripts/package.py
```

`build.py` regenerates `site/`. After validation, `package.py` creates matching `deploy/ROOT/`, `deploy/ROOT.war` and a `zhongjie-portfolio.zip` outside the project directory, with `zhongjie-portfolio/` as its top-level folder. Edit source content rather than generated files, which the next build replaces.

### Domain and context path

The canonical base URL is `https://www.zhongjiehuang.com`. For a future subpath deployment:

```bash
python3 build.py --base-url https://www.zhongjiehuang.com/portfolio
python3 scripts/package.py
```

`--base-url` also updates `content/site.json`, then rebuilds canonical URLs, language alternatives, sitemaps, share links and the 404-page base. Regular navigation and assets remain document-relative. Error pages use the configured absolute base so internal forwarding works at nested missing URLs. Set the real public address before deployment.

See `docs/DEPLOYMENT_TOMCAT.md` and `docs/DEPLOYMENT_STATIC.md` for deployment examples.

## Update the CVs

Both PDFs are included; serving them needs no PDF-generation dependencies. After changing public-profile content, regenerate and inspect them before rebuilding:

```bash
python3 -m pip install -r requirements-optional.txt
python3 scripts/build_cv.py
python3 scripts/build_cv.py --check
python3 build.py
python3 scripts/package.py
```

Optional dependencies are only needed to regenerate PDFs. Font licences and provenance accompany the font files.

## Publication boundaries

Serve only `site/`, `deploy/ROOT/` or the WAR. `docs/`, `content/` and `scripts/` are maintenance source, not a web root.

The public build excludes private contact details, credentials, raw medical images, research datasets, unpublished dissertations, private application source, transcripts and administrative records. The original undergraduate certificate is included under the user's previously confirmed publication choice, with its bytes preserved.

## Verification

Version 4.0.2 passed 13,353 structural and deployment-copy checks. Its recorded HTTPS checks on 17 October 2026 established availability of the homepage, IAFM/Marginloom case studies and both application entry points, not every route, browser, device or server configuration. Earlier no-deployment statements remain historical evidence.

The OutcomeLab portfolio/CV updates subsequently passed 14,405 structural and package checks. The live bilingual project entry, mobile layout and PDF downloads were checked on 19 October 2026; see `docs/OUTCOMELAB_UPDATE.md` and `docs/CV_OUTCOMELAB_UPDATE.md`.

The site uses local CSS, JavaScript and images. Bilingual JSON supplies most content. Progressive enhancements are isolated so unavailable storage or one failed feature does not prevent reading the profile.
