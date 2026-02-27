# Datasheet for Skill-MD

Following the template of Gebru et al., "Datasheets for Datasets" (2021).

## Motivation

**For what purpose was the dataset created?**
To evaluate how different instruction formats (plain prose, Markdown, pseudocode) affect LLM code-generation quality. The dataset provides a controlled benchmark where the only experimental variable is the skill-instruction format.

**Who created the dataset and on behalf of which entity?**
The authors of *Pseudocode Beats Prose*, as part of independent research into LLM prompt engineering.

**Who funded the creation of the dataset?**
Self-funded. API costs were the primary expense.

## Composition

**What do the instances that comprise the dataset represent?**
Each instance is a *task*: a JSON file containing a natural-language description of a coding artifact to produce (e.g., a Dockerfile, SQL pipeline, Terraform module, or data-visualization chart specification).

**How many instances are there in total?**
12 tasks across 4 domains (3 tasks per domain).

**Does the dataset contain all possible instances or is it a sample?**
It is a curated selection. Tasks were designed to exercise the full breadth of each domain's evaluation rubric.

**What data does each instance consist of?**
- `task_id` — numeric identifier within the domain
- `domain` — one of: chart, dockerfile, sql-query, terraform
- `description` — natural-language prompt (50-200 words)

**Is there a label or target associated with each instance?**
No ground-truth outputs. Quality is measured by automated rubric evaluation (13-15 binary rules per domain).

**Is any information missing from individual instances?**
No.

**Are relationships between individual instances made explicit?**
Tasks within a domain share the same evaluation rubric and skill files but are otherwise independent.

**Are there recommended data splits?**
No. All 12 tasks are used together. The experimental design crosses tasks with 3 prompt conditions and multiple models.

**Are there any errors, sources of noise, or redundancies?**
Tasks were iteratively refined. Evaluation rubrics were reviewed for inter-rater reliability (details in paper).

**Is the dataset self-contained, or does it link to or otherwise rely on external resources?**
Self-contained. No external APIs, databases, or credentials are required for evaluation.

**Does the dataset contain data that might be considered confidential?**
No.

**Does the dataset contain data that, if viewed directly, might be offensive?**
No.

## Collection Process

**How was the data associated with each instance acquired?**
Tasks were authored by the paper's authors, drawing on professional software engineering experience. Skill files were written to encode domain best practices.

**What mechanisms or procedures were used to collect the data?**
Manual authoring followed by iterative refinement based on pilot evaluations.

**Who was involved in the data collection process?**
The paper's authors.

**Over what timeframe was the data collected?**
January-February 2026.

**Were any ethical review processes conducted?**
Not applicable — the dataset contains only synthetic coding tasks with no human subjects data.

## Preprocessing / Cleaning / Labeling

**Was any preprocessing/cleaning/labeling of the data done?**
Task descriptions were edited for clarity and completeness. Rubric rules were validated against manual evaluation of pilot outputs.

**Was the "raw" data saved in addition to the preprocessed/cleaned/labeled data?**
The current files are the authoritative versions. Version history is available in the git repository.

## Uses

**Has the dataset been used for any tasks already?**
Yes — the experiments reported in *Pseudocode Beats Prose*.

**Is there a repository that links to any or all papers or systems that use the dataset?**
This repository.

**What (other) tasks could the dataset be used for?**
- Benchmarking new LLMs on structured code generation
- Evaluating alternative skill-instruction formats
- Studying the effect of rubric complexity on LLM performance
- Prompt engineering research

**Is there anything about the composition of the dataset or the way it was collected that might impact future uses?**
The 4 domains are all software/infrastructure-focused. Results may not transfer to non-technical domains.

**Are there tasks for which the dataset should not be used?**
Not intended for training LLMs (too small). Not suitable as a general coding benchmark — it specifically measures format sensitivity.

## Distribution

**Will the dataset be distributed to third parties outside of the entity on behalf of which the dataset was created?**
Yes, publicly via this repository.

**How will the dataset be distributed?**
GitHub repository alongside the paper.

**When will the dataset be distributed?**
Upon paper publication.

**Will the dataset be distributed under a copyright or other intellectual property (IP) license?**
CC-BY-4.0. See `LICENSE-DATA`.

**Have any third parties imposed IP-based or other restrictions on the data?**
No.

## Maintenance

**Who will be supporting/hosting/maintaining the dataset?**
The paper's authors, via the GitHub repository.

**How can the owner/curator/manager of the dataset be contacted?**
Via GitHub issues on this repository.

**Will the dataset be updated?**
Additional domains or tasks may be added in future work. The current version is frozen for reproducibility of the published results.

**Will older versions of the dataset continue to be supported/hosted/maintained?**
Yes, via git tags.

**If others want to extend/augment/build on/contribute to the dataset, is there a mechanism for them to do so?**
Pull requests are welcome.
