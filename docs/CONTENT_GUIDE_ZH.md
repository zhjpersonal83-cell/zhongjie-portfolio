# Content maintenance guide

## One source, several outputs

`content/profile.json` supplies the public introduction, contact details, education, projects, skills, interests, timeline and current status. Pages, public JSON downloads and the CV generator read this source.

Bilingual fields use `{"en": "English text", "zh": "Chinese translation"}`. Update both languages together. Project `id` values are stable URL identifiers; changing an ID changes its page address, so normally retain existing IDs.

`content/coursework.json` contains module codes, programme, year, categories, bilingual descriptions and references. Filters match the original English category values, while the Chinese interface displays translated labels. Keep both ends consistent.

`content/site.json` holds the version, review date, canonical base and website description. Keep its review date consistent with `profile.json.updated`.

## Add a project

Add an object to the `projects` array using the existing schema:

- `id`: a stable lowercase, hyphenated identifier.
- `title`, `subtitle`, `summary`: bilingual name, type and concise description.
- `period`: evidenced dates; proposed dates must not masquerade as completion dates.
- `category`: `research` or `software`.
- `status`, `status_label`: machine-readable status and bilingual display labels. Existing values include `submitted`, `completed`, `prototype`, `private` and `maintained`.
- `role`: the actual contribution or role, with accurate AI-assistance attribution where applicable.
- `stack`: supported tools and methods.
- `sections`: paragraphs covering the question, contribution, implementation and evidence.
- `outcomes`, `limits`, `evidence`: outputs, limitations and sources.
- `repository`: optional; use only a verified, public, user-owned repository.
- `live_url`: optional; the verified public application URL.

The generator creates bilingual project detail pages, directory cards, search entries and printable-CV entries. Homepage selection is configured separately in `scripts/build.py`. The PDF CV has its own selected-project layout in `scripts/build_cv.py`.

## Status conventions

Applications, completed interviews, offers, formal registration, course completion, dissertation submission and degree awards are distinct events. Update each status from evidence, retain the record date and do not describe plans as completed outcomes.

Research numbers need their dataset, evaluation setting and verification status. Without a new experiment, do not transfer results from another test set or claim causal gains, clinical validity or best-in-class performance.

No unsupported employment, internship, publication, additional qualification or formal language-score sections are invented. Add those only when evidence becomes available.

## Update order

1. Edit and review both languages; update the dates in both JSON sources.
2. Where required, run `python3 scripts/build_cv.py`, render both PDFs and inspect them.
3. Run `python3 build.py`.
4. Run `python3 scripts/validate.py`.
5. Run `python3 scripts/package.py`.
6. Deploy only the static output or WAR, rather than making the whole project a web root.

## Publication boundaries

Only put publishable professional information in `profile.json`, since it generates a public download. Exclude private contact information, credentials, immigration/administrative documents, raw medical images, research data, detailed transcripts and non-public application code.

The undergraduate certificate remains public under the user's earlier explicit choice. Withdrawing it later requires removing the source asset, download links and deployed copies, then rebuilding and deploying. Hiding navigation alone does not withdraw a public file.
