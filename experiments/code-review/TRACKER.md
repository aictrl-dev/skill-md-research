# Code-Review Research Tracker

> The **[Google Sheet](https://docs.google.com/spreadsheets/d/1txtt4rYQULxMZQHOgOqn8TcAx5bQBPEjknRsDxIUU4Q/edit)**
> is the source of truth (tabs: Hypotheses · Metrics · Results · Schema).
> This file is a human-readable index only.

## Experiments

| # | Experiment | Folder | Status | Headline |
|---|-----------|--------|--------|----------|
| 1 | KG-augmented code review | [`../cr-loop`](../cr-loop/) | complete (single-seed pilot) | +29% F1 (0.300→0.388, ext AK) from a one-paragraph subagent-prompt change (Phase E) |

## How to add an experiment

See [`README.md`](./README.md). Each experiment is its own folder with a frozen
benchmark + answer key; this framework's scripts aggregate its runs into the
shared `Results` tab.
