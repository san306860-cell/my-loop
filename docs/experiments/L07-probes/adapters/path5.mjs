// B 组适配层 —— 仅依据 qs-path5-gated/README.md「API 一览」编写（2026-08-20 21:15）。
// 映射说明：该实现注册/登录用 {email,password} → 适配层把探针的 username 映射为 <username>@probe.test；
// 生成是真端点 POST /api/projects/:id/generate；搜索无服务端端点（与 A 组同策略：返回列表数据面）。
// 无版本机制（README 已知限制 last-write-wins）→ readVersion 返回 null。
import { req } from "../lib.mjs";

export const dir = "/Users/a1234/Desktop/qs-path5-gated";
export const port = 3105;
export const upstreamEnv = url => ({ UPSTREAM_BASE_URL: url });
export const needsLoginAfterRegister = () => false; // README：成功即建会话

const asEmail = u => (u.includes("@") ? u : `${u}@probe.test`);
const cred = c => ({ email: c.username ? asEmail(c.username) : c.email, password: c.password });

export const register = (jar, base, c) => req(jar, "POST", `${base}/api/auth/register`, cred(c));
export const login = (jar, base, c) => req(jar, "POST", `${base}/api/auth/login`, cred(c));
export const logout = (jar, base) => req(jar, "POST", `${base}/api/auth/logout`);

export async function createProject(jar, base, name) {
  const r = await req(jar, "POST", `${base}/api/projects`, { name });
  let id = r.json?.id ?? r.json?.project?.id ?? null;
  if (!id) {
    const ls = await req(jar, "GET", `${base}/api/projects`);
    const arr = Array.isArray(ls.json) ? ls.json : ls.json?.projects ?? [];
    id = arr.find(p => p.name === name)?.id ?? null;
  }
  return { status: r.status, text: r.text, id };
}
export const listProjects = (jar, base) => req(jar, "GET", `${base}/api/projects`);
// README 无 GET /api/projects/:id —— 列表即全量项目对象（形状与 demo 一致），读单个 = 从列表取。
// 找不到（含他人项目）→ 404，text 给整份列表原文以便探针做泄露扫描。
export async function readProject(jar, base, id) {
  const ls = await req(jar, "GET", `${base}/api/projects`);
  if (ls.status !== 200) return { status: ls.status, text: ls.text };
  const arr = Array.isArray(ls.json) ? ls.json : ls.json?.projects ?? [];
  const p = arr.find(x => x?.id === id);
  return { status: p ? 200 : 404, text: p ? JSON.stringify(p) : ls.text };
}

const BRIEF = ["goal", "deliverable", "audience", "criteria"];
const QUAD = ["hidden", "open", "unknown", "blind"];
export function saveContent(jar, base, id, fields, _version) {
  const body = {};
  for (const k of BRIEF) if (k in fields) (body.brief ??= {})[k] = fields[k];
  for (const k of QUAD) if (k in fields) (body.quadrants ??= {})[k] = fields[k];
  return req(jar, "PUT", `${base}/api/projects/${id}`, body);
}
export const readVersion = () => null;

export const generate = (jar, base, id) => req(jar, "POST", `${base}/api/projects/${id}/generate`);
export const duplicateProject = (jar, base, id) => req(jar, "POST", `${base}/api/projects/${id}/duplicate`);
export const deleteProject = (jar, base, id) => req(jar, "DELETE", `${base}/api/projects/${id}`);
export const searchProjects = (jar, base, _q) => req(jar, "GET", `${base}/api/projects`); // 客户端过滤的数据面

// 与 path4 同策略：配 key 时一并配模型名（README 的 PUT /api/settings 接受 apiModel）
export const setApiKey = (jar, base, key) =>
  req(jar, "PUT", `${base}/api/settings`, { apiKey: key, apiModel: "probe-model" });
export const readSettings = (jar, base) => req(jar, "GET", `${base}/api/settings`);
export const aiCall = (jar, base, id, mode) => req(jar, "POST", `${base}/api/ai/${mode}`, { projectId: id });
export const rawBadJson = base =>
  req(null, "POST", `${base}/api/auth/register`, "{bad json", { "content-type": "application/json" });
