# Connected article metadata — focused QA

**PASS.** Isolated four-file metadata follow-up. Checked four-file uncommitted patch against4c1; exactly7 additions/5 deletions. Final source hashes still match after publisher commit; current local HEAD `57c596052c8f1180584e39ae1a73778110e7e21b`. QA made no source edits, commits or pushes.

| Check | Result |
|---|---|
| `npm run build:website` | Exit0, website assets prepared |
| `npm run test:website -- website/tests/blog-seo-validation.test.ts website/tests/seo-linking.test.ts` | Exit0,226/226tests across2files passed |
| `npx tsx website/tools/lint-marketing-html.ts website/public/blog/framework-matters.html website/public/blog/index.html website/public/blog/swe-evo-analysis.html` | Exit0,0errors/6existing unrelated orphan-OG warnings |
| `git diff --check` | Exit0 |
| Task-local structural/metadata checker | PASS, focused metadata/date/filter/preservation assertions |

Category label now aligns SWE meta section/tag, hero and badge as **AI Assisted Analysis**; card uses the existing **Analysis** filter taxonomy. Executed the existing inline filter script in jsdom with external scripts/network disabled: Analysis includes SWE, Research excludes SWE, All restores SWE. This exercises the real existing filter code; no new committed implementation-mirroring test.

SWE title/description align card, metadata, feed, JSON-LD and llms.txt. Its OG article:modified_time, JSON-LD dateModified, visible time, index card and sitemap align on22Oct2026. Framework modified metadata/JSON-LD/visible time/card/sitemap align on21Oct2026. Original2Feb2026 publication dates remain preserved.

All three HTML embedded stylesheets and both SWE WiT table markup blocks are **byte-identical** to4c1. Native-table roles, mobile CSS, source links and all hrefs remain unchanged. No browser, screen-reader, AT or fresh axe claim is made. Root owns the reply-to-code-review verdicts; QA did not remove ARIA roles or alter CSS.

Dependency lockfiles match the compatible existing QA worktree; reused ignored root/UI node_modules symlinks. No package/lock changes. No broad suite repeated.

## Checked SHA-256

| Source | SHA-256 |
|---|---|
| `website/public/blog/framework-matters.html` | `931876f341bcb8a0502b98abd628dae50ec8cc2fc6c048b307b31d3ab5d2e5c7` |
| `website/public/blog/index.html` | `4c83255a118f01dd5c57aa514c2e9594d24e84ce05f249b4a3003558315a5d6f` |
| `website/public/blog/swe-evo-analysis.html` | `ebdab1fa9eaf55383a95ff21b8918dbca2a7753c89d676b827f51e46b23f0974` |
| `website/public/llms.txt` | `a2c81be5d86dc58c14598a702f99300905a60ddad12e53a68b05ccfd656a7bd2` |

Build, focused-test, HTML-lint and structural logs were retained in the task-local capture environment. The machine receipt is included as [results.json](results.json). These follow-up hashes are distinct from the original eight-artifact sandbox verifier; they must not replace that verifier's4c1 source baseline. Existing release/deploy monitors remain separate.
