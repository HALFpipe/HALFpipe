// Exercise bookmark routing with a synthetic URL; no page or participant data is loaded.
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import assert from 'node:assert/strict';
const html = readFileSync(new URL('../qc-legacy-links.html', import.meta.url), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
function visit(hash) {
  const destinations = [];
  const listeners = {};
  const location = {
    href: 'https://example.test/halfpipe/quality-control.html', hash,
    replace(value) { destinations.push(value); }
  };
  runInNewContext(script, { URL, window: {
    location, addEventListener(name, handler) { listeners[name] = handler; }
  } });
  return { destinations, location, listeners };
}
assert.deepEqual(visit('#epi-tsnr').destinations,
  ['https://example.test/halfpipe/qc/tsnr.html#epi-tsnr']);
assert.deepEqual(visit('#summary-2').destinations,
  ['https://example.test/halfpipe/qc/tsnr.html#summary-2']);
assert.deepEqual(visit('#tabset-1-2').destinations,
  ['https://example.test/halfpipe/qc/before-starting.html#tabset-1-2']);
assert.deepEqual(visit('#epi%2Dtsnr').destinations,
  ['https://example.test/halfpipe/qc/tsnr.html#epi-tsnr']);
for (const hash of ['', '#workflow', '#unknown', '#constructor', '#__proto__', '#%invalid']) {
  assert.deepEqual(visit(hash).destinations, []);
}
const current = visit('');
current.location.hash = '#cheat-sheet';
current.listeners.hashchange();
assert.deepEqual(current.destinations,
  ['https://example.test/halfpipe/qc/cheat-sheet.html#cheat-sheet']);
console.log('Bookmark checks passed: sections, subsections, tabs, encoded anchors, unknown anchors, and hash changes.');
