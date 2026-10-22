# Landing-page work ready for implementation

These are copy and evidence briefs. They have not changed the product repository or production site. Preserve aictrl's restrained typography, flat corners and readable Words in Table layouts. Use diagrams for actual relationships or flow; avoid decorative colored boxes and repeated labels.

## Make the working clients discoverable

Current `/plugins` has a relevant integrations title but does not name ChatGPT or Claude.ai in its inspected body. `/docs/plugin-setup` explains Claude.ai setup; ChatGPT is mentioned in authentication text without its own setup section. Founder confirmation that both work is enough to prepare accurate copy, but not to invent install instructions or marketplace approval.

Proposed page title: **Engineering plugins and integrations | aictrl.dev**. Proposed description: **Use aictrl engineering skills and workflows from Claude.ai, ChatGPT and coding tools. Choose your client and follow its setup guide.** Confirm the rendered page actually fulfills that promise before publishing.

Opening copy to review: “Bring aictrl engineering workflows into the tools you already use. Choose a client, connect your workspace and start with a concrete task: review a change, explain a pull request or run a delivery workflow.” Use only tasks supported in the tested client; do not imply every skill works identically everywhere.

| Client entry | What the reader should learn | Useful next step |
| --- | --- | --- |
| Claude.ai | How the custom connector authenticates, what workspace access it receives and which tested task to try | Link to the existing `#claude-ai` setup section and the exact supported connection method |
| ChatGPT | Which currently supported installation path to use and what result to expect | Add a dedicated tested setup section, then link directly to it |
| Claude Code / Codex | Whether they need standalone local skills or the packaged integration | Show the existing canonical package instructions and scope |
| OpenCode and other editors | The actual supported skills/configuration path and any client-specific limits | Follow current README/docs rather than stale adapter-only instructions |
| Terminal / CI | What the headless CLI executes and how to inspect the result | Link to `/agent`, public source and a successful short demonstration |

For the new ChatGPT section, record the current UI path from a successful installation before writing numbered steps. Include required account/workspace conditions, expected permission prompt, first task, expected result, disconnect path and a specific troubleshooting link. Keep test accounts and credentials out of public docs. “Works in ChatGPT” and “listed in the ChatGPT directory” are separate claims.

An effective first task should work in a few minutes against sample/public-safe data. Use a real prompt and result from the tested package, with a compact screenshot or before/after table. A generic marketing animation is weaker evidence than a visible reviewed change and its validation.

## Give software-factory language a concrete meaning

Use `/ai-sdlc` for delivery intent. A useful opening promise is: “Make delivery work repeatable: connect the issue, the plan, execution, review and validation evidence.” Show which steps aictrl performs and where a person decides. Do not imply fully autonomous releases or guaranteed delivery gains.

Suggested table:

| Delivery step | Concrete artifact to show | Reader takeaway |
| --- | --- | --- |
| Define the task | One bounded issue and acceptance criteria | How to specify work the agent can verify |
| Plan and execute | Actual workflow definition and one execution | How skills and tools are selected for a repeatable path |
| Review the change | A specific finding linked to changed code | How review influences the patch rather than adding generic commentary |
| Validate and learn | A test/result and a concise explanation | What changed, why it matters and how the next run improves |

One small flow diagram can connect these artifacts. Every node must correspond to working behavior. Link to the relevant workflow, review and knowledge pages instead of repeating several broad paragraphs of “AI automation.”

Keep a software-factory explanation in the body where it helps the reader; avoid stuffing SDLC, AISDLC, DORA and AI-DORA into the same title. Delivery metrics require a dedicated capability/definition and evidence review before becoming part of the promise.

## Turn review and skill pages into a useful trial

For `/features/code-review`, show a real bug or missed constraint, the finding, the fix, and the validation. For explain-change, show how a short diagram or mapping table makes the PR understandable. Explain the limits of the example and what the reader can try in their own repository.

For skill discovery, link directly to one canonical skill and its local install/use instructions. Describe prerequisites and whether a hosted connection is necessary. The standalone public skills path should not be presented as requiring an aictrl account if it can run locally.

For `/agent`, show a terminal input, resulting artifact and how to inspect failure. Avoid asking a visitor to infer the useful outcome from CLI flags alone. Current package identity and commands must come from the public CLI manifest/README at implementation time.

## Review before publication

Check actual client setup, links, mobile table readability, canonical/title/description and the visible first task. Read all numeric claims: use compact prose such as 1.3k or a meaningful percentage when precision does not help, while retaining exact machine counts in research data. Distinguish demonstrated results from hypotheses and link to the supporting experiment where a result is claimed.

Use the existing blog writing and UI polish workflows when implementing. No application lockfile change, research harness or analytics replatforming is necessary to ship these copy and evidence improvements.
