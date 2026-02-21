# Literature Review: Instruction Format Effects on LLM Performance

**Last updated**: 2026-02-20
**Purpose**: Assess novelty and position the pseudocode vs markdown skill format experiment against existing work.

---

## 1. Prompt Format / Instruction Format Effects (2024-2026)

### He et al. (2024) — "Does Prompt Formatting Have Any Impact on LLM Performance?"
- **Citation**: Jia He, Mukund Rungta, David Koleczek, Arshdeep Sekhon, Franklin X Wang, Sadid Hasan. arXiv:2411.10541, November 2024.
- **Key findings**: Tested plain text, Markdown, JSON, YAML across six benchmarks on GPT-3.5-turbo and GPT-4. Performance varied up to 40% on code translation depending on format. JSON best on average for GPT-3.5; Markdown often optimal for GPT-4. No single format universally excelled.
- **Relevance**: Directly compares structured formats but **excludes pseudocode entirely**. Our work fills this gap.
- **Link**: https://arxiv.org/abs/2411.10541

### Sclar et al. (2024) — "Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design"
- **Citation**: Melanie Sclar, Yejin Choi, Yulia Tsvetkov, Alane Suhr. ICLR 2024 (Conference Paper).
- **Key findings**: Open-source LLMs are extremely sensitive to subtle formatting changes in few-shot settings, with up to 76 accuracy points difference (LLaMA-2-13B). Proposed FormatSpread metric.
- **Relevance**: Quantifies format sensitivity but for few-shot example formatting, not instruction format (markdown vs pseudocode).
- **Link**: https://arxiv.org/abs/2310.11324

### Errica et al. (2025) — "What Did I Do Wrong? Quantifying LLMs' Sensitivity and Consistency to Prompt Engineering"
- **Citation**: Federico Errica, Davide Sanvito, Giuseppe Siracusano, Roberto Bifulco. NAACL 2025 (Long Paper).
- **Key findings**: Two metrics: sensitivity (prediction changes across rephrasings) and consistency (stability within classes). Sensitivity does not require ground truth.
- **Relevance**: Metrics framework for format sensitivity, but applied to classification, not agentic tasks.
- **Link**: https://aclanthology.org/2025.naacl-long.73/

### Ngweta et al. (2025) — "Towards LLMs Robustness to Changes in Prompt Format Styles"
- **Citation**: Lilian Ngweta, Kiran Kate, Jason Tsay, Yara Rizk. NAACL 2025 Student Research Workshop.
- **Key findings**: Proposed Mixture of Formats (MOF), presenting each few-shot example in a distinct style. Boosted Min Accuracy from 0.139 to 0.712 for llama-3-70b-instruct.
- **Relevance**: Format robustness technique, but not pseudocode vs markdown comparison.
- **Link**: https://aclanthology.org/2025.naacl-srw.51/

### Liu et al. (2025) — "Beyond Prompt Content: CFPO"
- **Citation**: Yuanye Liu et al. "Beyond Prompt Content: Enhancing LLM Performance via Content-Format Integrated Prompt Optimization." arXiv:2502.04295, February 2025.
- **Key findings**: CFPO jointly optimizes prompt content AND formatting. Demonstrates format optimization matters independently of content.
- **Relevance**: Treats format as separate optimization axis, but no pseudocode comparison.
- **Link**: https://arxiv.org/abs/2502.04295

---

## 2. Pseudocode Prompting / Instruction for LLMs

### Mishra et al. (2023) — "Prompting with Pseudo-Code Instructions" [MOST DIRECTLY RELEVANT]
- **Citation**: Mayank Mishra, Prince Kumar, Riyaz Bhat, Rudra Murthy, Danish Contractor, Srikanth Tamilselvam. EMNLP 2023 (Main Conference), pp. 15178-15197. (IBM Research)
- **Key findings**: Created pseudo-code prompts for 132 tasks from Super-NaturalInstructions. Pseudocode yielded 7-16 point F1 improvement on classification and 12-38% ROUGE-L improvement. Ablation showed code comments, docstrings, and structural clues all contributed.
- **Models**: BLOOM and CodeGen families.
- **Gap**: Tested on NLP tasks (classification, QA), NOT agentic/tool-use tasks. Did NOT compare pseudocode to other structured formats like markdown — only to natural language.
- **Link**: https://aclanthology.org/2023.emnlp-main.939/

