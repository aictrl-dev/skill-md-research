/**
 * Results-row contract for the code-review research framework.
 * Single source of truth shared by aggregate.ts and sync-sheet.ts.
 * RESULTS_COLUMNS MUST stay identical to the "Results" tab header in the Sheet.
 */

export const RESULTS_COLUMNS = [
  'R-ID', 'Experiment', 'H-ID', 'Variant / Phase', 'Skill Version', 'Model',
  'KG State', 'AnswerKey Version', 'N PRs', 'TP', 'FP', 'FN', 'Novels',
  'Precision', 'Recall', 'F1', 'Δ F1 vs Baseline', 'Cost', 'Log Link',
] as const;

export const KG_STATES = ['empty', 'populated'] as const;
export type KgState = (typeof KG_STATES)[number];

export const ANSWER_KEY_VERSIONS = ['orig', 'extended'] as const;
export type AnswerKeyVersion = (typeof ANSWER_KEY_VERSIONS)[number];

export interface ResultsRow {
  rId?: string; // assigned at MCP write time; blank from the scripts
  experiment: string;
  hId: string;
  variant: string;
  skillVersion: string;
  model: string;
  kgState: KgState;
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
  cost: string; // tokens / $ ; blank when no run-meta
  logLink: string;
}

export interface ValidateOpts {
  /** When supplied, the row's hId MUST be a member (prevents orphan Results). */
  knownHids?: string[];
}

const REQUIRED_STRINGS: ReadonlyArray<keyof Pick<ResultsRow,
  'experiment' | 'variant' | 'skillVersion' | 'model'>> = [
  'experiment', 'variant', 'skillVersion', 'model',
];
const REQUIRED_NUMBERS: ReadonlyArray<keyof Pick<ResultsRow,
  'nPrs' | 'tp' | 'fp' | 'fn' | 'novels' | 'precision' | 'recall' | 'f1'>> = [
  'nPrs', 'tp', 'fp', 'fn', 'novels', 'precision', 'recall', 'f1',
];

function inTuple<T extends string>(tuple: readonly T[], v: string): v is T {
  return (tuple as readonly string[]).includes(v);
}

export function validateResultsRow(row: ResultsRow, opts: ValidateOpts = {}): void {
  for (const k of REQUIRED_STRINGS) {
    if (typeof row[k] !== 'string' || row[k].trim() === '') {
      throw new Error(`Results row invalid: '${k}' must be a non-empty string`);
    }
  }
  if (!/^H-\d+$/.test(row.hId)) {
    throw new Error(`Results row invalid: H-ID '${row.hId}' must match /^H-\\d+$/`);
  }
  if (!inTuple(KG_STATES, row.kgState)) {
    throw new Error(`Results row invalid: KG State '${row.kgState}' not in ${KG_STATES.join(' | ')}`);
  }
  if (!inTuple(ANSWER_KEY_VERSIONS, row.answerKeyVersion)) {
    throw new Error(`Results row invalid: AnswerKey Version '${row.answerKeyVersion}' not in ${ANSWER_KEY_VERSIONS.join(' | ')}`);
  }
  for (const k of REQUIRED_NUMBERS) {
    if (typeof row[k] !== 'number' || !Number.isFinite(row[k])) {
      throw new Error(`Results row invalid: '${k}' must be a finite number`);
    }
  }
  if (row.deltaF1 !== null && (typeof row.deltaF1 !== 'number' || !Number.isFinite(row.deltaF1))) {
    throw new Error(`Results row invalid: 'deltaF1' must be a finite number or null`);
  }
  if (opts.knownHids && !opts.knownHids.includes(row.hId)) {
    throw new Error(`Results row invalid: H-ID '${row.hId}' not found among known hypotheses [${opts.knownHids.join(', ')}]`);
  }
}

/** Render a row into a 19-cell array in exact RESULTS_COLUMNS order. */
export function toCellArray(row: ResultsRow): (string | number)[] {
  const blankIfNull = (v: number | null): string | number => (v === null ? '' : v);
  return [
    row.rId ?? '',
    row.experiment,
    row.hId,
    row.variant,
    row.skillVersion,
    row.model,
    row.kgState,
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
  ];
}
