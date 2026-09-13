"use client";
import { useEffect, useState } from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
const BACKEND_DEFAULT = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
const LANGGRAPH_URL = process.env.NEXT_PUBLIC_LANGGRAPH_URL || "http://localhost:2024";
const ASSISTANT_ID = process.env.NEXT_PUBLIC_ASSISTANT_ID || "agent";
function baseOf(v: string) {
  return v.trim().replace(/\/+$/, "");
}
function textOf(m: any): string {
  const c = m ? m.content : "";
  if (typeof c === "string") return c;
  if (Array.isArray(c)) {
    return c
      .map((b: any) => {
        if (typeof b === "string") return b;
        if (b && typeof b === "object") return b.text ?? b.content ?? JSON.stringify(b);
        return String(b ?? "");
      })
      .join("");
  }
  if (c == null) return "";
  return typeof c === "object" ? JSON.stringify(c) : String(c);
}
function interruptsOf(raw: any): any[] {
  if (!raw) return [];
  return Array.isArray(raw) ? raw : [raw];
}
function allowedOf(value: any): string[] {
  if (value && typeof value === "object") {
    const a = value.allowed_decisions;
    if (Array.isArray(a)) return a.map(String);
    const r = value.review_configs;
    if (Array.isArray(r) && r[0] && Array.isArray(r[0].allowed_decisions)) {
      return r[0].allowed_decisions.map(String);
    }
  }
  return ["approve", "edit", "reject"];
}
function actionOf(value: any): any {
  if (value && typeof value === "object") {
    const ar = value.action_requests;
    if (Array.isArray(ar) && ar[0]) return ar[0];
    if (value.action) return value.action;
    if (value.name) return { name: value.name, args: value.args ?? {} };
  }
  return null;
}
function versionOf(item: any): string {
  if (typeof item === "string") return item;
  if (item && typeof item === "object") {
    const v = item.version ?? item.id ?? item.name;
    if (typeof v === "string" && v) return v;
  }
  return "";
}
export default function Page() {
  const [backendUrl, setBackendUrl] = useState(BACKEND_DEFAULT);
  const [userId, setUserId] = useState("");
  const [token, setToken] = useState("");
  const [threadId, setThreadId] = useState("");
  const [input, setInput] = useState("");
  const [editText, setEditText] = useState("");
  const [versions, setVersions] = useState<string[]>([]);
  const [selectedVersion, setSelectedVersion] = useState("");
  const [notice, setNotice] = useState("");
  const stream = useStream({
    apiUrl: LANGGRAPH_URL,
    assistantId: ASSISTANT_ID,
    threadId: threadId || null,
    streamMode: ["values"],
    fetchStateHistory: true,
    onError: (e: any) => setNotice("运行失败：" + (e?.message || "未知错误")),
    ...(token ? { defaultHeaders: { Authorization: "Bearer " + token } } : {}),
  } as any);
  const messages: any[] = (stream as any).messages ?? (stream as any).values?.messages ?? [];
  const rawInterrupt = (stream as any).interrupt;
  const interrupts = interruptsOf(rawInterrupt);
  const busy = !!(stream as any).isLoading;
  useEffect(() => {
    const first = interruptsOf(rawInterrupt)[0];
    const action = first ? actionOf(first.value ?? first) : null;
    setEditText(action ? JSON.stringify(action.args ?? {}, null, 2) : "");
  }, [rawInterrupt]);
  async function login() {
    setNotice("");
    const name = userId.trim();
    if (!name) {
      setNotice("请先输入用户");
      return;
    }
    try {
      const res = await fetch(baseOf(backendUrl) + "/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: name }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setNotice("登录失败：" + (data.detail || res.status));
        return;
      }
      if (!data.token) {
        setNotice("登录失败：未返回令牌");
        return;
      }
      setToken(data.token);
      setNotice("登录成功");
    } catch (e: any) {
      setNotice("登录失败：" + (e?.message || "网络错误"));
    }
  }
  async function newSession() {
    setNotice("");
    if (!token) {
      setNotice("请先登录");
      return;
    }
    const id = crypto.randomUUID();
    try {
      const res = await fetch(baseOf(backendUrl) + "/v1/sessions/ensure", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
        body: JSON.stringify({ thread_id: id }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setNotice("创建会话失败：" + (data.detail || res.status));
        return;
      }
      setThreadId(data.thread_id || id);
      const agentRes = await fetch(baseOf(LANGGRAPH_URL) + "/threads", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
        body: JSON.stringify({ thread_id: data.thread_id || id }),
      });
      if (!agentRes.ok) {
        setNotice("创建会话失败：智能体线程未建成（" + agentRes.status + "）");
        return;
      }
      setVersions([]);
      setSelectedVersion("");
      setNotice("会话已创建");
    } catch (e: any) {
      setNotice("创建会话失败：" + (e?.message || "网络错误"));
    }
  }
  async function refreshVersions(silent?: boolean) {
    if (!threadId || !token) return;
    try {
      const res = await fetch(baseOf(backendUrl) + "/v1/sessions/" + threadId + "/versions", {
        headers: { Authorization: "Bearer " + token },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (!silent) setNotice("获取版本失败：" + (data.detail || res.status));
        return;
      }
      const list = Array.isArray(data.versions)
        ? data.versions.map(versionOf).filter(Boolean)
        : [];
      setVersions(list);
      if (list.length > 0 && !list.includes(selectedVersion)) {
        setSelectedVersion(list[list.length - 1]);
      }
      if (!silent) setNotice("版本已刷新");
    } catch (e: any) {
      if (!silent) setNotice("获取版本失败：" + (e?.message || "网络错误"));
    }
  }
  async function publish() {
    setNotice("");
    if (!threadId || !token) {
      setNotice("请先登录并创建会话");
      return;
    }
    try {
      const res = await fetch(baseOf(backendUrl) + "/v1/sessions/" + threadId + "/publish", {
        method: "POST",
        headers: { Authorization: "Bearer " + token },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setNotice("发布失败：" + (data.detail || res.status));
        return;
      }
      setNotice("发布成功");
      await refreshVersions(true);
      if (data.version) setSelectedVersion(data.version);
    } catch (e: any) {
      setNotice("发布失败：" + (e?.message || "网络错误"));
    }
  }
  function send() {
    setNotice("");
    const text = input.trim();
    if (!text) return;
    if (!token) {
      setNotice("请先登录");
      return;
    }
    if (!threadId) {
      setNotice("请先创建会话");
      return;
    }
    (stream as any).submit(
      { messages: [{ id: crypto.randomUUID(), type: "human", content: text }] },
      { streamMode: ["values"] }
    );
    setInput("");
  }
  function decide(decision: any) {
    setNotice("");
    if (busy) {
      setNotice("运行尚未结束，请稍候再点");
      return;
    }
    Promise.resolve(
      (stream as any).submit({}, { command: { resume: { decisions: [decision] } }, streamMode: ["values"] })
    ).catch((e: any) => setNotice("提交失败：" + (e?.message || "网络错误")));
  }
  function submitEdit(action: any) {
    try {
      const args = JSON.parse(editText || "{}");
      decide({ type: "edit", edited_action: { name: action?.name || "", args } });
    } catch {
      setNotice("修改内容不是合法 JSON");
    }
  }
  const canChat = !!(token && threadId);
  const playSrc =
    threadId && selectedVersion && token
      ? baseOf(backendUrl) +
        "/v1/games/" +
        threadId +
        "/" +
        selectedVersion +
        "/index.html?token=" +
        encodeURIComponent(token)
      : "";
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", fontSize: 14 }}>
      <div style={{ display: "flex", gap: 8, alignItems: "center", padding: 8, borderBottom: "1px solid #ddd", flexWrap: "wrap" }}>
        <label>后端地址</label>
        <input value={backendUrl} onChange={(e) => setBackendUrl(e.target.value)} style={{ width: 220 }} />
        <label>用户</label>
        <input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="请输入用户" style={{ width: 140 }} />
        <button onClick={login}>登录</button>
        <button onClick={newSession}>新会话</button>
        <span>会话：{threadId || "未创建"}</span>
      </div>
      {notice ? <div style={{ padding: "4px 8px", background: "#f6f6f6" }}>{notice}</div> : null}
      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", borderRight: "1px solid #ddd", minWidth: 0 }}>
          <div style={{ padding: 8, fontWeight: "bold" }}>对话区</div>
          <div style={{ flex: 1, overflowY: "auto", padding: 8 }}>
            {!canChat ? <div>请先登录并创建会话后再对话</div> : null}
            {messages.map((m: any, i: number) => (
              <div key={m?.id || i} style={{ marginBottom: 8 }}>
                <div style={{ fontWeight: "bold" }}>{m?.type === "human" ? "我" : "智能体"}</div>
                <div style={{ whiteSpace: "pre-wrap" }}>{textOf(m)}</div>
              </div>
            ))}
            {interrupts.map((it: any, i: number) => {
              const value = it?.value ?? it;
              const allowed = allowedOf(value);
              const action = actionOf(value);
              return (
                <div key={i} style={{ border: "1px solid #e00", padding: 8, marginBottom: 8 }}>
                  <div style={{ fontWeight: "bold" }}>待审批</div>
                  <div style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(value, null, 2)}</div>
                  {allowed.includes("edit") ? (
                    <textarea value={editText} onChange={(e) => setEditText(e.target.value)} rows={6} style={{ width: "100%", marginTop: 8 }} />
                  ) : null}
                  <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                    {allowed.includes("approve") ? <button onClick={() => decide({ type: "approve" })} disabled={busy}>批准</button> : null}
                    {allowed.includes("edit") ? <button onClick={() => submitEdit(action)} disabled={busy}>提交修改</button> : null}
                    {allowed.includes("reject") ? <button onClick={() => decide({ type: "reject" })} disabled={busy}>拒绝</button> : null}
                  </div>
                </div>
              );
            })}
          </div>
          <div style={{ display: "flex", gap: 8, padding: 8, borderTop: "1px solid #ddd" }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") send();
              }}
              placeholder="请输入对话内容"
              disabled={!canChat || busy}
              style={{ flex: 1 }}
            />
            <button onClick={send} disabled={!canChat || busy}>发送</button>
          </div>
        </div>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center", padding: 8, borderBottom: "1px solid #ddd", flexWrap: "wrap" }}>
            <span style={{ fontWeight: "bold" }}>试玩区</span>
            <button onClick={publish} disabled={!canChat}>发布</button>
            <label>版本</label>
            <select value={selectedVersion} onChange={(e) => setSelectedVersion(e.target.value)} disabled={!canChat}>
              <option value="">请选择版本</option>
              {versions.map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
            <button onClick={() => refreshVersions()} disabled={!canChat}>刷新版本</button>
          </div>
          <div style={{ flex: 1 }}>
            {playSrc ? (
              <iframe title="试玩" src={playSrc} sandbox="allow-scripts" allowFullScreen style={{ width: "100%", height: "100%", border: 0 }} />
            ) : (
              <div style={{ padding: 8 }}>发布并选择版本后试玩</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
