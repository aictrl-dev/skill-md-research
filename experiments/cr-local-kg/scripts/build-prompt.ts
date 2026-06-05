// Build the reviewer's user message for a task: review instructions + each file inlined.
import * as fs from 'node:fs';
import * as path from 'node:path';

/** review instructions (review.md) followed by every target file inlined as a fenced block. */
export function buildPrompt(reviewMd: string, repoDir: string, paths: string[]): string {
  const blocks = paths.map((p) => {
    const full = path.join(repoDir, p);
    if (!fs.existsSync(full)) {
      throw new Error(`build-prompt: file not found in repo: ${p}`);
    }
    const content = fs.readFileSync(full, 'utf8');
    return `\n--- FILE: ${p} ---\n\`\`\`\n${content}\n\`\`\`\n`;
  });
  return `${reviewMd}\n\n# CODE UNDER REVIEW\n${blocks.join('\n')}`;
}

// CLI: build-prompt.ts --repo <dir> --paths a.ts,b.ts [--review prompts/review.md]
if (import.meta.url === `file://${process.argv[1]}`) {
  const a: Record<string, string> = {};
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i].startsWith('--')) { a[argv[i].slice(2)] = argv[i + 1] ?? ''; i += 1; }
  }
  const reviewPath = a.review ?? new URL('../prompts/review.md', import.meta.url).pathname;
  const reviewMd = fs.readFileSync(reviewPath, 'utf8');
  process.stdout.write(buildPrompt(reviewMd, a.repo, a.paths.split(',')));
}
