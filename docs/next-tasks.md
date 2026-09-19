# 接下来的任务:跑通单人游戏闭环

> 目标:单人游戏"生成 → 试玩 → 观测 → 反馈 → 修复 → 新版"闭环全链路打通。
> 联机是 Phase 5,本期只做零成本预留。

## 已定基线

- **引擎**:Phaser 3 锁定版本;官方 phaser skills(14 个,在 `docs/skills/`)作为生成知识源
- **产物**:agent 编辑多文件 Phaser 工程 → esbuild 打包为**单文件** `dist/index.html` 交付
- **Runtime 收口**:游戏代码只调用平台 Runtime API(遥测/输入/存档/测试模式/net 占位),不碰网络、不碰引擎底层
- **沙箱**:Modal,镜像内离线依赖(node / phaser / esbuild / playwright+chromium)
- **框架边界**:游戏产物不用 React;React 只用于平台自身 UI

## 第一步结论:先定契约,镜像紧随其后

沙箱镜像是第一个可落地的工程件,但镜像 = 契约的打包,先花半天做 Phase 0,否则镜像装了也白装。

---

## Phase 0 契约(半天)

- [ ] Runtime API 草案(`track / net / save / test` 接口签名)
- [ ] 工程模板目录结构(见下)
- [ ] 版本锁定清单(node LTS / Phaser 3.x / esbuild / playwright)

```
/workspace/work/
├── index.html
├── src/
│   ├── main.js          # Phaser 配置 + 场景注册
│   ├── scenes/*.js
│   └── events.js        # Runtime.track 语义事件
├── assets/              # 用户素材(引用 /workspace/input)
├── tests/smoke.test.js  # 平台模板,agent 不许改
└── package.json         # 依赖锁定
```

## Phase 1 沙箱镜像(第一个工程交付)

- [ ] 定义 Modal Image:debian_slim + node + 离线依赖(phaser/esbuild/playwright+chromium),构建并打版本 tag
- [ ] 镜像只装"工具";runtime 与模板走同步机制(复用 `skill_sync` 模式),不进镜像
- [ ] `api_server` 的 `ModalGateway._create` 改用该镜像(当前未指定 image,用的默认镜像)
- [ ] 验收:hello-phaser 工程在沙箱内跑通 build + headless 测试

## Phase 2 平台运行时 + 工程模板

- [ ] `runtime.js`:错误捕获、场景生命周期自动上报、输入统计(rage click/静默)、`track()` 语义事件、存档、测试模式(固定时钟+种子)、net 占位
- [ ] 工程模板(main/scenes/tests/package.json/index.html)
- [ ] 测试模板两层:Phaser HEADLESS 逻辑冒烟 + Playwright 真渲染冒烟
- [ ] 构建脚本:esbuild → `dist/index.html`
- [ ] runtime/模板同步进沙箱的机制

## Phase 3 agent 侧改造

- [ ] skill 重写为 `phaser-project`:短 SKILL.md + references(runtime API / 模板速查 / 示例游戏)
- [ ] 官方 phaser skills 子集挂载到 `/skills`
- [ ] prompt 更新:设计审批 → 工程实现 → 测试门禁 → 构建 → 交付
- [ ] 硬约束:`permissions`(input 只读等)、execute 超时下调、summarization 阈值修正
- [ ] 交付前 rubric 自评(验收清单)
- [ ] 端到端冒烟:生成一个能玩的游戏,测试全过

## Phase 4 单人反馈闭环(本期终点)

- [ ] 播放器壳页(同源 wrapper):错误捕获、输入统计、事件转发
- [ ] `api_server`:遥测接收 endpoint + 存储 + 触发策略
- [ ] 证据包(报错栈+最近操作+反馈+当前代码)→ 修复 run
- [ ] HITL 双轨:`publish_hotfix` 自动 / `propose_update` 需批准
- [ ] 版本化发布 + 一键回滚
- [ ] LangSmith 评估集:evaluator(产物合规/轨迹/质量)
- [ ] 验收:玩 → 出错 → agent 收到证据包 → 修复 → 新版可玩

## Phase 5 后续(不在本期)

- 联机回合制试点:房间服务(FastAPI/WS + Redis)+ `Runtime.net` 实体化
- 逻辑/渲染分离与 net 占位已在模板预留,单人期零成本

## 明确不做

- 高频实时竞技联机(格斗/射击类)
- React 或其他框架进入游戏产物
- 多引擎支持(只锁 Phaser 3)
