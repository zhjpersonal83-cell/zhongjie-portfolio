# Static-server deployment

Nginx or another static host supporting directory indexes and custom 404 pages can serve this site. This document originated during file preparation, when no server was changed. Later live deployments are recorded separately. Before a future deployment, verify the domain, web root and any `/portfolio/` context path.

## 1. Build

```bash
python3 build.py --base-url https://www.zhongjiehuang.com
python3 scripts/package.py
```

Content comes from `content/`, source styles/scripts and `static/`. The generated public document root is `site/`; a static server does not need `ROOT.war`. Keep source, maintenance documents and delivery ZIPs outside the web root.

For `https://example.com/portfolio/`:

```bash
python3 build.py --base-url https://example.com/portfolio
python3 scripts/package.py
```

The base URL supplies canonical, hreflang, sitemap and structured-data URLs. Normal navigation and assets are document-relative. Only 404 pages use the absolute canonical base, allowing internal forwarding at deeply nested missing URLs. They retain the current document's `#main` skip link and do not set an HTML `<base>`. Rebuild after changing the public domain or context path.

## 2. Nginx root-context example

`deploy/nginx.conf.example` contains an `http`-context cache `map` and a root-context virtual host. Adjust its domain, document path, listeners and TLS to the actual server; do not overwrite the main Nginx configuration.

| Setting | Purpose |
| --- | --- |
| `root` points to `site/` | Serve only generated public content |
| `index index.html` | Resolve directory indexes |
| `try_files $uri $uri/ =404` | Serve existing paths and preserve 404 for missing paths |
| `error_page 404 /404.html` | Use the custom error page without changing the status to 200 |
| `etag on` | Supply ETags |
| `no-cache` for HTML/discovery files | Allow storage but require revalidation |
| One-year cache for content-hashed CSS/JS | Changed content receives a new filename |
| One-hour cache for other static files | Bound image/PDF update delay |
| `nosniff`, referrer policy and embedding restrictions | Basic response headers |

See the [official core-module documentation](https://nginx.org/en/docs/http/ngx_http_core_module.html) for `try_files`, `error_page` and `etag`. All `add_header` directives are at one level; a `map` chooses caching, avoiding accidental loss of inherited security headers. See the [Headers](https://nginx.org/en/docs/http/ngx_http_headers_module.html) and [Map](https://nginx.org/en/docs/http/ngx_http_map_module.html) modules.

The example CSP restricts object content, base URLs and framing, but does not restrict script/style loading, retaining compatibility with current inline structured data and styles. A full source policy needs hashes or nonces for actual inline content and browser validation. This example is not an already configured HTTPS service; retain or complete the server's certificate and HTTP-to-HTTPS redirect setup.

## 3. Subpath example

Use `root` with a real subdirectory to avoid ambiguity between `alias` and file lookup:

```text
/srv/www/portfolio-public/portfolio/index.html
/srv/www/portfolio-public/portfolio/zh/index.html
/srv/www/portfolio-public/portfolio/assets/...
```

Copy the contents of `site/` into `portfolio-public/portfolio/`, then merge the following routes into the verified virtual host, replacing example paths:

```nginx
location = /portfolio {
    return 301 /portfolio/;
}

location /portfolio/ {
    root /srv/www/portfolio-public;
    index index.html;
    try_files $uri $uri/ =404;
    error_page 404 /portfolio/404.html;
}

location = /portfolio/404.html {
    root /srv/www/portfolio-public;
    internal;
}

location ~* ^/portfolio/(WEB-INF|META-INF)(/|$) {
    return 404;
}
```

Combine this with MIME, cache, security-header and hidden-file restrictions from the root example. Check conflicts with existing location matching. Keep `error_page` within the portfolio route to avoid changing other sites' error handling.

A generated `portfolio/robots.txt` does not replace the domain-root `/robots.txt`. If crawler discovery is required, merge this site's complete sitemap URL into the root file while retaining other rules. See [Google's robots.txt location guidance](https://developers.google.com/crawling/docs/robots-txt/create-robots-txt).

## 4. Published files

`WEB-INF/web.xml` is retained for Tomcat packaging. Nginx does not automatically apply Java web-application directory protection, so the example explicitly blocks `WEB-INF` and `META-INF`. Other static platforms may exclude them from the publishing copy; do not alter original certificates or generated source files to evade validation.

The privacy page describes the current static portfolio. Adding analytics, forms, login, external fonts or third-party scripts requires a corresponding policy and server review. This delivery needs no backend form service.

## 5. Publish, verify and roll back

1. Retain the current release or create a versioned copy; store backups outside the public web root.
2. Upload `site/` to the planned release location and verify hashes. Never make the full project the Nginx root.
3. Follow the existing server procedure to syntax-check the merged configuration, then switch the directory or reload after confirming no conflicts. The original file-preparation run did not perform these operations.
4. Check both languages, deep refresh, coursework filters, navigation, themes, CV/certificate links, print, mobile layout, status codes, MIME, caching and security headers.
5. Test a nested missing URL: expect HTTP 404, working styling and a home link. Confirm `WEB-INF/web.xml` cannot be downloaded.
6. On failure, restore the previous directory/configuration using the server's established process. Roll back only this portfolio's files/routes.

Offline structure checks are recorded in `docs/TEST_REPORT.md`. They do not establish HTTP behaviour, valid Nginx syntax, TLS or real-browser compatibility on the final host.
