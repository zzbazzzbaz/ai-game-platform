import test from 'node:test';
import assert from 'node:assert/strict';

import { clamp } from '../src/logic.js';

// 【生成区】模板示例用例：真实游戏逻辑测试请替换/追加到 tests/ 下。
test('logic：clamp 边界', () => {
  assert.equal(clamp(5, 0, 10), 5);
  assert.equal(clamp(-1, 0, 10), 0);
  assert.equal(clamp(99, 0, 10), 10);
});
