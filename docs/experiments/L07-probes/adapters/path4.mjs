// A 组适配层 —— 仅依据 qs-path4-v2/README.md「API 一览」编写（2026-08-20 21:10）。
// 备注（对两组同策略）：该实现的「生成 Prompt」是纯前端行为、搜索是客户端过滤（README 无对应端点），
// generate 返回项目原文（生成器消费的服务端数据面），真实点击另由浏览器验证记录在案；
// searchProjects 返回列表响应（客户端搜索的数据面）。无版本机制 → readVersion 返回 null。
import { req } from "../lib.mjs";

export const dir = "/Users/a1234/Desktop/qs-path4-v2";
export const port = 3104;
export const upstreamEnv = url => ({ AI_UPSTREAM_BASE_URL: url });
export const needsLoginAfterRegister = () => false; // README：注册即登录

export const register = (jar, base, cred) => req(jar, "POST", `${base}/api/auth/register`, cred);
export const login = (jar, base, cred) => req(jar, "POST", `${base}/api/auth/login`, cred);
export const logout = (jar, base) => req(jar, "POST", `${base}/api/auth/logout`);

export async function createProject(jar, base, name) {
  const r = await req(jar, "POST", `${base}/api/projects`, { name });
  let id = r.json?.id ?? r.json?.project?.id ?? r.json?.data?.id ?? null;
  if (!id) { // 兜底：从列表里按名字找最新
    const ls = await req(jar, "GET", `${base}/api/projects`);
    const arr = Array.isArray(ls.json) ? ls.json : ls.json?.projects ?? [];
    id = arr.find(p => p.name === name)?.id ?? null;
  }
  return { status: r.status, text: r.text, id };
}
export const listProjects = (jar, base) => req(jar, "GET", `${base}/api/projects`);
export const readProject = (jar, base, id) => req(jar, "GET", `${base}/api/projects/${id}`);

const BRIEF = ["goal", "deliverable", "audience", "criteria"];
const QUAD = ["hidden", "open", "unknown", "blind"];
export function saveContent(jar, base, id, fields, _version) {
  const body = {};
  for (const k of BRIEF) if (k in fields) (body.brief ??= {})[k] = fields[k];
  for (const k of QUAD) if (k in fields) (body.quadrants ??= {})[k] = fields[k];
  return req(jar, "PUT", `${base}/api/projects/${id}`, body);
}
export const readVersion = () => null; // README 已知限制：last-write-wins，无版本机制

export async function generate(jar, base, id) {
  return readProject(jar, base, id); // 见文件头备注；真实点击由浏览器检查记录
}
export const duplicateProject = (jar, base, id) => req(jar, "POST", `${base}/api/projects/${id}/duplicate`);
export const deleteProject = (jar, base, id) => req(jar, "DELETE", `${base}/api/projects/${id}`);
export const searchProjects = (jar, base, _q) => req(jar, "GET", `${base}/api/projects`); // 客户端过滤的数据面

// AI 调用前置条件（README：key/model 都在服务端拼装）→ 配 key 时一并配模型名；两组适配层同策略
export const setApiKey = (jar, base, key) =>
  req(jar, "PUT", `${base}/api/settings`, { apiKey: key, apiModel: "probe-model" });
export const readSettings = (jar, base) => req(jar, "GET", `${base}/api/settings`);
export const aiCall = (jar, base, _id, mode) => req(jar, "POST", `${base}/api/ai/chat`, {
  messages: [{ role: "system", content: `${mode} 模式` }, { role: "user", content: "请诊断这个项目" }],
});
export const rawBadJson = base =>
  req(null, "POST", `${base}/api/auth/register`, "{bad json", { "content-type": "application/json" });
