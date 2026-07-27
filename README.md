# Zhongjie Huang Portfolio — Context-safe build

Pure HTML, CSS and JavaScript. No JSP, Java classes or runtime compilation.

## Why this build exists
Version 3.0 used root-relative paths such as `/assets/styles.css`. Those work only when the site is deployed as Tomcat's `ROOT` application. If the WAR or folder is deployed under `/zhongjie-ai-portfolio/`, the browser incorrectly requests `http://host:port/assets/styles.css`, causing unstyled pages.

Version 3.2 converts all internal HTML links and assets to document-relative paths. It therefore works both at `/` and under a Tomcat context path such as `/zhongjie-ai-portfolio/`.

## Recommended Tomcat deployment
1. Stop Tomcat.
2. Delete the previously expanded application folder and matching old WAR.
3. Copy `deploy/zhongjie-ai-portfolio-static.war` into `webapps`.
4. Start Tomcat.
5. Open `http://localhost:8080/zhongjie-ai-portfolio-static/`.

For the domain root, rename `deploy/ROOT-static.war` to `ROOT.war`, remove the old `webapps/ROOT` folder, and deploy it to `webapps`.

Always clear the old expanded directory before replacing a WAR, then use Ctrl+F5.


## 3.2 deployment stability

This release uses versioned CSS/JS filenames to prevent stale browser or Tomcat assets, keeps all content visible if animation initialisation fails, and reduces oversized vertical spacing.