### Kumar et al. (2025) — "Training with Pseudo-Code for Instruction Following"
- **Citation**: Prince Kumar, Rudra Murthy, Riyaz Bhat, Danish Contractor. arXiv:2505.18011, May 2025.
- **Key findings**: Fine-tuned LLMs with pseudo-code augmented training data. 3-19% relative gain on instruction-following benchmarks. Training-time approach, not inference-time prompting.
- **Relevance**: Training-time complement to our inference-time study.
- **Link**: https://arxiv.org/abs/2505.18011

### Chae et al. (2024) — "Language Models as Compilers"
- **Citation**: Hyungjoo Chae et al. EMNLP 2024 (Main Conference), pp. 22471-22502.
- **Key findings**: Think-and-Execute framework using pseudocode as intermediate reasoning representation. Outperformed CoT and PoT on algorithmic reasoning.
- **Relevance**: Uses pseudocode as reasoning format, not instruction format for agents.
- **Link**: https://aclanthology.org/2024.emnlp-main.1253/

### Mishra et al. (2022) — "Reframing Instructional Prompts to GPTk's Language"
- **Citation**: Swaroop Mishra, Daniel Khashabi, Chitta Baral, Yejin Choi, Hannaneh Hajishirzi. Findings of ACL 2022.
- **Key findings**: Reframing prompts (decomposing, itemizing) boosted GPT-3 by 12.5% and GPT-2 by 6.7%. Precursor to pseudocode prompting work.
- **Link**: https://aclanthology.org/2022.findings-acl.50/

---

## 3. Agent Skills Benchmarks

### Li et al. (2026) — "SkillsBench" [KEY COMPARISON]
- **Citation**: Xiangyi Li et al. (40 co-authors from Amazon, BenchFlow, ByteDance, etc.). arXiv:2602.12670, February 2026. Website: skillsbench.ai
- **Key findings**: 86 tasks, 11 domains, 7 agent-model configs, 7,308 trajectories. Curated Skills raise pass rate by 16.2pp. Self-generated Skills provide NO benefit. Smaller models with Skills match larger models without.
- **Gap**: Evaluated skill efficacy (with vs without) but did NOT compare different skill formats. Our work extends SkillsBench by asking "does format matter?"
- **Link**: https://arxiv.org/abs/2602.12670

### Xu & Yan (2026) — "Agent Skills for Large Language Models"
- **Citation**: Renjun Xu, Yang Yan. arXiv:2602.12430, February 2026.
- **Key findings**: Formalizes agent skills as composable packages. Covers architecture, acquisition, security.
- **Relevance**: Theoretical framework for skills but no empirical format comparison.
- **Link**: https://arxiv.org/abs/2602.12430

---

## 4. Chart Generation / Data Visualization with LLMs

### Chen et al. (2024) — "VisEval"
- **Citation**: Nan Chen et al. IEEE TVCG 31(1):1301-1311, 2025. IEEE VIS 2024.
- **Key findings**: 2,524 NL2VIS queries, automated evaluation covering validity, legality, readability.
- **Relevance**: Chart evaluation methodology; our rubric is more focused (15 style rules vs broad legality).
- **Link**: https://arxiv.org/abs/2407.00981

### Tian et al. (2024) — "ChartGPT"
- **Citation**: Yuan Tian et al. IEEE TVCG 2024. IEEE VIS 2024.
- **Key findings**: Step-by-step reasoning pipeline for chart generation. Fine-tuning dataset.
- **Link**: https://arxiv.org/abs/2311.01920

---

## 5. Surveys and Meta-Analyses

