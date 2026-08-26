# L07 实验探针套件（预注册声明）

**定稿时间：2026-08-20 20:30 左右，两组构建 20:24 发派后立即写成，此刻两组均无一行实现代码。**
定稿后到两组交付前，探针断言与判定逻辑不改；只允许在交付后补写 `adapters/`（形状映射，
依据各自 README 的 API 一览，不读 src，规则见 `adapters/README.md`）。

旧探针（三路径实验的 probe.mjs / hard.mjs / evil.mjs）已被删除，本套按同一口径重建：
12 条统一探针 + 3 条硬探针 + 恶意上游。**A/B 两组吃同一套，组间对比不受重建影响。**

## 跑法

```bash
node probe.mjs adapters/path4.mjs    # 12 条统一探针（A 组；B 组换 path5）
node hard.mjs  adapters/path4.mjs    # H1 并发丢失更新 / H2 重试安全 / H3 CSS 陷阱
node evil.mjs  adapters/path4.mjs    # E1 链路真实 / E2 key 不透传
```

## 计量口径（预注册）

- **质量分** = 12 条统一探针通过数（主指标）；硬探针 3 + evil 2 另列（次指标，测「没人问到的地方」）。
- **行数**：`*.js|*.mjs|*.cjs|*.css|*.html` 全计，排除 `node_modules/`、`DEMO-REFERENCE.html`、
  `.my-loop/`、`docs/`、`package-lock.json`。含测试与前端（两组同口径）。
- **token**：解析两组 agent 的 transcript JSONL，逐条累加 usage 四项，同一脚本跑两组。
- **墙钟**：发派 20:24:03 起，至各自完成通知；细分时间戳看各自 CURRENT.md 竖切表。
- **判读**：按 `../L07对照实验设计.md` §4 预注册规则，探针分差 ≤1 视为打平，跑完不许挪门槛。

## 与锚的关系（防「教到考题」）

P1–P12 全部直接对应发给两组的锚 A1–A8（两组拿到的验收标准一字相同）；
H1/H2/H3/E1/E2 锚里**没有**写——它们测的是手册②反例步（并发与重试 / 失败路径）
和 builder 卡硬约束是否真的起作用，这正是三路径实验里拉开差距的那类「没人问到的地方」。
