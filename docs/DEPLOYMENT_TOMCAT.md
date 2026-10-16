# Tomcat 部署与回滚说明

本次交付包含可检查的静态文件与 WAR 包，**没有连接、修改或部署到服务器**。以下为后续部署步骤；真正执行前需要核对服务器的 Tomcat 实例、虚拟主机、域名、现有应用与备份位置。

## 1. 交付物与使用范围

| 路径 | 用途 |
| --- | --- |
| `site/` | 生成的网页、图片、公开文件与 `WEB-INF/web.xml` |
| `deploy/ROOT/` | 与 `site/` 逐文件一致的展开应用 |
| `deploy/ROOT.war` | 与上述目录内容一致的 WAR，默认用于网站根路径 |
| `content/`、`sources/`、`static/`、`scripts/`、`docs/` | 编辑、构建与维护资料；不应作为公开网站根目录 |
| `docs/BUILD_MANIFEST.json` | 交付文件大小与 SHA-256 清单；不包含清单自身的摘要 |
| `docs/TEST_REPORT.md` | 本地静态校验的真实结果与未覆盖事项 |

网站自身只需要静态资源服务，不包含 Java、JSP、Servlet 业务代码或数据库。Tomcat 仍需它自身支持的 Java 运行环境；本项目的构建与打包只依赖 Python 3 标准库。Tomcat 的 Default Servlet 可以提供静态资源。[官方说明](https://tomcat.apache.org/tomcat-10.1-doc/default-servlet.html)

## 2. 先确定访问路径并重新构建

在解压后的 `zhongjie-portfolio` 目录运行：

```bash
python3 build.py --base-url https://www.zhongjiehuang.com
python3 scripts/package.py
```

这些命令只在本机生成和检查文件。`package.py` 会更新 `deploy/ROOT/`、`deploy/ROOT.war`、测试报告和构建清单，然后在项目目录之外创建交付 ZIP；校验失败时不会替换交付 ZIP。

| 目标网址 | 构建时的 `--base-url` | Tomcat 中的 WAR 名称 |
| --- | --- | --- |
| `https://www.zhongjiehuang.com/` | `https://www.zhongjiehuang.com` | `ROOT.war` |
| `https://example.com/portfolio/` | `https://example.com/portfolio` | `portfolio.war` |

子路径使用示例：

```bash
python3 build.py --base-url https://example.com/portfolio
python3 scripts/package.py
```

为 `/portfolio/` 部署时，上传阶段把最新 `deploy/ROOT.war` 命名为 `portfolio.war` 即可。交付包只保留一份 WAR，避免两份内容漂移。不要仅重命名旧 WAR：先用最终域名和子路径重建 canonical、hreflang、sitemap 以及 404 的导航与资源 URL。

Tomcat 自动部署按应用文件名推导上下文路径：大写 `ROOT` 对应根应用；`portfolio.war` 对应 `/portfolio`。如果服务器已用外置 Context Descriptor 指定 `docBase`，应遵循已有配置，不能直接假定 WAR 文件名就是生效路径。[官方命名规则](https://tomcat.apache.org/tomcat-10.1-doc/config/context.html#Naming)

## 3. 安装前核对与备份

1. 确认真正运行的 `CATALINA_BASE`、Host `appBase`、服务管理方式及反向代理配置。`webapps` 是常见默认位置，但不能凭目录名猜测当前服务实例。
2. 查看根应用是否属于本作品集。若已有其他业务占用根路径，先选定 `/portfolio/` 或单独虚拟主机，避免覆盖该业务。
3. 确认同名 Context Descriptor 是否存在，例如实例配置目录中的 `conf/Catalina/localhost/ROOT.xml` 或 `portfolio.xml`。它可能影响实际部署来源。
4. 进入计划好的维护窗口，按服务器现有流程停止或下线目标应用。将当前目标 WAR、同名展开目录和相关 Context Descriptor **备份到 `appBase/webapps` 之外**，记录原路径、权限及摘要。备份不要以另一个 WAR 名称留在自动部署目录，否则可能被识别为新应用。
5. 核验新 WAR 摘要与交付包一致，然后只替换所选应用的同名文件。保留其他应用目录及其 WAR；不要对整个 `webapps` 目录执行批量删除。

Tomcat 支持启动时部署或运行时自动部署，但具体行为取决于 Host 的 `deployOnStartup`、`autoDeploy`、`unpackWARs` 等配置。不要把“复制 WAR”当成在所有服务器上都立即完成部署的保证。[官方部署流程](https://tomcat.apache.org/tomcat-10.1-doc/deployer-howto.html)

## 4. 404、子路径与公开文件

包内 `WEB-INF/web.xml` 将 404 映射到 `/404.html`；该位置相对于当前 Web 应用上下文。默认错误页面为英文，并提供中文对应页面入口。

仅两种语言的 404 页面使用配置的绝对 canonical 基址生成站内导航与资源 URL，因此在深层错误网址被内部转发到 404 页面后，样式和返回首页入口仍指向正确位置。404 不设置 HTML `<base>`，其 `#main` 跳过导航链接仍指向当前错误文档。其余 34 个正常页面的浏览链接与资源地址使用文档相对路径。校验器模拟了带与不带末尾斜杠的多级缺失网址下的 URL 解析；实际服务器仍须验证 404 返回码与链接，离线解析不能证明服务器配置已经生效。

学位证书保留原文件，SHA-256 为：

```text
3a1c5afda69264df17715098d05bb5ad24d8888676857c1a0ccff1b04f486087
```

部署公开文件与部署整个源码目录不同。对 Tomcat，使用 WAR 或展开应用；对静态服务器，使用 `site/`。不要把整个交付 ZIP 解压到一个可浏览下载的公开目录。

## 5. 部署后的实际检查

以下项目是**待服务器部署后执行**的验收项，不代表本次已经通过：

- 英文首页、中文首页、项目详情、课程、CV、联系与隐私页面能直接打开；刷新深层页面不报错。
- 从深层页面切换语言仍停留在同一内容页；所有 CSS、JS、图片、简历和证书请求成功。
- 随机不存在的多级路径返回 HTTP `404`，显示作品集错误页；错误页资源和中英文入口有效。
- 目录网址缺少末尾斜杠时行为正确，不发生循环跳转；根路径和目标子路径符合实际部署方案。
- 手机和桌面浏览器验证导航、课程筛选、主题切换、键盘操作、打印以及 PDF 下载。
- 域名、HTTPS、MIME、缓存、反向代理安全响应头与访问日志符合服务器配置；canonical 和 sitemap 指向当前正式地址。
- `WEB-INF` 内容不能被外部直接下载，其他原有应用保持可用。

## 6. 回滚

按同一维护流程停止或下线本次目标应用；将本次 WAR 和展开目录移到 `webapps/appBase` 之外留作排查，再恢复上一版目标应用及必要的 Context Descriptor。恢复权限后按原流程启动，核对首页、深层页、404 和其他应用。回滚只操作本作品集的目标上下文，不清空整个应用目录。

## 7. 本次验证边界

本次用纯 Python 检查了静态结构、文件路径、资源、锚点、语言对应、配置、证书摘要及打包一致性，具体数量以 `docs/TEST_REPORT.md` 为准。没有运行 Tomcat、nginx、浏览器端交互或真实服务器部署检查。部署文档根据 Apache Tomcat 官方资料编写，实际运行版本及服务器现有策略需要在后续操作时确认。
