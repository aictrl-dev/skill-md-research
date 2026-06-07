# How the commercial field reports itself — and where this work differs

A factual comparison of public AI-code-review claims against the methodological choices in
this work. Sources are web-cited; several are 2026-dated vendor/benchmark posts that should
be re-confirmed before external publication. The point of this document is **not** to claim
superiority — it is to make the methodological contrast explicit and let it stand on
evidence.

## What vendors actually publish

| Vendor / source | Architecture | Model | Reports **recall**? | Headline framing | Reproducible / independent? |
|---|---|---|---|---|---|
| CodeRabbit | agentic loop; 50+ linters/SAST inline + verification agent | frontier cloud | via Martian (R 53.5%) | "less noise" (but recall-leaning) | 3rd-party (Martian) |
| Greptile | repo dependency-graph; agentic v3 | Claude | self: 82% "catch rate" | recall/coverage | **no — 45% when re-run by a 3rd party** |
| Qodo | ~12 specialist agents | frontier cloud | self: R 56.7%, F1 60.1% | best-F1 | self-run benchmark |
| Graphite Diamond | whole-repo context, feedback learning | undisclosed | **no** (precision only) | "<3% false positives" | self/internal |
| CodeAnt | RAG index + 3-LLM ≥2 consensus + SAST | 3 undisclosed | via Martian (R 51.1%) | low-FP + recall | 3rd-party (Martian) |
| Cursor BugBot | **v1: parallel passes + majority vote + validator** → v2 agentic | undisclosed | **no** (resolution rate) | reversed precision→recall | self |
| GitHub Copilot Autofix | **CodeQL dataflow grounds the LLM** | GPT-4o | **no** (fix-coverage) | fix acceptance | self |
| Amazon CodeGuru | automated-reasoning dataflow (source→sink) | proprietary ML | **no** | "low false positives" | none published |
| Diffblue (tests) | RL + **executes tests** (no LLM) | RL | coverage analog | determinism | partial |
| Google (ICSE'24) / Meta (arXiv 2507.13499) | ML resolves reviewer comments | seq models / Llama-70B FT | **no** (applied-rate) | adoption | peer-reviewed |
| Korbit, Snyk, Codacy, Sourcegraph, Baz, Panto, Bito, Ellipsis, Cubic | various (specialist agents, RAG, SAST) | mostly frontier cloud | **no** | precision/low-noise (mostly) | marketing only |

## The methodological problems in the public record

1. **Recall is almost never reported.** Most "metrics" are precision/false-positive rate
   ("<3% FPR"), *coverage* on a self-chosen bug list, or a *usefulness proxy* ("did the
   developer change the code after the comment"). Of the vendors surveyed, only Qodo (self)
   and the independent Martian benchmark report defensible precision **and** recall, topping
   out around 50–60% F1.
2. **Self-run benchmarks don't reproduce.** The cleanest demonstration: Greptile reported
   82% recall on 50 PRs; a third party (Augment) re-ran the *same repos* and got 45%. The
   field has no shared, SWE-bench-style standard; vendors "each run their own benchmark and
   win."
3. **No shared oracle.** Ground truth is variously: injected bugs, self-curated comment
   lists, three frontier LLMs voting, or post-hoc "did the dev act on it." None separates
   *user-impacting* defects from *technically-correct-but-noise* findings.
4. **Precision is bought with external tools, not prompting.** The vendors with credible
   low-false-positive numbers anchor on **objective external evidence**: CodeRabbit (50+
   linters + verification agent), Copilot Autofix (CodeQL dataflow), CodeGuru (automated
   reasoning), Cubic (static-typing verification), Diffblue (actually runs tests). Pure-LLM
   reviewers fight false positives with model-side tricks (voting, validator models, prompt
   restraint).

## Where this work differs (stated as choices, not as superiority)

- **We report recall, and a recall-weighted objective (F2).** The public field is
  precision/noise-anchored; recall is the metric most often omitted. Ours is front and centre
  because single-pass review is recall-bound.
- **We define the oracle and split it** into full vs *user-impacting* (real-bug) sets, with
  FALSE entries so hallucinations cost precision — rather than a usefulness proxy.
- **We publish negative results** (judge, confidence, consensus-vote, proof-obligation,
  thinking, KG all fail to move F2). No vendor publishes what *didn't* work.
- **We disclose our own evaluation bugs** (scratch contamination, a fail-open treatment that
  silently became the control, over-lenient matching) and the invariants that catch them.
  Self-disclosed eval failures are the opposite of marketing.
- **We use a local ~12B model.** Every disclosed LLM reviewer in the field runs frontier
  cloud (the lone non-frontier paths are non-LLM, e.g. CodeGuru/Diffblue, or a fine-tuned
  70B). No public work demonstrates a small *local* model doing competitive detection review.

## Two honest checks against over-claiming

- **An ensemble-vote design is not novel and has a cautionary precedent.** Cursor BugBot v1
  was essentially our shape (parallel passes + randomized order + majority vote + validator)
  and Cursor *moved away from it* toward a single agentic loop — at the **frontier** tier,
  where one strong pass dominates. Our bet is specific to the *small-local* tier, where a
  single pass is weak; we should not generalise it to frontier models.
- **Our study is small.** One model, one 20-task TypeScript benchmark, mostly single-rep
  (±~0.05 F2), an oracle partly authored by a model we also benchmark. We are *more rigorous
  than most published vendor eval on the axes above* — defined oracle, reported recall,
  negative results, disclosed bugs — and *less rigorous on scale* (no large real-PR traffic,
  no multi-rep significance yet). Both are true and both belong in any write-up.

The defensible summary is therefore narrow and evidence-based: **this is a small but
methodologically transparent study of a local small model, reporting the metric (recall) and
the failures the commercial field generally omits — not a state-of-the-art claim.**
