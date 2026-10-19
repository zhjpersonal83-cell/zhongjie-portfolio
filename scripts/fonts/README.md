# Fonts for the optional public CV generator

`PortfolioSansSC-Regular.ttf` and `PortfolioSansSC-Semibold.ttf` are static,
renamed subsets of Noto Sans SC. They include the characters used by the current
public profile and CV template. Both fonts retain the SIL Open Font License 1.1;
the copyright statement and complete licence are in `OFL.txt`.

Upstream source: https://github.com/google/fonts/tree/main/ofl/notosanssc

The supplied files were derived from `NotoSansSC[wght].ttf`, with the weight axis
instantiated at 400 and 600 using FontTools, then subset to the current content.
They are named Portfolio Sans SC to distinguish the modified subsets from the
upstream fonts. The PDF generator embeds the required glyphs in each PDF; users
do not need to install a Chinese font to read the finished documents.

The two PDFs can be regenerated offline with the bundled fonts and
`requirements-optional.txt`. If a later content change introduces characters not
in the subset, the generator stops with the missing characters listed. Pass a
complete static TrueType font using `--font-regular` and `--font-semibold`, or
regenerate these subsets from the upstream font. Do not suppress the coverage
check or substitute an unembedded viewer font.

The website itself does not request or load these fonts. They are solely source
dependencies for PDF regeneration.

On 19 October 2026, the renamed OFL subsets were extended from the upstream Noto Sans SC variable font at weights 400 and 600 to cover the OutcomeLab CV description. The coverage check remains enabled.
