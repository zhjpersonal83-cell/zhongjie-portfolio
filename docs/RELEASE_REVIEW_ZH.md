# v4.0.2 content review and decisions

Historical website update: 17 October 2026. Version 4.0.2 added GitHub links to both application cards and detail pages, updated IAFM's ten-currency reports, paired transfers and administrator permissions, and was deployed with live entry-point checks. The v4.0.1 decisions to remove the portfolio-self and Android Hub project entries and retain text-only emotion recognition remained in force. Academic-source review remained dated 16 October 2026. Later OutcomeLab/CV releases have separate records.

## Key content decisions

| Topic | Adopted wording | Evidence and limits |
| --- | --- | --- |
| Name | Zhongjie Huang | Consistent across the earlier portfolio and academic records |
| BSc | Sheffield AI & CS, September 2021–July 2025; awarded 1 July 2025; 2:1 | Formal HEAR and original certificate; module marks/rankings excluded |
| MSc | Artificial Intelligence study, 2025–2026; dissertation submitted; results and award pending | Recent CV, application fact-check material and submitted dissertation; no later award evidence located |
| Exact MSc dates | Supported years only; document dates are not combined into an award date | Earlier CVs, expected dates, dissertation cover and form fields differ by version |
| MSc research | Four-pipeline QuPath/Cellpose-DINO/Cyto R-CNN/CSGO comparison | Based on the newer dissertation rather than an early application proposal |
| MSc findings | No clear evidence that fusion outperformed the image-only baseline | Do not relabel the finding as significant improvement or clinical validation |
| BSc result | Reported mixed-test accuracy of 76.25% | Specific mixed-test setting; not rerun during this update or interchangeable with another dataset's result |
| PhD | Durham interview completed, outcome pending; January 2027 proposed entry | Latest visible interview progress; no formal offer/registration evidence |
| Proposed direction | Reliable visual segmentation under environmental and sensor shift | Future research, separate from completed experiments |
| Marginloom | Personal AI-reliability research/software prototype, developed with AI assistance | Public repository/README/configuration reviewed; no business, revenue, customer or clinical-effectiveness claim |
| IAFM | Personal investment and financial-management application | Public application entry; private accounts and operational records excluded |
| Employment, internships, extra awards, publications and language scores | No unsupported entries | Coursework/personal projects are not employment or formal publications |

## Sources

The review used the supplied undergraduate certificate, BSc transcript/HEAR, 2025 BSc final report, MSc dissertation dated 30 September 2026, October 2026 LinkedIn handoff, recent job-search CV and Durham interview fact-check material.

These records supported the professional profile but are not distributed with the website, apart from the separately approved public certificate. Internal retrieval records, raw identifiers, private correspondence and research data are excluded.

Public references:

- Account: https://github.com/zhjpersonal83-cell
- Marginloom: https://github.com/zhjpersonal83-cell/marginloom
- IAFM: https://github.com/zhjpersonal83-cell/Investment_and_Financial_Management
- The LinkedIn address was retained from the confirmed handoff; this historical review did not verify its live page.
- Existing public email `zhuang68@sheffield.ac.uk` was retained, rather than replaced with a private address or phone number.

Marginloom had a successful recorded GitHub Actions run for a specific commit on 4 October 2026. That historical record was not a new execution or full audit of current software and was not presented as current certification.

## Structure and features at v4.0.2

Four project entries were retained. The homepage, directory and case studies linked to Marginloom/IAFM applications and source. The IAFM narrative described ten-currency reports, paired transfers and server-controlled inflation maintenance, without elevating targeted checks into independent security certification. Removed project experiences stayed excluded from detail pages, search, sitemap, public JSON and both CVs. Language switching retained the current page, and all 32 coursework entries remained.

Editable source and display output were separated. `content/profile.json` and `content/coursework.json` supplied generated pages/downloads. Themes, command search, combined filters and copying were progressive enhancements; core information was embedded in HTML.

PDF CVs had a reproducible generator and source fingerprints. Packaging created matching static/WAR outputs and checked original-certificate and deployment-copy integrity.

## Verification scope

See `TEST_REPORT.md` for automated checks and `VERIFICATION_NOTES.md` for supplementary interaction/PDF review.

Version 4.0.2 passed 13,353 structural/deployment-copy checks. Bilingual source links and text-only emotion recognition were checked. Required font glyphs were supplied, and both two-page PDFs were rebuilt with valid fingerprints. On 17 October 2026 the homepage, IAFM/Marginloom detail pages and both application entry points returned HTTP 200 over HTTPS. The build script itself did not deploy.

Earlier card-browser checks, CV-layout reviews and no-deployment statements establish only their recorded versions/steps. Entry-point checks do not imply full physical-device, all-route, header, 404 or cross-browser acceptance.

## Updates when new evidence arrives

1. After formal MSc results/award confirmation, update `education` and `timeline`, then regenerate both CVs.
2. Update the PhD application status after a formal offer; do not use PhD-student status before registration begins.
3. Change public contact/domain values consistently in profile data, site configuration and PDFs.
4. Add dated evidence links after actual project releases, measurements or public outcomes; do not automatically inherit old test conclusions.
