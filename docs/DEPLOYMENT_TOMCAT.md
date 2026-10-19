# Tomcat deployment and rollback

Historical baseline: v4.0.2 was deployed to https://www.zhongjiehuang.com on 17 October 2026. The homepage, two application case studies, and the IAFM/Marginloom entry points returned HTTP 200 over HTTPS. Subsequent OutcomeLab and CV releases are recorded separately.

The original v4.0.0 delivery prepared static files and a WAR without connecting to a server. That historical record is not the current deployment status. Before each future deployment, verify the actual Tomcat instance, virtual host, domain, existing applications and backup location.

## 1. Deliverables and scope

| Path | Purpose |
| --- | --- |
| `site/` | Generated pages, images, public files and `WEB-INF/web.xml` |
| `deploy/ROOT/` | Exploded application matching `site/` file for file |
| `deploy/ROOT.war` | Matching WAR, normally for the root context |
| `content/`, `sources/`, `static/`, `scripts/`, `docs/` | Editable source and maintenance material, not a public web root |
| `docs/BUILD_MANIFEST.json` | File sizes and SHA-256 hashes, excluding its own hash |
| `docs/TEST_REPORT.md` | Recorded local checks and untested areas |

The website contains static resources rather than Java/JSP/Servlet business code or a database. Tomcat still needs its supported Java runtime; the core build/package tools need only Python's standard library. The Default Servlet serves static resources; see the [official documentation](https://tomcat.apache.org/tomcat-10.1-doc/default-servlet.html).

## 2. Choose the public path and rebuild

From the extracted `zhongjie-portfolio` directory:

```bash
python3 build.py --base-url https://www.zhongjiehuang.com
python3 scripts/package.py
```

These commands generate and check local files. `package.py` updates the exploded application, WAR, test report and build manifest, then creates the delivery ZIP outside the project. A failed validation does not replace that ZIP.

| Public address | Build `--base-url` | Tomcat WAR name |
| --- | --- | --- |
| `https://www.zhongjiehuang.com/` | `https://www.zhongjiehuang.com` | `ROOT.war` |
| `https://example.com/portfolio/` | `https://example.com/portfolio` | `portfolio.war` |

For a subpath:

```bash
python3 build.py --base-url https://example.com/portfolio
python3 scripts/package.py
```

Upload the newly built `deploy/ROOT.war` as `portfolio.war` for `/portfolio/`. Keep a single packaged WAR to avoid divergence. Renaming an old WAR is insufficient: rebuild canonical, hreflang, sitemap and 404 navigation/asset URLs for the final domain and path.

Tomcat normally derives the context from the application filename: uppercase `ROOT` is the root application, while `portfolio.war` maps to `/portfolio`. An external Context Descriptor with `docBase` may override the deployment source, so inspect existing configuration. See [official naming rules](https://tomcat.apache.org/tomcat-10.1-doc/config/context.html#Naming).

## 3. Inspect and back up before installation

1. Verify the running `CATALINA_BASE`, Host `appBase`, service manager and reverse proxy. A directory named `webapps` does not establish the active instance.
2. Confirm the root application belongs to this portfolio. If another application occupies it, use a selected subpath or separate virtual host.
3. Check for a matching Context Descriptor, such as `conf/Catalina/localhost/ROOT.xml` or `portfolio.xml`, which can affect deployment.
4. During the planned maintenance window, stop or take down only the target application using the established process. Back up its WAR, exploded directory and relevant descriptor **outside `appBase/webapps`**, recording original paths, permissions and hashes. A backup WAR left in the auto-deploy directory may become a separate application.
5. Verify the new WAR hash, then replace only the chosen application. Retain other application directories and WARs; do not bulk-delete `webapps`.

Startup/runtime deployment depends on `deployOnStartup`, `autoDeploy`, `unpackWARs` and other Host settings. Copying a WAR does not prove immediate deployment on every server. See the [official deployment process](https://tomcat.apache.org/tomcat-10.1-doc/deployer-howto.html).

## 4. Error pages, context paths and public files

`WEB-INF/web.xml` maps 404 responses to `/404.html` relative to the current application context. The default error page is English and links to its Chinese counterpart.

Only the two error pages use the absolute canonical base for internal navigation and assets. This keeps styling and home links valid after internal forwarding from a nested missing URL. They do not set `<base>`; `#main` remains relative to the error document. Normal pages use document-relative navigation and assets. Offline checks simulate nested missing paths with and without trailing slashes, but the actual server must still be checked for status codes and correct routing.

The original certificate is preserved with SHA-256:

```text
3a1c5afda69264df17715098d05bb5ad24d8888676857c1a0ccff1b04f486087
```

Publishing selected website files differs from publishing the full source tree. Use a WAR/exploded application for Tomcat, or `site/` for a static host. Do not extract the complete delivery ZIP into a publicly browsable directory.

## 5. Post-deployment checks

The recorded entry-point checks do not establish all of the following:

- Open English/Chinese homepages, project details, coursework, CV, contact and privacy pages directly; refresh deep pages.
- Switch languages while retaining the content page; confirm CSS, JS, image, CV and certificate requests succeed.
- Test a random nested missing path: HTTP 404, the portfolio error page and working bilingual home/assets links.
- Check directory URLs without trailing slashes for correct redirects and no loops; confirm root/subpath routing matches the plan.
- Check mobile and desktop navigation, filtering, themes, keyboard use, printing and PDF downloads.
- Check domain, HTTPS, MIME, caching, proxy security headers and logs; canonical/sitemap URLs must use the actual public address.
- Ensure `WEB-INF` cannot be downloaded and other applications remain available.

## 6. Rollback

Use the same maintenance procedure to stop or take down the target context. Move the failed WAR and exploded directory outside `webapps/appBase` for investigation; restore the previous target application and any necessary descriptor. Restore permissions, start through the established process, and check the homepage, deep pages, 404 and other applications. Do not empty the whole application directory.

## 7. Historical verification boundary

Version 4.0.2 passed 13,353 Python structural/deployment-copy checks. On 17 October 2026 these HTTPS addresses also returned HTTP 200:

- `https://www.zhongjiehuang.com/`
- `https://www.zhongjiehuang.com/projects/investment-financial-management/`
- `https://www.zhongjiehuang.com/projects/marginloom/`
- `https://iafm.zhongjiehuang.com/`
- `https://marginloom.zhongjiehuang.com/`

Earlier statements that Tomcat/Nginx/live checks were not executed describe initial file preparation. Entry-point checks and offline validation have different scopes; later changes require the relevant pages, browser behaviour and server settings to be checked again.
