# 静态服务器部署说明

本网站可由 nginx 或其他支持目录首页和自定义 404 的静态服务器提供。本轮只交付文件，没有发布网站。后续应先确认目标域名、网站根路径或 `/portfolio/` 子路径，再执行实际部署。

## 1. 生成静态站点

在项目目录执行：

```bash
python3 build.py --base-url https://www.zhongjiehuang.com
python3 scripts/package.py
```

网站内容来自 `content/`、源样式/脚本以及 `static/`；构建后的公开文档根目录为 `site/`。静态服务器不需要 `ROOT.war`。源码、维护文档及完整交付 ZIP 应存放在公开目录之外。

如果实际地址为 `https://example.com/portfolio/`，构建命令应改为：

```bash
python3 build.py --base-url https://example.com/portfolio
python3 scripts/package.py
```

构建基址用于 canonical、hreflang、sitemap 和结构化数据。正常页面的导航与资源使用文档相对路径；仅 404 页面的站内导航与资源使用配置的绝对 canonical 基址，确保多级缺失网址下仍能正确解析。404 保留当前文档的 `#main` 跳过导航链接，不设置 HTML `<base>`。更改正式域名或部署子路径后需要重新构建。

## 2. nginx 根路径示例

参考 `deploy/nginx.conf.example`。它包含位于 `http` 上下文的缓存 `map` 和一个根路径虚拟主机示例。域名、文档路径、监听方式及 TLS 均需与真实服务器匹配，不应覆盖已有 nginx 主配置。

该示例使用以下行为：

| 项目 | 配置目的 |
| --- | --- |
| `root` 指向 `site/` | 只提供生成的公开站点 |
| `index index.html` | 处理目录首页 |
| `try_files $uri $uri/ =404` | 已有文件正常返回，不存在路径保持 404 |
| `error_page 404 /404.html` | 提供自定义错误页，不把 404 改为 200 |
| `etag on` | 为静态资源提供 ETag |
| HTML 与发现文件 `no-cache` | 可以缓存，但使用前需要重新验证 |
| 含内容哈希的 CSS/JS 缓存一年 | 内容改变即换文件名，避免旧资源复用 |
| 其他静态文件缓存一小时 | 控制图片和 PDF 的更新延迟 |
| `nosniff`、Referrer Policy、限制嵌入 | 提供基本的响应头设置 |

nginx 的 `try_files`、`error_page` 和 `etag` 行为见 [官方核心模块文档](https://nginx.org/en/docs/http/ngx_http_core_module.html)。示例把所有 `add_header` 放在同一层，并用 `map` 选择缓存策略，避免子级声明缓存响应头时意外失去继承的安全响应头；相关规则见 [Headers 模块](https://nginx.org/en/docs/http/ngx_http_headers_module.html) 与 [Map 模块](https://nginx.org/en/docs/http/ngx_http_map_module.html)。

示例 CSP 只限制对象内容、基地址和页面被嵌入的来源，不限制脚本/样式加载，以兼容当前页面结构化数据与样式。若后续要增加完整脚本/样式来源限制，应为实际页面中的内联内容设计 hash 或 nonce 并进行浏览器验证。示例不是已配置好的 HTTPS 服务，证书与 HTTP 到 HTTPS 的跳转应沿用或补全服务器既有配置。

## 3. nginx 子路径示例

为避免 `alias` 与文件查找的路径组合出现歧义，可以使用 `root` 加实际子目录。示意结构为：

```text
/srv/www/portfolio-public/portfolio/index.html
/srv/www/portfolio-public/portfolio/zh/index.html
/srv/www/portfolio-public/portfolio/assets/...
```

即把 `site/` 的内容放在 `portfolio-public/portfolio/` 中，再把以下路由合并到经过核对的虚拟主机；示意路径需替换成真实位置：

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

配合根路径示例中的 MIME、缓存、安全响应头与隐藏文件限制使用，并根据已有 `location` 的匹配关系检查冲突。上面的 `error_page` 只放在作品集路由内，避免直接改变同一虚拟主机上其他网站的错误页。

子路径站点生成的 `portfolio/robots.txt` 不能代替域名根部的 `/robots.txt`。如需要搜索引擎发现规则，应在已有域名根部 `robots.txt` 中合并本网站 sitemap 的完整 URL，保留其他网站的规则。[Google 官方 robots.txt 位置说明](https://developers.google.com/crawling/docs/robots-txt/create-robots-txt)

## 4. 文件公开范围

`WEB-INF/web.xml` 随站点保留用于 Tomcat 打包。nginx 不会自动套用 Java Web 应用的目录保护规则，示例因此明确阻止 `WEB-INF` 和 `META-INF` 路径。其他静态平台可在发布副本中排除这两个目录，但不要手工改变源码中的原始证书或生成文件以规避构建校验。

隐私页面描述的是本静态作品集当前行为；未来接入分析工具、留言表单、登录、外部字体或第三方脚本后，应同步更新该页面与服务器策略。当前交付不依赖后端表单服务。

## 5. 发布、验收和回滚

1. 保留现有发布目录或创建带版本标识的发布副本；备份放在公开文档根目录之外。
2. 将新的 `site/` 内容传到计划中的目标发布位置；核对文件摘要。不要把整个项目目录设置为 nginx `root`。
3. 按服务器现有流程检查合并后的 nginx 配置语法，确认无冲突后再切换站点目录或重新加载配置。本次没有执行这些操作。
4. 验证英文和中文页面、深层页面刷新、课程筛选、导航、主题切换、CV/证书、打印、手机布局、HTTP 状态码及 MIME/缓存/安全响应头。
5. 专门访问一个多级不存在路径，确认 HTTP 404、样式和返回首页入口正常；确认 `WEB-INF/web.xml` 不能公开下载。
6. 若验收失败，按服务器既有流程恢复上一版目录或配置；只回滚本作品集的文件与路由，保留其他网站。

本地结构检查结果见 `docs/TEST_REPORT.md`。HTTP 行为、nginx 配置语法、TLS 和真实浏览器兼容性需要在最终服务器环境中验证，不能由离线 ZIP 内容检查推断为已通过。
