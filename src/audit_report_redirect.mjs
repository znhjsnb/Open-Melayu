// Redirect only the test's machine-report output into this writable workspace.
// Test modules, assertions, dataset reads, and HTTP behavior stay unchanged.
import fs from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { syncBuiltinESMExports } from 'node:module';

const source = resolve('C:/Users/d/Documents/dict/.tmp');
const target = fileURLToPath(new URL('../data/hallucination_audit/test-output/', import.meta.url));
const pathOf = value => value instanceof URL ? fileURLToPath(value) : String(value);
const same = (a, b) => resolve(a).toLowerCase() === resolve(b).toLowerCase();
const mkdir = fs.mkdir.bind(fs);
const writeFile = fs.writeFile.bind(fs);
fs.mkdir = (path, ...args) => mkdir(same(pathOf(path), source) ? target : path, ...args);
fs.writeFile = (path, ...args) => writeFile(
  same(pathOf(path), resolve(source, 'frontend-module-results.json'))
    ? resolve(target, 'frontend-module-results.json') : path, ...args);
syncBuiltinESMExports();
