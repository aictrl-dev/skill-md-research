/**
 * Row contracts for the code-review research framework.
 * Single source of truth shared by aggregate.ts and sync-sheet.ts.
 *
 * EXPERIMENTS_COLUMNS MUST stay identical to the "Experiments" tab header, and
 * CLASS_BREAKDOWN_COLUMNS to the "ClassBreakdown" tab header, in the Sheet:
 * https://docs.google.com/spreadsheets/d/1txtt4rYQULxMZQHOgOqn8TcAx5bQBPEjknRsDxIUU4Q
 */

export const EXPERIMENTS_COLUMNS = [
  'E-ID', 'Experiment', 'H-ID', 'Variant / Phase', 'Skill Version', 'Model',
  'Tool/Context Config', 'AnswerKey Version', 'N PRs', 'TP', 'FP', 'FN', 'Novels',
  'Precision', 'Recall', 'F1', 'Δ F1 vs Baseline', 'Cost', 'Log Link',
  'SNR', 'Latency (p50/p95 ms)', 'Tokens/PR', 'Annotation Coverage', 'Seed',
  'Significance',
] as const;

export const CLASS_BREAKDOWN_COLUMNS = [
  'E-ID', 'Experiment', 'H-ID', 'AnswerKey Version', 'Defect Class',
  'TP', 'FP', 'FN', 'Precision', 'Recall', 'F1', 'Notes',
] as const;

export const ANSWER_KEY_VERSIONS = ['orig', 'extended'] as const;
export type AnswerKeyVersion = (typeof ANSWER_KEY_VERSIONS)[number];

/** Allowed Annotation-Coverage bands (Python H-016 stratifier). '' = N/A (e.g. C#). */
export const ANNOTATION_COVERAGES = ['none', 'sparse', 'partial', 'dense'] as const;
export type AnnotationCoverage = (typeof ANNOTATION_COVERAGES)[number];

/** Δ-F1 significance verdict. '' until a baseline exists. */
export const SIGNIFICANCES = ['confirmed', 'inconclusive', 'noise'] as const;
export type Significance = (typeof SIGNIFICANCES)[number];

/** Canonical defect-class taxonomy for the ClassBreakdown tab (C# + Python). */
export const DEFECT_CLASSES = [
  'security', 'injection', 'authz', 'crypto', 'async-concurrency', 'null-safety',
  'resource-mgmt', 'exception-handling', 'api-contract', 'supply-chain',
  'dynamic-typing', 'memory-lifecycle', 'performance', 'style', 'other',
] as const;
export type DefectClass = (typeof DEFECT_CLASSES)[number];

export interface ExperimentRow {
  eId?: string; // assigned at MCP write time; blank from the scripts
  experiment: string;
  hId: string;
  variant: string;
  skillVersion: string;
  model: string;
  toolContextConfig: string; // free string, e.g. 'KG:populated', 'annot:dense'
  answerKeyVersion: AnswerKeyVersion;
  nPrs: number;
  tp: number;
  fp: number;
  fn: number;
  novels: number;
  precision: number;
  recall: number;
  f1: number;
  deltaF1: number | null; // blank when no baseline supplied
  cost: string; // $ for the sweep; blank when no run-meta
  logLink: string;
  snr: number | null; // TP/FP; null when FP === 0
  latency: string; // 'p50/p95' ms; blank when not captured
  tokensPerPr: number | null; // blank when not captured
  annotationCoverage: AnnotationCoverage | ''; // '' for C# / N/A
  seed: string; // RNG/sampling seed(s); blank when N/A
  significance: Significance | ''; // '' until a baseline exists
}

export interface ClassBreakdownRow {
  eId?: string;
  experiment: string;
  hId: string;
  answerKeyVersion: AnswerKeyVersion;
  defectClass: DefectClass;
  tp: number;
  fp: number;
  fn: number;
  precision: number;
  recall: number;
  f1: number;
  notes: string;
}

export interface ValidateOpts {
  /** When supplied, the row's hId MUST be a member (prevents orphan rows). */
  knownHids?: string[];
}

const REQUIRED_STRINGS: ReadonlyArray<keyof Pick<ExperimentRow,
  'experiment' | 'variant' | 'skillVersion' | 'model' | 'toolContextConfig'>> = [
  'experiment', 'variant', 'skillVersion', 'model', 'toolContextConfig',
];
const REQUIRED_NUMBERS: ReadonlyArray<keyof Pick<ExperimentRow,
  'nPrs' | 'tp' | 'fp' | 'fn' | 'novels' | 'precision' | 'recall' | 'f1'>> = [
  'nPrs', 'tp', 'fp', 'fn', 'novels', 'precision', 'recall', 'f1',
];

function inTuple<T extends string>(tuple: readonly T[], v: string): v is T {
  return (tuple as readonly string[]).includes(v);
}

const isFiniteNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);

