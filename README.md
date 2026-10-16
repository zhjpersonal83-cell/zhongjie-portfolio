# Zhongjie Huang Portfolio · v4.0.1

**网站更新日期：2026-10-17；原有学术资料核对日期：2026-10-16。** 中英双语个人研究与工程作品集，包含完整源码、可直接托管的静态页面、Tomcat WAR，以及中英文公开简历。

## 从哪里开始

| 需要做什么 | 文件或目录 |
| --- | --- |
| 查看英文首页 | `site/index.html` |
| 查看中文首页 | `site/zh/index.html` |
| 部署到 Tomcat 根路径 | `deploy/ROOT.war` |
| 部署到一般静态服务器 | `site/` 的内容 |
| 查看中英文简历 | `site/files/zhongjie-huang-cv-en.pdf` / `zhongjie-huang-cv-zh.pdf` |
| 修改个人信息 | `content/profile.json` |
| 修改课程目录 | `content/coursework.json` |
| 修改站点地址或版本 | `content/site.json` |
| 查看测试结果 | `docs/TEST_REPORT.md` |
| 查看内容更新与确认事项 | `docs/RELEASE_REVIEW_ZH.md` |

本轮只准备文件，**没有执行服务器部署**。现成的 `site/` 和 WAR 不需要 Python、Node.js、数据库或前端构建环境来运行。

## 本版内容

- 36 个 HTML 页面：18 个栏目或项目页面，各有对应的中英文版本。
- 4 个项目案例：硕士组织学图像研究、本科表情识别、Marginloom、IAFM 投资与财务管理应用。
- 首页和项目页面提供 [Marginloom](https://marginloom.zhongjiehuang.com) 与 [IAFM](https://iafm.zhongjiehuang.com) 的直接访问入口。
- 7 组有依据的能力分类，以及 32 门课程（8 门研究生课程、24 门本科课程）。
- 独立的教育、研究、技能、近况、项目、课程、联系、简历与研究验证方法栏目。
- 中英文 PDF 简历、可打印简历网页及公开个人资料 JSON 下载。
- 页面对应的语言切换、深浅主题、快捷导航、项目和课程组合筛选、可分享筛选网址。
- 原始本科学位证书与肖像继续保留；表情识别项目仅展示文字介绍。

## 学历和项目状态

本科：University of Sheffield，BSc Artificial Intelligence and Computer Science，2021 年 9 月至 2025 年 7 月；学位授予日 2025 年 7 月 1 日，2:1。

硕士：MSc Artificial Intelligence，2025–2026；论文已提交，最终成绩和学位授予待确认。不同旧资料中的具体完成、提交日期有差异，因此没有编造一个精确日期，也没有填写未经确认的学位等级。

博士：已完成杜伦大学面试，结果待确认；2027 年 1 月仅为拟议入学时间。拟开展研究与已经完成的项目分别标明状态。

## 重新构建

Python 3.9 或更新版本即可生成网站；核心构建及校验使用标准库。

```bash
python3 build.py
python3 scripts/validate.py
python3 scripts/package.py
```

`build.py` 重新生成 `site/`；`package.py` 校验后生成一致的 `deploy/ROOT/`、`deploy/ROOT.war` 和项目外的 `zhongjie-portfolio.zip`，压缩包顶层目录为 `zhongjie-portfolio/`。不要直接编辑生成目录，否则下一次构建会覆盖这些编辑。

### 配置域名和子路径

当前 canonical 地址为 `https://www.zhongjiehuang.com`。如以后改用子路径，先执行：

```bash
python3 build.py --base-url https://www.zhongjiehuang.com/portfolio
python3 scripts/package.py
```

`--base-url` 会**同步修改 `content/site.json`**，然后更新 canonical、语言替代链接、站点地图、分享链接和 404 页基址。普通页面的浏览链接及资源路径保持文档相对。404 页面通过配置的绝对基址支持服务器内部转发，因此正式部署时必须设置真实对外地址。

Tomcat 详细步骤见 `docs/DEPLOYMENT_TOMCAT.md`；静态服务器与 nginx 示例见 `docs/DEPLOYMENT_STATIC.md`。

## 更新简历

两份 PDF 已包含在包内，部署时无需生成。更新公开个人资料后，建议先重新生成 PDF，再构建网站：

```bash
python3 -m pip install -r requirements-optional.txt
python3 scripts/build_cv.py
python3 scripts/build_cv.py --check
python3 build.py
python3 scripts/package.py
```

PDF 生成依赖仅用于更新简历；网站运行、静态构建与打包无需这些依赖。字体许可及来源随字体文件一并保留。

## 文件边界

仅将 `site/`、`deploy/ROOT/` 或 WAR 用作网站内容。`docs/`、`content/`、`scripts/` 是维护源码和说明，不应把整个项目目录设为 Web 根目录。

公开构建不包含私人联系方式、账号凭据、原始医学图像、研究数据集、非公开论文全文、私有仓库源码、成绩单或行政文件。源项目中的原始本科学位证书按照已确认的公开选择保留，未修改其字节。

## Verification

The release includes structural validation and package consistency checks. The report records what actually ran. Browser rendering, real-device behaviour, Tomcat/nginx runtime behaviour and TLS configuration still need to be verified in the target hosting environment. No browser or server deployment was performed during this update.

The website is a static application with local CSS, JavaScript and images. Most content is generated from bilingual JSON. Client-side enhancements are isolated so unavailable storage or one failed feature does not prevent reading the profile.
