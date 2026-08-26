// L07 实验探针公共库 —— 2026-08-20 20:30 定稿（先于两组任何实现存在）
// Node 24，零依赖。探针断言不假设 API 形状，形状映射全部在 adapters/ 里。
import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";

export class Jar {
  constructor() { this.cookies = new Map(); }
  header() {
    return [...this.cookies.entries()].map(([k, v]) => `${k}=${v}`).join("; ");
  }
  store(res) {
    const sc = typeof res.headers.getSetCookie === "function"
      ? res.headers.getSetCookie() : [];
    for (const line of sc) {
      const [pair] = line.split(";");
      const i = pair.indexOf("=");
      if (i > 0) this.cookies.set(pair.slice(0, i).trim(), pair.slice(i + 1).trim());
    }
  }
}

export async function req(jar, method, url, body, headers = {}) {
  const h = { ...headers };
  if (jar && jar.cookies.size) h.cookie = jar.header();
  let payload;
  if (body !== undefined && typeof body !== "string") {
    h["content-type"] = h["content-type"] || "application/json";
    payload = JSON.stringify(body);
  } else payload = body;
  const res = await fetch(url, { method, headers: h, body: payload, redirect: "manual" });
  if (jar) jar.store(res);
  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch {}
  return { status: res.status, text, json, headers: res.headers };
}

// 起服务：默认「裸环境」—— 只带 PATH/HOME/PORT，逼出未文档化的必配变量
export async function startServer(dir, port, extraEnv = {}) {
  const env = {
    PATH: process.env.PATH, HOME: process.env.HOME,
    TMPDIR: process.env.TMPDIR || "/tmp",
    PORT: String(port), ...extraEnv,
  };
  const proc = spawn("npm", ["start"], { cwd: dir, env, stdio: ["ignore", "pipe", "pipe"] });
  let log = "";
  proc.stdout.on("data", d => { log += d; });
  proc.stderr.on("data", d => { log += d; });
  const base = `http://127.0.0.1:${port}`;
  for (let i = 0; i < 60; i++) {
    await sleep(500);
    try {
      const r = await fetch(base + "/", { redirect: "manual" });
      if (r.status < 600) return { proc, base, getLog: () => log };
    } catch {}
    if (proc.exitCode !== null) break;
  }
  throw new Error(`server in ${dir} did not come up on :${port}\n--- log ---\n${log.slice(-2000)}`);
}

export async function stopServer(srv) {
  if (!srv?.proc) return;
  srv.proc.kill("SIGTERM");
  for (let i = 0; i < 20; i++) {
    if (srv.proc.exitCode !== null) return;
    await sleep(200);
  }
  srv.proc.kill("SIGKILL");
  await sleep(300);
}

// 恶意上游：OpenAI 形状，把收到的 Authorization 回显进 content（测密钥是否透传到浏览器）
export function startEvilUpstream(port = 3199) {
  return import("node:http").then(({ createServer }) => new Promise(resolve => {
    const seen = [];
    const s = createServer((rq, rs) => {
      let b = "";
      rq.on("data", d => (b += d));
      rq.on("end", () => {
        seen.push({ url: rq.url, auth: rq.headers.authorization || "", body: b.slice(0, 500) });
        rs.setHeader("content-type", "application/json");
        rs.end(JSON.stringify({
          id: "evil-1", object: "chat.completion",
          choices: [{ index: 0, finish_reason: "stop",
            message: { role: "assistant",
              content: `EVIL-ECHO auth=[${rq.headers.authorization || "none"}] 你的请求我收到了` } }],
          usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 },
        }));
      });
    });
    s.listen(port, "127.0.0.1", () => resolve({ server: s, seen, url: `http://127.0.0.1:${port}/v1` }));
  }));
}

export function uid(p) { return `${p}${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`; }

export function report(results) {
  let pass = 0;
  for (const r of results) {
    console.log(`${r.ok ? "PASS" : "FAIL"}  ${r.id}  ${r.name}${r.ok ? "" : `\n      └ ${r.why}`}`);
    if (r.ok) pass++;
  }
  console.log(`\n== ${pass}/${results.length} ==`);
  return pass;
}
