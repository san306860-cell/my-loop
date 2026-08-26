// 3 条硬探针 —— 2026-08-20 20:30 定稿（先于两组任何实现存在）。
// 用法：node hard.mjs adapters/path4.mjs
// 测「没人问到的地方」：并发丢失更新 / 重试安全 / CSS 陷阱。锚里没写，两组的手册②步都要求自己想到。
import { Jar, startServer, stopServer, uid, report } from "./lib.mjs";

const A = await import(new URL(process.argv[2], import.meta.url));
const R = [];
const t = (id, name, ok, why = "") => R.push({ id, name, ok: !!ok, why });

let srv = null;
try {
  srv = await startServer(A.dir, A.port);
  const base = srv.base;
  const u = { username: uid("hc_"), password: "Pw!" + uid("") };
  const jarA = new Jar(), jarB = new Jar();
  await A.register(jarA, base, u);
  if (await A.needsLoginAfterRegister?.() ?? true) await A.login(jarA, base, u);
  await A.login(jarB, base, u);

  // H1 并发丢失更新：两个「设备」从同一基线同时保存同一字段
  const p = await A.createProject(jarA, base, uid("并发-"));
  await A.saveContent(jarA, base, p.id, { open: "BASELINE" });
  const verA = await (A.readVersion?.(jarA, base, p.id) ?? null);
  const verB = await (A.readVersion?.(jarB, base, p.id) ?? null);
  const [w1, w2] = await Promise.all([
    A.saveContent(jarA, base, p.id, { open: "DEV-A-" + uid("") }, verA),
    A.saveContent(jarB, base, p.id, { open: "DEV-B-" + uid("") }, verB),
  ]);
  const fin = await A.readProject(jarA, base, p.id);
  const hasA = fin.text.includes("DEV-A-"), hasB = fin.text.includes("DEV-B-");
  const conflictSignal = [w1.status, w2.status].some(s => s >= 400 && s < 500);
  const silentLoss = w1.status < 300 && w2.status < 300 && (hasA !== hasB);
  t("H1", "并发写同一字段：不许静默丢失更新（要么冲突信号，要么合并）",
    conflictSignal || (hasA && hasB),
    `w1=${w1.status} w2=${w2.status} final(A=${hasA},B=${hasB}) silentLoss=${silentLoss}`);

  // H2 重试安全：响应丢了客户端重试
  const mark = uid("RETRY-");
  let worst = 0;
  for (let i = 0; i < 5; i++) {
    const r = await A.saveContent(jarA, base, p.id, { blind: mark });
    worst = Math.max(worst, r.status);
  }
  const after5 = await A.readProject(jarA, base, p.id);
  const d1 = await A.deleteProject(jarA, base, p.id);
  const d2 = await A.deleteProject(jarA, base, p.id);
  const l1 = await A.logout(jarA, base);
  const l2 = await A.logout(jarA, base);
  t("H2", "保存×5 / 删除×2 / 登出×2 重放，终态一致且无 5xx",
    worst < 500 && after5.text.includes(mark) &&
    d1.status < 500 && d2.status < 500 && l1.status < 500 && l2.status < 500,
    `save-worst=${worst} del=${d1.status},${d2.status} logout=${l1.status},${l2.status}`);

  // H3 CSS 陷阱：注释未正确闭合会吞掉后续整块（demo 样式必须完好迁移）
  const html = await fetch(base + "/").then(r => r.text());
  let css = [...html.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/gi)].map(m => m[1]).join("\n");
  for (const m of html.matchAll(/<link[^>]+href="([^"]+\.css[^"]*)"/gi)) {
    const url = m[1].startsWith("http") ? m[1] : base + (m[1].startsWith("/") ? "" : "/") + m[1];
    css += "\n" + (await fetch(url).then(r => r.ok ? r.text() : "").catch(() => ""));
  }
  const stripped = css.replace(/\/\*[\s\S]*?\*\//g, "");
  const danglingClose = stripped.includes("*/");
  const rootOk = /:root\s*\{[^}]*--/.test(stripped);
  const rules = (stripped.match(/\{/g) || []).length;
  t("H3", "CSS 注释全部正确闭合，:root 变量块存活，规则量级完整",
    !danglingClose && rootOk && rules > 80,
    `dangling=${danglingClose} root=${rootOk} rules=${rules} cssLen=${css.length}`);
} catch (e) {
  console.error("RUN-ABORT:", String(e).slice(0, 400));
} finally {
  await stopServer(srv);
}
while (R.length < 3) t(`H${R.length + 1}`, "（未执行 —— 前置失败）", false, "run aborted");
report(R);