### Schulhoff et al. (2024) — "The Prompt Report"
- **Citation**: Sander Schulhoff et al. (31 authors from UMD, OpenAI, Stanford, Microsoft). arXiv:2406.06608, June 2024 (updated Feb 2025).
- **Key findings**: 76+ page survey, 1,500+ papers, taxonomy of 58 text-only prompting techniques. Meta-analysis of prefix-prompting.
- **Gap**: Discusses format dimension but no original experiments comparing formats.
- **Link**: https://arxiv.org/abs/2406.06608

### Sahoo et al. (2024) — "A Systematic Survey of Prompt Engineering"
- **Citation**: Pranab Sahoo et al. arXiv:2402.07927, February 2024 (updated March 2025).
- **Key findings**: 29 prompting techniques categorized by application area.
- **Link**: https://arxiv.org/abs/2402.07927

### Plaat et al. (2025) — "Agentic Large Language Models, a Survey"
- **Citation**: Aske Plaat et al. arXiv:2503.23037, March 2025.
- **Key findings**: Comprehensive survey of agentic LLMs: reason, act, interact.
- **Link**: https://arxiv.org/abs/2503.23037

---

## 6. Related Approaches

### ProgPrompt (Singh et al., 2023)
- Code-like specifications for robotic task planning. Pythonic function headers with available actions.
- **Link**: https://progprompt.github.io/

### AutoManual (Chen et al., NeurIPS 2024)
- Agents autonomously build instruction manuals through interaction. Two agents with a Formulator.
- **Link**: https://arxiv.org/abs/2405.16247

### AgentIF Benchmark
- Agentic instruction following study. Best model followed <30% of instructions perfectly. Performance declined with instruction length.

---

## 7. Novelty Gap Analysis

### What EXISTS in the literature:

| Study | What was compared | Domain | Models |
|-------|-------------------|--------|--------|
| Mishra (EMNLP'23) | Pseudocode vs NL | NLP tasks (classification, QA) | BLOOM, CodeGen |
| He (2024) | Markdown vs JSON vs YAML vs plain | Reasoning, code, translation | GPT-3.5, GPT-4 |
| SkillsBench (2026) | Skills vs no-skills | 86 tasks, 11 domains | 7 agent configs |
| Sclar (ICLR'24) | Format sensitivity | Classification | Open-source LLMs |

### What DOES NOT EXIST (our contribution):

1. **No paper compares pseudocode vs markdown as instruction formats for LLM agents**
2. **No paper compares instruction formats for agent skill/tool instructions** (MCP, Claude skills)
3. **No paper tests instruction format effects on chart/visualization generation**
4. **No paper combines SkillsBench-style methodology (with/without skill) with format comparison**
5. **No paper tests format effects across modern frontier models** (Claude, GLM) on agentic tasks
6. **No paper evaluates instruction format across multiple structured-output domains** (charts + commits + API specs)

---

## 8. Target Venues

| Venue | Fit | Deadline | Notes |
|-------|-----|----------|-------|
| **arXiv preprint** | Immediate | Anytime | Priority claim |
| **EMNLP 2026 Industry Track** | Strong | ~Jun 2026 | Builds on Mishra (2023) lineage |
| **COLM 2026** | Strong | ~May 2026 | New venue, covers instruction design |
| **NAACL SRW or main** | Good | ~Jan 2026 (passed for 2026) | Accepted format papers in 2025 |
| **PromptEng Workshop** (ACM WebConf) | Good | ~Feb yearly | Dedicated workshop |
| **NeurIPS Datasets & Benchmarks** | Stretch | ~May 2026 | If benchmark released |

---

## 9. Key Papers to Cite (Essential Reading List)

1. Mishra et al. (2023) — pseudocode prompting, EMNLP
2. He et al. (2024) — format comparison (no pseudocode)
3. Li et al. (2026) — SkillsBench
4. Sclar et al. (2024) — format sensitivity, ICLR
5. Schulhoff et al. (2024) — The Prompt Report survey
6. Xu & Yan (2026) — agent skills framework
7. Chae et al. (2024) — pseudocode as reasoning, EMNLP

---

*This document will be iteratively updated as new relevant work is found.*
