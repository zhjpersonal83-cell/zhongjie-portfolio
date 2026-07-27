# Tomcat deployment — context-safe static build

This package contains no JSP and no Java code. Tomcat only serves static files.

## Option A: deploy under a context path

Copy:

`deploy/zhongjie-ai-portfolio-static.war`

to Tomcat's `webapps` directory. Tomcat will expose it at:

`http://localhost:8080/zhongjie-ai-portfolio-static/`

## Option B: deploy at the server root

1. Stop Tomcat.
2. Delete the old `webapps/ROOT` directory and `webapps/ROOT.war`.
3. Rename `deploy/ROOT-static.war` to `ROOT.war`.
4. Copy it into `webapps`.
5. Start Tomcat and open `http://localhost:8080/`.

## Required cleanup

Tomcat expands WAR files. If an old expanded folder remains, stale HTML can continue referencing the old CSS paths. Delete the corresponding expanded folder before copying the new WAR. Then hard-refresh with Ctrl+F5.

## CSS diagnostic

Open DevTools → Network and reload. `styles.css` must return HTTP 200 with `Content-Type: text/css`. In this build, nested pages request paths such as `../../assets/styles.css`, so deployment beneath a context path remains valid.
