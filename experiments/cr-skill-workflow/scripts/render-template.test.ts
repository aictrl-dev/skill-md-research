import { renderTemplate } from './render-template.ts';
import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

describe('renderTemplate', () => {
  it('substitutes a simple string artefact', () => {
    const result = renderTemplate('hello {{ pass1.findings }}', {
      pass1: { findings: 'world' },
    });
    assert.equal(result, 'hello world');
  });

  it('JSON-serialises non-string artefacts', () => {
    const findings = [{ file: 'x.ts', line: 1 }];
    const result = renderTemplate('data: {{ pass1.findings }}', {
      pass1: { findings },
    });
    assert.equal(result, `data: ${JSON.stringify(findings, null, 2)}`);
  });

  it('leaves unresolved placeholders intact', () => {
    const result = renderTemplate('{{ missing.key }}', {});
    assert.equal(result, '{{ missing.key }}');
  });

  it('handles multiple substitutions in one template', () => {
    const result = renderTemplate('A={{a.x}} B={{b.y}}', {
      a: { x: '1' },
      b: { y: '2' },
    });
    assert.equal(result, 'A=1 B=2');
  });

  it('handles whitespace inside braces', () => {
    const result = renderTemplate('{{ pass1.findings }}', {
      pass1: { findings: 'ok' },
    });
    assert.equal(result, 'ok');
  });
});
