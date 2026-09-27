// 【模板】门禁：G1' 构建 + G2 逻辑单测 + G7 静态约束。
// G4（无头浏览器冒烟）在 M2 接入，届时用本工程 devDependency 里的 playwright。
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { readdir, readFile } from 'node:fs/promises';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

function run(args) {
  const result = spawnSync(process.execPath, args, { cwd: root, stdio: 'inherit' });
  if (result.status !== 0) {
    throw new Error(`失败：node ${args.join(' ')}`);
  }
}

async function collectSources(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await collectSources(full)));
    } else if (/\.(js|mjs)$/.test(entry.name)) {
      files.push(full);
    }
  }
  return files;
}

const FORBIDDEN = [
  [/\bhttps?:\/\//, '绝对地址 http(s)://'],
  [/\bwss?:\/\//, '绝对地址 ws(s)://'],
  [/\blocalhost\b/, '写死 localhost'],
  [/\b127\.0\.0\.1\b/, '写死 127.0.0.1'],
  [/\bfrom\s+['"](node:)?fs['"]|require\(\s*['"](node:)?fs['"]\s*\)/, '客户端引用 fs'],
];

async function staticChecks() {
  const violations = [];
  for (const file of await collectSources(join(root, 'src'))) {
    const text = await readFile(file, 'utf8');
    for (const [pattern, label] of FORBIDDEN) {
      if (pattern.test(text)) {
        violations.push(`${relative(root, file)}: ${label}`);
      }
    }
  }

  const dist = join(root, 'dist/index.html');
  if (!existsSync(dist)) {
    violations.push('缺少 dist/index.html');
  } else {
    const html = await readFile(dist, 'utf8');
    // 去掉内联脚本内容后再检查，避免把打包产物里的 JS 字符串当成 HTML 标签
    const markup = html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '<script></script>');
    if (/<script\b[^>]*\bsrc=/i.test(markup) || /<link\b[^>]*\bhref=/i.test(markup)) {
      violations.push('dist/index.html 仍引用外部脚本/样式，未内联');
    }
    if (!/[\u4e00-\u9fa5]/.test(html)) {
      violations.push('缺少中文文案');
    }
  }

  if (violations.length) {
    console.error('G7 静态约束未通过：\n- ' + violations.join('\n- '));
    process.exit(1);
  }
}

run(['--test']); // G2
run(['scripts/build.mjs']); // G1'
await staticChecks(); // G7
console.log('gate 通过（G1\', G2, G7）');
