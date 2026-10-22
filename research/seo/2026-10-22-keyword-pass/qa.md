# SWE-EVO keyword/definition pass — focused QA

**PASS.** Checked the uncommitted worktree on `seo/days-1-5-20261021` against HEAD `0527af498b00d5df33781c41fd4b939f996eb9af`. Exactly **five** files changed: SWE article, CLI benchmark article, blog index, feed and sitemap. QA made no source edits.

| Command | Result |
|---|---|
| `npm run build:website` | Exit0; website assets prepared |
| `npm run test:website -- website/tests/blog-seo-validation.test.ts website/tests/seo-linking.test.ts` | Exit0; 226/226 tests across2 files passed |
| `npx tsx website/tools/lint-marketing-html.ts website/public/blog/swe-evo-analysis.html website/public/blog/headless-coding-agent-cli-benchmark.html website/public/blog/index.html` | Exit0; 0 errors/6 existing unrelated orphan-OG warnings |
| `git diff --check` | Exit0 |
| `node /tmp/aictrl-swe-wit/keyword-check.cjs` | Exit0; focused metadata/date/content-preservation/ID/aria/anchor assertions pass |

The 149-character description matches exactly across ordinary/OG/Twitter metadata, WebPage and BlogPosting JSON-LD, feed item and index card. Title, H1, canonical URL, OG URL/image and Twitter image remain unchanged. Original publication remains2 February2026 in JSON-LD, visible byline, card and RSS pubDate; dateModified, visible updated time, card update and sitemap lastmod consistently show22 October2026. Other JSON-LD fields remain identical.

The early definition and natural “What is SWE-EVO, and what does it measure?” heading are present with the existing `what-is-swe-evo` ID. After restoring only the hero date/definition and that heading, the SWE body matches HEAD, preserving findings, rounded numeric claims, methodology, prompts, source URLs and all other content. CSS, results table and token comparison are identical. All external hrefs across the three HTML files are unchanged.

The CLI article body differs only by the single contextual paragraph; its findings tables/figures, metadata and original dates remain unchanged. That paragraph links to both intended SWE definition/exercise anchors and explicitly says the scripted experiment does not establish a SWE-EVO score. All8 local hash references found across changed HTML resolve to one existing target, including those two new links and `/agent#quickstart`. IDs remain unique; aria-labelledby/describedby references resolve.

Root-supplied browser observations, separate from QA's static checks: desktop and375×812 inspections showed the new definition/heading and legible copy. Phone innerWidth375 versus document scrollWidth360 showed no horizontal overflow. Root restored the viewport and left the preview open. QA did not repeat browser automation or claim a new axe/contrast measurement for this copy-only change.

## Checked SHA-256

| Source | SHA-256 |
|---|---|
| `website/public/blog/swe-evo-analysis.html` | `e93fef35dce693cfd0210d9ef16bbc16553fa556691dfcdc6cfd716d9ff2175e` |
| `website/public/blog/headless-coding-agent-cli-benchmark.html` | `9351a15043a569d7128d688d6b1337097a39b63676cfc1eaa29198b4e2336d6d` |
| `website/public/blog/index.html` | `796a769ca7464f00f38cb19b5cc4472b89afcfc286e13c3ebdaf2649070628b9` |
| `website/public/blog/feed.xml` | `be7e964724e1e96dacc747ca83cc38e7bb22338d4acbd66d5eaf7b15bd812bbd` |
| `website/public/sitemap.xml` | `8dc8cc9a514d7e7064fae8751f8005cf146f26288d72719eb6767906867977a1` |

Receipts: `/tmp/aictrl-swe-wit/keyword-{build,focused-tests,html-lint,structural}.log`, `keyword-check.cjs`, `keyword-results.json`. Earlier QA hashes and CI results belong to earlier content. No broad product/backend suite repeated, no new factual web research, ranking/indexing/traffic effect, live release, provider execution or qualified-NSM result claimed. No commits, pushes or external writes by QA.
