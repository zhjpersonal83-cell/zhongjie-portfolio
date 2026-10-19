# Verification notes

**Recorded:** 16 October 2026  
**Scope:** the generated bilingual portfolio, its progressive JavaScript enhancements, selected CSS colour combinations, and separately reported build/PDF checks.

These notes distinguish what was checked from what remains unverified. They supplement the formal structural `TEST_REPORT`; they are not a browser acceptance report or a declaration of comprehensive WCAG conformance.

## 1. JavaScript behaviour: 16 passing test scenarios

No installed `jsdom`, `linkedom`, or `happy-dom` package was available in the current runtime. No package or browser was installed for these checks, and no preview server was started.

The checks used Node.js with a minimal element/event fixture constructed from five **actual generated HTML pages**:

- `site/coursework/index.html`
- `site/zh/coursework/index.html`
- `site/projects/index.html`
- `site/contact/index.html`
- `site/zh/contact/index.html`

The fixture supplied only the element, event, attribute, select-option, storage, clipboard and URL interfaces needed by the application. The existing `static/assets/app.js` was executed against that fixture. Pure search helpers were also extracted verbatim from the same source. The tests did not substitute a second implementation of the filtering or search algorithm.

All **16 scenarios passed**:

| No. | Scenario | Observed result |
| --- | --- | --- |
| 1 | AI boundaries and Unicode normalisation | `AI` did not match `Details about a maintained application`; it matched `Artificial intelligence`, and full-width `ＡＩ` matched Chinese wording for artificial intelligence. |
| 2 | Bidirectional language and GPU aliases | `NLP`, Chinese wording for natural language, and Chinese wording for natural-language processing matched text-processing/language-technology content; English NLP wording matched Chinese wording; `GPU` matched `Graphical Processing Units (GPUs)`. |
| 3 | English coursework search | `NLP` returned the three relevant generated records: COM3110, COM6115 and COM6513. |
| 4 | Chinese coursework search | Chinese wording for natural language returned the same three records. |
| 5 | Programme, subject area and query together | Combining the MSc programme, language-technology area and a query identifying COM6115 returned the expected record, reported `Showing 1 of 32 modules.`, and updated the shared URL. |
| 6 | Shared URL restoration | A new application instance restored the selected controls and expected record from the generated filter URL. |
| 7 | No matching result | An unmatched query hid all records, exposed the supplied empty-result message and reported zero results. |
| 8 | Clearing filters | Clearing restored all 32 coursework records and default controls, hid the empty-result message and disabled the inactive clear button. Unrelated query parameters, the URL fragment and existing history state were retained. |
| 9 | Invalid URL values and markup-shaped text | Unrecognised programme, area and level values were ignored. A query resembling an HTML element remained search text and did not insert content elements. |
| 10 | Storage access denied | A `localStorage` property getter that threw an exception did not prevent theme use or subsequent menu, filter and print-module initialisation. Theme toggling and filtering still worked. |
| 11 | History writes denied | A throwing `history.replaceState()` did not stop visible filtering. |
| 12 | Project-filter combination | The generated six-project catalogue correctly selected Marginloom when software category, prototype status and an `AI` query were combined. |
| 13 | Native dialog unavailable | When `showModal` was absent, quick-search controls were not activated. The normal navigation remained the fallback. |
| 14 | Clipboard in an insecure context | No clipboard call was made. Feedback included an email address for manual selection; the button did not claim success and the page did not navigate. |
| 15 | Secure clipboard request rejected | The Chinese manual-copy message appeared, the button became usable again, and its label did not falsely announce success. |
| 16 | Clipboard request pending, then successful | The button did not announce success while the clipboard promise was pending. Only successful completion produced the configured copied label and status message. |

The testing script and extracted page fixture were temporary verification materials for this build session, not additional production dependencies. The implementation also passed `node --check`. Earlier static CSS checks found balanced structural tokens and no undefined references among its 21 custom properties.

## 2. No-JavaScript structure: all 40 generated pages checked

The generated HTML and relevant default CSS rules were inspected together. On every page:

- The primary navigation contained ordinary links and had neither `hidden` nor `.js-only` applied to it.
- Default CSS displayed the navigation. Its collapsed state depended on the script-added `.menu-ready` class.
- Search, theme, mobile-menu, copy, print and filter-reset enhancement buttons carried `.js-only`, which is hidden when JavaScript has not enabled the page.
- An ordinary `mailto:` link remained available, so contact access did not depend on the clipboard enhancement.
- The complete page content remained in the HTML. Catalogue entries did not require JavaScript to become readable.

The actual English and Chinese contact pages also had visible copy-status elements without `.sr-only`. Their fallback text could be selected normally; the stylesheet did not disable text selection.

These were **markup and CSS-rule checks**, not visual inspection in a browser with JavaScript disabled.

## 3. Static colour calculations: 12 combinations

Foreground and background values were read from `static/assets/styles.css`. Ratios were calculated from sRGB relative luminance, including the nonlinear-to-linear channel conversion. Values below are rounded to two decimal places.

| Theme and foreground | Page background `--bg` | Card background `--surface` | Section background `--surface-alt` |
| --- | ---: | ---: | ---: |
| Light main text, `#172c35` | 13.28:1 | 14.37:1 | 12.72:1 |
| Light muted text, `#52656b` | 5.60:1 | 6.06:1 | **5.37:1** |
| Dark main text, `#f0f2e9` | 14.58:1 | 13.13:1 | 11.64:1 |
| Dark muted text, `#b5c6c6` | 9.30:1 | 8.38:1 | 7.43:1 |

The lowest of these twelve calculated combinations was **5.37:1**. All twelve exceed the **4.5:1 normal-text AA contrast threshold**. This statement applies only to the foreground/background combinations listed; it does not certify all components, states, imagery, or accessibility requirements across the site.

## 4. Build, existing routes and PDF checks reported by other contributors

The following results were supplied by the coordinating agent or the PDF contributor. They were not repeated as part of the JavaScript/CSS verification above:

| Check | Reported result and verification owner |
| --- | --- |
| Python build | The coordinating agent confirmed that the Python build generated 40 pages. |
| Existing page paths | The coordinating agent compared the old project and confirmed that all 17 original page paths were retained. |
| English CV PDF | Two pages; the PDF contributor rendered and visually inspected both pages. |
| Chinese CV PDF | Two pages; the PDF contributor rendered and visually inspected both pages. |
| PDF inspection method | The PDF contributor used `pdftoppm` and `view_image` to inspect all four rendered pages and reported no layout defects. The coordinating agent separately spot-checked two pages. |

The formal structural `TEST_REPORT` records the separate final build/package checks.

## 5. Coverage limits

No real browser or browser layout engine was used for the JavaScript/CSS checks recorded here. In particular, they do not establish:

- Actual desktop/mobile layout, media-query rendering, font metrics or horizontal overflow in a browser.
- Native dialog focus trapping, real keyboard interaction or screen-reader announcements.
- Operating-system clipboard permission prompts or real browser Clipboard API availability.
- Browser-generated print pagination from the HTML CV. The separately checked downloadable PDFs are different artifacts.
- Comprehensive WCAG conformance or behaviour across a browser/device matrix.

The tested application behaviour, no-JavaScript structure and listed colour combinations produced no defect requiring a production CSS or JavaScript change during this verification pass.
