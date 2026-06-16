"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  AccountState,
  CatalogItem,
  JobDetail,
  JobEvent,
  artifactUrl,
  createJob,
  getAccount,
  getJob,
  getPersonas,
  getThemes,
  startDistribute,
  streamJob,
} from "@/lib/api";
import PublishPanel from "@/components/PublishPanel";
import PlatformVersions from "@/components/PlatformVersions";

type LogLine = { kind: string; text: string };

const COMPLETION_TEXT: Record<string, string> = {
  DONE: "✅ 全流程完成",
  DONE_WITH_CONCERNS: "⚠️ 完成（部分步骤降级）",
  BLOCKED: "⛔ 受阻：关键步骤无法继续",
  NEEDS_CONTEXT: "❓ 需要补充信息",
};

export default function HomePage() {
  const [personas, setPersonas] = useState<CatalogItem[]>([]);
  const [themes, setThemes] = useState<CatalogItem[]>([]);
  const [account, setAccount] = useState<AccountState | null>(null);

  const [prompt, setPrompt] = useState("写一篇关于 AI Agent 的公众号文章");
  const [persona, setPersona] = useState("");
  const [theme, setTheme] = useState("");
  const [interactive, setInteractive] = useState(false);
  const [publishDraft, setPublishDraft] = useState(false);

  const [running, setRunning] = useState(false);
  const [lines, setLines] = useState<LogLine[]>([]);
  const [result, setResult] = useState<JobDetail | null>(null);
  const [tab, setTab] = useState<"preview" | "markdown">("preview");
  const logRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef<(() => void) | null>(null);

  // 带稿来 / 多平台分发
  const [srcText, setSrcText] = useState("");
  const [distributing, setDistributing] = useState(false);
  const [distLines, setDistLines] = useState<LogLine[]>([]);
  const [distResult, setDistResult] = useState<JobDetail | null>(null);
  const distLogRef = useRef<HTMLDivElement>(null);
  const distCancelRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    getPersonas().then(setPersonas).catch(() => {});
    getThemes().then(setThemes).catch(() => {});
    getAccount().then(setAccount).catch(() => {});
    return () => {
      cancelRef.current?.();
      distCancelRef.current?.();
    };
  }, []);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [lines]);

  useEffect(() => {
    if (distLogRef.current) distLogRef.current.scrollTop = distLogRef.current.scrollHeight;
  }, [distLines]);

  function push(kind: string, text: string) {
    setLines((prev) => [...prev, { kind, text }]);
  }

  function renderEvent(e: JobEvent) {
    switch (e.type) {
      case "status":
        push("step", `状态：${e.status}${e.error ? " — " + e.error : ""}`);
        break;
      case "log":
        push("log", String(e.text ?? ""));
        break;
      case "notice":
        push("notice", `提示：${e.text}`);
        break;
      case "assistant_text": {
        const t = String(e.text ?? "");
        push(/\[\d\/8\]/.test(t) ? "step" : "log", t);
        break;
      }
      case "tool_use":
        push("tool", `🔧 ${e.name}${e.detail ? "  " + e.detail : ""}`);
        break;
      case "tool_result":
        if (e.is_error) push("err", "工具返回错误");
        break;
      case "result_meta":
        push(
          "log",
          `本轮结束 · turns=${e.num_turns ?? "?"} · cost=$${
            e.total_cost_usd != null ? Number(e.total_cost_usd).toFixed(4) : "?"
          }`
        );
        break;
    }
  }

  function pushDist(kind: string, text: string) {
    setDistLines((prev) => [...prev, { kind, text }]);
  }

  function renderDistEvent(e: JobEvent) {
    switch (e.type) {
      case "status":
        pushDist("step", `状态：${e.status}${e.error ? " — " + e.error : ""}`);
        break;
      case "log":
        pushDist("log", String(e.text ?? ""));
        break;
      case "notice":
        pushDist("notice", `提示：${e.text}`);
        break;
      case "assistant_text":
        pushDist("log", String(e.text ?? ""));
        break;
      case "tool_use":
        pushDist("tool", `🔧 ${e.name}${e.detail ? "  " + e.detail : ""}`);
        break;
      case "tool_result":
        if (e.is_error) pushDist("err", "工具返回错误");
        break;
    }
  }

  async function trackDistributeJob(jobId: string) {
    setDistLines([]);
    setDistResult(null);
    setDistributing(true);
    pushDist("step", `分发任务已创建：${jobId}`);
    distCancelRef.current = streamJob(
      jobId,
      renderDistEvent,
      async () => {
        try {
          const detail = await getJob(jobId);
          setDistResult(detail);
          if (detail.completion)
            pushDist("step", COMPLETION_TEXT[detail.completion] ?? detail.completion);
        } catch (err) {
          pushDist("err", String(err));
        }
        setDistributing(false);
      }
    );
  }

  async function onDistributeFromResult() {
    if (!result?.id) return;
    try {
      const job = await startDistribute({
        source_job_id: result.id,
        platforms: ["xiaohongshu", "douyin"],
      });
      await trackDistributeJob(job.id);
    } catch (err) {
      pushDist("err", String(err));
      setDistributing(false);
    }
  }

  async function onDistributeFromText() {
    if (!srcText.trim()) return;
    try {
      const job = await startDistribute({
        source_text: srcText,
        platforms: ["xiaohongshu", "douyin"],
      });
      await trackDistributeJob(job.id);
    } catch (err) {
      pushDist("err", String(err));
      setDistributing(false);
    }
  }

  async function onSubmit() {
    setLines([]);
    setResult(null);
    setRunning(true);
    try {
      const job = await createJob({
        prompt,
        interactive,
        theme: theme || null,
        persona: persona || null,
        publish_draft: publishDraft,
      });
      push("step", `任务已创建：${job.id}`);
      cancelRef.current = streamJob(
        job.id,
        renderEvent,
        async () => {
          try {
            const detail = await getJob(job.id);
            setResult(detail);
            if (detail.completion)
              push("step", COMPLETION_TEXT[detail.completion] ?? detail.completion);
          } catch (err) {
            push("err", String(err));
          }
          setRunning(false);
        }
      );
    } catch (err) {
      push("err", String(err));
      setRunning(false);
    }
  }

  const canPublish = account?.wechat_bound ?? false;

  return (
    <>
      <h1>一句话，生成一篇公众号文章</h1>
      <p className="sub">
        热点抓取 → 选题 → 框架 → 写作 → SEO → 配图 → 微信排版 → 推送草稿箱。云端全自动，零部署。
      </p>

      <div className="panel">
        <h2>写什么</h2>
        <label>需求（一句话）</label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="例如：写一篇关于 AI Agent 的公众号文章"
        />
        <div className="row">
          <div>
            <label>写作人格</label>
            <select value={persona} onChange={(e) => setPersona(e.target.value)}>
              <option value="">沿用我的默认（{account?.writing_persona ?? "…"}）</option>
              {personas.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label} — {p.description}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label>排版主题</label>
            <select value={theme} onChange={(e) => setTheme(e.target.value)}>
              <option value="">沿用我的默认（{account?.theme ?? "…"}）</option>
              {themes.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.id}
                  {t.description ? `（${t.description}）` : ""}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="checkbox">
          <input
            id="interactive"
            type="checkbox"
            checked={interactive}
            onChange={(e) => setInteractive(e.target.checked)}
          />
          <label htmlFor="interactive" style={{ margin: 0 }}>
            交互模式（在选题/框架/配图处暂停确认）
          </label>
        </div>

        <div className="checkbox">
          <input
            id="publish"
            type="checkbox"
            checked={publishDraft && canPublish}
            disabled={!canPublish}
            onChange={(e) => setPublishDraft(e.target.checked)}
          />
          <label htmlFor="publish" style={{ margin: 0 }}>
            完成后推送到我的公众号草稿箱
          </label>
        </div>
        {!canPublish && (
          <p className="hint">
            尚未绑定公众号。前往 <Link href="/settings">设置</Link> 绑定 appid/secret
            后即可一键推送草稿箱（其余环节无需任何配置）。
          </p>
        )}

        <div style={{ marginTop: 18 }}>
          <button className="btn" onClick={onSubmit} disabled={running || !prompt.trim()}>
            {running ? "生成中…" : "开始生成"}
          </button>
        </div>
      </div>

      {(lines.length > 0 || running) && (
        <div className="panel">
          <h2>
            实时进度{" "}
            {running && <span className="badge running">running</span>}
          </h2>
          <div className="log" ref={logRef}>
            {lines.map((l, i) => (
              <div key={i} className={`line ${l.kind}`}>
                {l.text}
              </div>
            ))}
          </div>
        </div>
      )}

      {result && (
        <div className="panel">
          <h2>
            成稿{" "}
            <span className={`badge ${result.status}`}>{result.status}</span>{" "}
            {result.title && <span style={{ color: "var(--muted)" }}>· {result.title}</span>}
          </h2>
          {result.error && <p className="log err">{result.error}</p>}
          {result.images && result.images.length > 0 && (
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 14 }}>
              {result.images.map((src, i) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  key={i}
                  src={artifactUrl(src)}
                  alt={`配图 ${i + 1}`}
                  style={{
                    width: 120,
                    height: 120,
                    objectFit: "cover",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                  }}
                />
              ))}
            </div>
          )}
          {result.article_markdown ? (
            <>
              <div className="tabs">
                <button
                  className={tab === "preview" ? "active" : ""}
                  onClick={() => setTab("preview")}
                >
                  微信预览
                </button>
                <button
                  className={tab === "markdown" ? "active" : ""}
                  onClick={() => setTab("markdown")}
                >
                  Markdown
                </button>
                <button
                  className="secondary"
                  style={{ marginLeft: "auto" }}
                  onClick={() =>
                    navigator.clipboard.writeText(result.article_markdown ?? "")
                  }
                >
                  复制 Markdown
                </button>
              </div>
              {tab === "preview" ? (
                result.preview_html ? (
                  <iframe
                    className="preview-frame"
                    srcDoc={result.preview_html}
                    title="preview"
                  />
                ) : (
                  <p className="hint">未生成预览 HTML（可切到 Markdown 查看正文）。</p>
                )
              ) : (
                <pre className="md">{result.article_markdown}</pre>
              )}
            </>
          ) : (
            <p className="hint">未找到成稿文件。请查看上方进度日志排查。</p>
          )}

          {result.article_markdown && <PublishPanel jobId={result.id} />}

          {result.article_markdown && (
            <div style={{ marginTop: 16 }}>
              <button
                className="btn secondary"
                onClick={onDistributeFromResult}
                disabled={distributing}
              >
                {distributing ? "分发中…" : "分发到多平台（小红书 + 抖音）"}
              </button>
            </div>
          )}

          {result.platform_versions && result.platform_versions.length > 0 && (
            <PlatformVersions versions={result.platform_versions} />
          )}
        </div>
      )}

      {/* 分发任务进度 */}
      {(distLines.length > 0 || distributing) && (
        <div className="panel">
          <h2>
            分发进度{" "}
            {distributing && <span className="badge running">running</span>}
          </h2>
          <div className="log" ref={distLogRef}>
            {distLines.map((l, i) => (
              <div key={i} className={`line ${l.kind}`}>
                {l.text}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 分发结果（多平台版本） */}
      {distResult && distResult.platform_versions && distResult.platform_versions.length > 0 && (
        <div className="panel">
          <h2>
            多平台版本{" "}
            <span className={`badge ${distResult.status}`}>{distResult.status}</span>
          </h2>
          {distResult.error && <p className="log err">{distResult.error}</p>}
          <PlatformVersions versions={distResult.platform_versions} />
        </div>
      )}

      {/* 带稿来：直接粘贴正文进行多平台分发 */}
      <div className="panel">
        <h2>带稿来 · 直接分发已有文章</h2>
        <p className="hint">粘贴任意文章正文，自动改写为小红书和抖音风格版本。</p>
        <label>文章正文（Markdown 或纯文本）</label>
        <textarea
          value={srcText}
          onChange={(e) => setSrcText(e.target.value)}
          placeholder="在此粘贴文章内容…"
          style={{ minHeight: 140 }}
        />
        <div style={{ marginTop: 12 }}>
          <button
            className="btn"
            onClick={onDistributeFromText}
            disabled={distributing || !srcText.trim()}
          >
            {distributing ? "分发中…" : "开始分发"}
          </button>
        </div>
      </div>
    </>
  );
}
