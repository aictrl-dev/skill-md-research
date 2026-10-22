# Signup email handoff — issue 6439 focused QA

**PASS within static/build/DOM scope.** Worktree `/home/bulat/code/aictrl-signup-email-handoff-6439-20261022`, branch `fix/signup-email-handoff-6439`, base/HEAD `0e6e6b96b27caa7c31e7caa4bb6f9aee4c8c84a7`. Only `website/public/signup.html` is changed. No source edits by QA.

Final SHA-256: `1e589deba3cd1c9c41de3f6a776ceb7c4b1a5a4c193fb2f4466864fff6d56cd4`.

| Command | Result |
|---|---|
| `npm run build:website` | Exit 0; website assets prepared |
| `npx tsx website/tools/lint-marketing-html.ts website/public/signup.html` | Exit 0; 0 errors, 7 existing warnings |
| `npm run test:website -- website/tests/blog-seo-validation.test.ts website/tests/seo-linking.test.ts` | Exit 0; 226 tests /2 files passed |
| `git diff --check` | Exit 0 |
| `node /tmp/aictrl-signup6439-check.cjs` | Exit 0; static handoff, URL/aria/link/scope assertions and scoped axe pass |

Verified no email-entry form/input, submit button, POST method, fetch/XMLHttpRequest/sendBeacon handler in this marketing page. The sole email handoff anchor has the expected label, bare `https://app.aictrl.dev/` href with no query/hash/identity parameters, one valid `aria-describedby="email-next-step"` target, correct next-screen helper text, and decorative aria-hidden icon. GitHub/Google provider links remain exactly `https://app.aictrl.dev/?provider=github` and `https://app.aictrl.dev/?provider=google`; other existing link destinations remain unchanged. No duplicate IDs or dangling aria descriptions; unused input CSS removed.

Axe scope `.card`: **0 violations, 10 passes, 0 incomplete**. `color-contrast` excluded because jsdom lacks paint/layout; no browser contrast/layout claim. The existing missing-PostHog warning is present in the unchanged baseline page; the other six warnings are unrelated orphan OG assets (about/cookies/docs/early-access/privacy/terms). No tracking was added or suppressed.

Receipts: `/tmp/aictrl-signup6439-{build,html-lint,focused-tests,structural}.log`, `/tmp/aictrl-signup6439-check.cjs`, `/tmp/aictrl-signup6439-results.json`.

Limits: validates the marketing page handoff only. No live app navigation, provider execution, email send/delivery, account creation, attribution/qualified-traffic result or release verified. No full product UI/backend suite repeated for this one-page change. Existing source inspection finds email/magic-link handlers, but this report makes no runtime availability claim.

Root-supplied CUA observations (separate from QA's static/jsdom checks): inspected `http://127.0.0.6:3005/signup` at desktop and 375×812. Phone document width375 equals viewport375; provider widths229 and heights52/52/76; no forms/inputs. Original OAuth hrefs unchanged; clean app email href and helper association confirmed. Three Tab presses reached the email anchor with native `outline: auto 1px`. The anchor was not activated and no email sent; viewport reset afterward. These are root's reported browser observations, not independently repeated by QA.
