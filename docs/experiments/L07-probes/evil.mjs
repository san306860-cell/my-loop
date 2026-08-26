// 恶意上游探针 —— 2026-08-20 20:30 定稿（先于两组任何实现存在）。
// 用法：node evil.mjs adapters/path4.mjs
// 场景：上游把收到的 Authorization 回显进消息正文。合格的代理必须
// (E1) 真的在服务端注入用户的 key 调上游（链路真实），且 (E2) 浏览器可见响应里不出现 key 明文。
import { Jar, startServer, stopServer, startEvilUpstream, uid, report } from "./lib.mjs";

const A = await import(new URL(process.argv[2], import.meta.url));
const R = [];
const t = (id, name, ok, why = "") => R.push({ id, name, ok: !!ok, why });
const SECRET = "sk-EVIL-PROBE-KEY-4d3c2b1a";

let srv = null, evil = null;
try {
  evil = await startEvilUpstream(3199);
  srv = await startServer(A.dir, A.port, A.upstreamEnv(evil.url));
  const base = srv.base;
  const jar = new Jar();
  const u = { username: uid("ev_"), password: "Pw!" + uid("") };
  await A.register(jar, base, u);
  if (await A.needsLoginAfterRegister?.() ?? true) await A.login(jar, base, u);
  const p = await A.createProject(jar, base, uid("evil-"));
  await A.saveContent(jar, base, p.id, { goal: "测试目标", hidden: "内部约束" });
  await A.setApiKey(jar, base, SECRET);

  const res = await A.aiCall(jar, base, p.id, "diagnose");
  const upstreamGotKey = evil.seen.some(s => (s.auth || "").includes(SECRET));
  t("E1", "服务端真的带用户 key 调了上游（代理链路真实）",
    evil.seen.length > 0 && upstreamGotKey,
    `upstream-hits=${evil.seen.length} auth-carried=${upstreamGotKey} aiStatus=${res.status}`);
  t("E2", "上游回显 key 后，浏览器可见响应不含 key 明文",
    evil.seen.length > 0 && !res.text.includes(SECRET),
    `aiStatus=${res.status} leaked=${res.text.includes(SECRET)} body≈${res.text.slice(0, 160)}`);
} catch (e) {
  console.error("RUN-ABORT:", String(e).slice(0, 400));
} finally {
  await stopServer(srv);
  evil?.server?.close();
}
while (R.length < 2) t(`E${R.length + 1}`, "（未执行 —— 前置失败）", false, "run aborted");
report(R);