export function validateExperimentRow(row: ExperimentRow, opts: ValidateOpts = {}): void {
  for (const k of REQUIRED_STRINGS) {
    if (typeof row[k] !== 'string' || row[k].trim() === '') {
      throw new Error(`Experiment row invalid: '${k}' must be a non-empty string`);
    }
  }
  if (!/^H-\d+$/.test(row.hId)) {
    throw new Error(`Experiment row invalid: H-ID '${row.hId}' must match /^H-\\d+$/`);
  }
  if (!inTuple(ANSWER_KEY_VERSIONS, row.answerKeyVersion)) {
    throw new Error(`Experiment row invalid: AnswerKey Version '${row.answerKeyVersion}' not in ${ANSWER_KEY_VERSIONS.join(' | ')}`);
  }
  for (const k of REQUIRED_NUMBERS) {
    if (!isFiniteNum(row[k])) {
      throw new Error(`Experiment row invalid: '${k}' must be a finite number`);
    }
  }
  if (row.deltaF1 !== null && !isFiniteNum(row.deltaF1)) {
    throw new Error(`Experiment row invalid: 'deltaF1' must be a finite number or null`);
  }
  if (row.snr !== null && !isFiniteNum(row.snr)) {
    throw new Error(`Experiment row invalid: 'snr' must be a finite number or null`);
  }
  if (row.tokensPerPr !== null && !isFiniteNum(row.tokensPerPr)) {
    throw new Error(`Experiment row invalid: 'tokensPerPr' must be a finite number or null`);
  }
  if (row.annotationCoverage !== '' && !inTuple(ANNOTATION_COVERAGES, row.annotationCoverage)) {
    throw new Error(`Experiment row invalid: Annotation Coverage '${row.annotationCoverage}' not in ('' | ${ANNOTATION_COVERAGES.join(' | ')})`);
  }
  if (row.significance !== '' && !inTuple(SIGNIFICANCES, row.significance)) {
    throw new Error(`Experiment row invalid: Significance '${row.significance}' not in ('' | ${SIGNIFICANCES.join(' | ')})`);
  }
  if (opts.knownHids && !opts.knownHids.includes(row.hId)) {
    throw new Error(`Experiment row invalid: H-ID '${row.hId}' not found among known hypotheses [${opts.knownHids.join(', ')}]`);
  }
}

export function validateClassBreakdownRow(row: ClassBreakdownRow, opts: ValidateOpts = {}): void {
  if (typeof row.experiment !== 'string' || row.experiment.trim() === '') {
    throw new Error(`ClassBreakdown row invalid: 'experiment' must be a non-empty string`);
  }
  if (!/^H-\d+$/.test(row.hId)) {
    throw new Error(`ClassBreakdown row invalid: H-ID '${row.hId}' must match /^H-\\d+$/`);
  }
  if (!inTuple(ANSWER_KEY_VERSIONS, row.answerKeyVersion)) {
    throw new Error(`ClassBreakdown row invalid: AnswerKey Version '${row.answerKeyVersion}' not in ${ANSWER_KEY_VERSIONS.join(' | ')}`);
  }
  if (!inTuple(DEFECT_CLASSES, row.defectClass)) {
    throw new Error(`ClassBreakdown row invalid: Defect Class '${row.defectClass}' not in ${DEFECT_CLASSES.join(' | ')}`);
  }
  for (const k of ['tp', 'fp', 'fn', 'precision', 'recall', 'f1'] as const) {
    if (!isFiniteNum(row[k])) {
      throw new Error(`ClassBreakdown row invalid: '${k}' must be a finite number`);
    }
  }
  if (opts.knownHids && !opts.knownHids.includes(row.hId)) {
    throw new Error(`ClassBreakdown row invalid: H-ID '${row.hId}' not found among known hypotheses [${opts.knownHids.join(', ')}]`);
  }
}

const blankIfNull = (v: number | null): string | number => (v === null ? '' : v);

/** Render an ExperimentRow into a 25-cell array in exact EXPERIMENTS_COLUMNS order. */
export function toExperimentCellArray(row: ExperimentRow): (string | number)[] {
  return [
    row.eId ?? '',
    row.experiment,
    row.hId,
    row.variant,
    row.skillVersion,
    row.model,
    row.toolContextConfig,
    row.answerKeyVersion,
    row.nPrs,
    row.tp,
    row.fp,
    row.fn,
    row.novels,
    row.precision,
    row.recall,
    row.f1,
    blankIfNull(row.deltaF1),
    row.cost,
    row.logLink,
    blankIfNull(row.snr),
    row.latency,
    blankIfNull(row.tokensPerPr),
    row.annotationCoverage,
    row.seed,
    row.significance,
  ];
}

/** Render a ClassBreakdownRow into a 12-cell array in exact CLASS_BREAKDOWN_COLUMNS order. */
export function toClassBreakdownCellArray(row: ClassBreakdownRow): (string | number)[] {
  return [
    row.eId ?? '',
    row.experiment,
    row.hId,
    row.answerKeyVersion,
    row.defectClass,
    row.tp,
    row.fp,
    row.fn,
    row.precision,
    row.recall,
    row.f1,
    row.notes,
  ];
}
