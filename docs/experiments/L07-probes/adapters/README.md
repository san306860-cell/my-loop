# Adapter 契约（2026-08-20 20:30 与探针同时定稿）

探针断言固定，API 形状映射全放这里。**每个 adapter 只准依据该路径 README 的「API 一览」编写，
不许读它的 src/**——README 写不清导致 adapter 写不出来的功能，按探针 FAIL 计（README 是交付物的一部分）。
两个 adapter 必须由同一人一次写完，改任何一个的判定逻辑都算改探针，需在实验报告中声明。

必须导出：

```
dir            绝对路径
port           3104 / 3105
upstreamEnv(url) -> {ENV_NAME: url}   // README 里写明的上游 base URL 环境变量
needsLoginAfterRegister() -> bool     // 注册是否自动登录
register(jar, base, {username,password}) -> {status,text}
login / logout(jar, base, ...)        -> {status,text}
createProject(jar, base, name)        -> {status, id}
listProjects / searchProjects(jar, base, q?) -> {status,text}
readProject(jar, base, id)            -> {status,text}   // 原文，探针只做子串断言
saveContent(jar, base, id, fields, version?) -> {status,text}
                                      // fields ⊆ {goal,deliverable,audience,criteria,hidden,open,unknown,blind}
readVersion(jar, base, id) -> token|null   // 无版本机制就返回 null
generate(jar, base, id, fields)       -> {status,text}   // 浏览器拿到的生成结果
duplicateProject / deleteProject(jar, base, id) -> {status,text}
setApiKey(jar, base, key) / readSettings(jar, base) -> {status,text}
aiCall(jar, base, id, mode)           -> {status,text}
rawBadJson(base) -> {status}          // 向注册端点 POST 字面量 '{bad json'，content-type: application/json
```
