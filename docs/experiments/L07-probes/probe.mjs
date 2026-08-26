// 12 条统一探针 —— 2026-08-20 20:30 定稿（先于两组任何实现存在）。
// 用法：node probe.mjs adapters/path4.mjs
// 断言只依赖 adapter 接口与响应原文子串，不假设 API 形状。
import { Jar, startServer, stopServer, uid, report } from "./lib.mjs";

const A = await import(new URL(process.argv[2], import.meta.url));
const R = [];
const t = (id, name, ok, why = "") => R.push({ id, name, ok: !!ok, why });

const F = {
  goal: uid("PROBE-GOAL-"), deliverable: uid("PROBE-DELIV-"),
  audience: uid("PROBE-AUD-"), criteria: uid("PROBE-CRIT-"),
  hidden: uid("PROBE-HID-"), open: uid("PROBE-OPEN-"),
  unknown: uid("PROBE-UNK-"), blind: uid("PROBE-BLIND-"),
};
const SECRET = "sk-PROBE-SECRET-9z8y7x6w5v";
const u1 = { username: uid("u1_"), password: "Pw!" + uid("") };
const u2 = { username: uid("u2_"), password: "Pw!" + uid("") };

let srv = null;
try {
  // P1 裸跑（只有 PATH/HOME/PORT）
  let bootErr = "";
  try { srv = await startServer(A.dir, A.port); } catch (e) { bootErr = String(e).slice(0, 300); }
  const home = srv ? await fetch(srv.base + "/").then(r => r.text()).catch(() => "") : "";
  t("P1", "npm start 裸跑可起，首页是真页面", srv && home.length > 1000, bootErr || `homepage len=${home.length}`);
  if (!srv) throw new Error("server never started — 后续探针全部记 FAIL");
  const base = srv.base;

  // P2 注册 + 登录
  const jar1 = new Jar();
  const reg = await A.register(jar1, base, u1);
  if (await A.needsLoginAfterRegister?.() ?? true) await A.login(jar1, base, u1);
  const lp0 = await A.listProjects(jar1, base);
  t("P2", "注册/登录后能访问受保护资源", reg.status < 400 && lp0.status === 200,
    `register=${reg.status} list=${lp0.status}`);

  // P3 简报 + 四象限保存回读（8 特征串）
  const proj = await A.createProject(jar1, base, uid("项目-"));
  await A.saveContent(jar1, base, proj.id, F);
  const rd = await A.readProject(jar1, base, proj.id);
  const missing = Object.values(F).filter(v => !rd.text.includes(v));
  t("P3", "8 个字段保存后原样读回", proj.id && rd.status === 200 && missing.length === 0,
    `missing=${missing.join(",").slice(0, 120)}`);

  // P4 生成 Prompt 含填写内容
  const gen = await A.generate(jar1, base, proj.id, F);
  const hit = Object.values(F).filter(v => gen.text.includes(v)).length;
  t("P4", "生成的 Prompt 包含 ≥6/8 个填写值", gen.status < 400 && hit >= 6, `hit=${hit}/8 status=${gen.status}`);

  // P5 登出后旧会话失效
  await A.logout(jar1, base);
  const afterLogout = await A.listProjects(jar1, base);
  t("P5", "登出后旧 cookie 访问受保护资源 → 401", afterLogout.status === 401, `got ${afterLogout.status}`);

  // P6 换「浏览器」重登，数据一字不丢
  const jar2 = new Jar();
  await A.login(jar2, base, u1);
  const rd2 = await A.readProject(jar2, base, proj.id);
  const miss2 = Object.values(F).filter(v => !rd2.text.includes(v));
  t("P6", "新 cookie jar 重登后 8 字段仍在", rd2.status === 200 && miss2.length === 0, `missing=${miss2.length}`);

  // P7 服务重启后数据仍在（防内存存储）
  await stopServer(srv);
  srv = await startServer(A.dir, A.port);
  const jar3 = new Jar();
  await A.login(jar3, base, u1);
  const rd3 = await A.readProject(jar3, base, proj.id);
  const miss3 = Object.values(F).filter(v => !rd3.text.includes(v));
  t("P7", "服务重启后数据仍在", rd3.status === 200 && miss3.length === 0, `missing=${miss3.length}`);

  // P8 项目 CRUD：建 / 复制 / 搜索 / 删除
  const name8 = uid("CRUD-独特名-");
  const p8 = await A.createProject(jar3, base, name8);
  const dup = await A.duplicateProject(jar3, base, p8.id);
  const found = await A.searchProjects(jar3, base, name8);
  const del = await A.deleteProject(jar3, base, p8.id);
  const lsAfter = await A.listProjects(jar3, base);
  t("P8", "建/复制/搜索/删除全部可用", p8.id && dup.status < 400 && found.status === 200 &&
    found.text.includes(name8) && del.status < 400 && !JSON.stringify(lsAfter.text).includes(`"${p8.id}"`),
    `dup=${dup.status} search=${found.status} del=${del.status}`);

  // P9 越权：u2 读 u1 的项目
  const jar4 = new Jar();
  await A.register(jar4, base, u2);
  if (await A.needsLoginAfterRegister?.() ?? true) await A.login(jar4, base, u2);
  const steal = await A.readProject(jar4, base, proj.id);
  const leaked = Object.values(F).some(v => steal.text.includes(v));
  t("P9", "越权读别人项目 → 403/404 且无数据泄露", [403, 404].includes(steal.status) && !leaked,
    `status=${steal.status} leaked=${leaked}`);

  // P10 未登录 → 401
  const jar5 = new Jar();
  const unauth = [];
  for (const fn of [() => A.listProjects(jar5, base), () => A.readProject(jar5, base, proj.id),
                    () => A.readSettings(jar5, base)]) {
    unauth.push((await fn()).status);
  }
  t("P10", "未登录访问受保护接口一律 401", unauth.every(s => s === 401), `got ${unauth.join(",")}`);

  // P11 畸形输入不许 5xx
  const bads = [];
  bads.push((await A.rawBadJson(base)).status);                                  // 坏 JSON
  bads.push((await A.register(new Jar(), base, { username: "x".repeat(200000), password: "p" })).status); // 超长
  bads.push((await A.register(new Jar(), base, {})).status);                     // 空必填
  bads.push((await A.saveContent(jar3, base, proj.id, { goal: 12345, hidden: { a: 1 } })).status); // 错类型
  t("P11", "4 组畸形输入无一 5xx", bads.every(s => s < 500), `got ${bads.join(",")}`);

  // P12 API Key 永不回显
  await A.setApiKey(jar3, base, SECRET);
  const views = [await A.readSettings(jar3, base), await A.readProject(jar3, base, proj.id),
                 await A.listProjects(jar3, base)];
  const echo = views.some(v => v.text.includes(SECRET));
  t("P12", "设置 API Key 后任何读接口不含明文", views[0].status === 200 && !echo, `echo=${echo}`);
} catch (e) {
  console.error("RUN-ABORT:", String(e).slice(0, 400));
} finally {
  await stopServer(srv);
}
while (R.length < 12) t(`P${R.length + 1}`, "（未执行 —— 前置失败）", false, "run aborted");
report(R);
