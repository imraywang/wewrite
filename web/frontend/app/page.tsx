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
import {
  Button,
  Textarea,
  Checkbox,
  Select,
  Tabs,
  Card,
  Badge,
  useToast,
} from "@/components/ui";

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

  const toast = useToast();

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
          toast.error(String(err));
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
      toast.error(String(err));
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
      toast.error(String(err));
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
            toast.error(String(err));
          }
          setRunning(false);
        }
      );
    } catch (err) {
      push("err", String(err));
      toast.error(String(err));
      setRunning(false);
    }
  }

  const canPublish = account?.wechat_bound ?? false;

  // Log line color mapping
  const lineClass: Record<string, string> = {
    step: "text-accent font-medium",
    log: "text-text/80",
    notice: "text-amber-400",
    tool: "text-muted",
    err: "text-red-400",
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-text">一句话，生成内容并一键分发多平台</h1>
        <p className="mt-1 text-sm text-muted leading-relaxed">
          选题 → 写作 → 反 AI 与原创度把关 → 多平台智能改写 → 分发到公众号 · 小红书 · 抖音。
        </p>
      </div>

      <Card className="space-y-5">
        <h2 className="text-base font-semibold tracking-tight text-text">写什么</h2>
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted">需求（一句话）</label>
          <Textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="例如：写一篇关于 AI Agent 的公众号文章"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted">写作人格</label>
            <Select
              value={persona}
              onValueChange={setPersona}
              options={[
                { value: "", label: `沿用我的默认（${account?.writing_persona ?? "…"}）` },
                ...personas.map((p) => ({ value: p.id, label: p.label, description: p.description })),
              ]}
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted">排版主题</label>
            <Select
              value={theme}
              onValueChange={setTheme}
              options={[
                { value: "", label: `沿用我的默认（${account?.theme ?? "…"}）` },
                ...themes.map((t) => ({ value: t.id, label: t.id, description: t.description || undefined })),
              ]}
            />
          </div>
        </div>

        <div className="space-y-2">
          <Checkbox
            id="interactive"
            checked={interactive}
            onCheckedChange={setInteractive}
          >
            交互模式（在选题/框架/配图处暂停确认）
          </Checkbox>

          <Checkbox
            id="publish"
            checked={publishDraft && canPublish}
            onCheckedChange={setPublishDraft}
            disabled={!canPublish}
          >
            完成后推送到我的公众号草稿箱
          </Checkbox>
        </div>

        {!canPublish && (
          <p className="text-sm text-muted">
            尚未绑定公众号。前往{" "}
            <Link href="/settings" className="text-accent hover:underline">
              设置
            </Link>{" "}
            绑定 appid/secret 后即可一键推送草稿箱（其余环节无需任何配置）。
          </p>
        )}

        <div>
          <Button onClick={onSubmit} disabled={running || !prompt.trim()} variant="primary">
            {running ? "生成中…" : "开始生成"}
          </Button>
        </div>
      </Card>

      {(lines.length > 0 || running) && (
        <Card>
          <div className="mb-2 flex items-center gap-2">
            <h2 className="text-base font-semibold tracking-tight text-text">实时进度</h2>
            {running && <Badge tone="neutral">running</Badge>}
          </div>
          <div
            ref={logRef}
            className="h-64 overflow-y-auto rounded-md bg-surface-2 p-3 font-mono text-xs space-y-0.5"
          >
            {lines.map((l, i) => (
              <div key={i} className={lineClass[l.kind] ?? "text-text"}>
                {l.text}
              </div>
            ))}
          </div>
        </Card>
      )}

      {result && (
        <Card className="space-y-5">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold tracking-tight text-text">成稿</h2>
            <Badge
              tone={
                result.status === "done"
                  ? "ok"
                  : result.status === "error"
                  ? "danger"
                  : "neutral"
              }
            >
              {result.status}
            </Badge>
            {result.title && (
              <span className="text-sm text-muted">· {result.title}</span>
            )}
          </div>

          {result.error && (
            <p className="rounded-md bg-red-950/30 px-3 py-2 text-sm text-red-400">
              {result.error}
            </p>
          )}

          {result.images && result.images.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {result.images.map((src, i) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  key={i}
                  src={artifactUrl(src)}
                  alt={`配图 ${i + 1}`}
                  className="h-28 w-28 rounded-lg border border-border object-cover"
                />
              ))}
            </div>
          )}

          {result.article_markdown ? (
            <div className="space-y-3">
              <div className="flex justify-end">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() =>
                    navigator.clipboard.writeText(result.article_markdown ?? "")
                  }
                >
                  复制 Markdown
                </Button>
              </div>
              <Tabs
                value={tab}
                onValueChange={(v) => setTab(v as "preview" | "markdown")}
                items={[
                  {
                    value: "preview",
                    label: "微信预览",
                    content: result.preview_html ? (
                      <iframe
                        className="h-[600px] w-full rounded-md border border-border"
                        srcDoc={result.preview_html}
                        title="preview"
                      />
                    ) : (
                      <p className="text-sm text-muted">
                        未生成预览 HTML（可切到 Markdown 查看正文）。
                      </p>
                    ),
                  },
                  {
                    value: "markdown",
                    label: "Markdown",
                    content: (
                      <pre className="overflow-x-auto whitespace-pre-wrap rounded-md bg-surface-2 p-4 text-xs text-text">
                        {result.article_markdown}
                      </pre>
                    ),
                  },
                ]}
              />
            </div>
          ) : (
            <p className="text-sm text-muted">未找到成稿文件。请查看上方进度日志排查。</p>
          )}

          {result.article_markdown && <PublishPanel jobId={result.id} />}

          {result.article_markdown && (
            <div>
              <Button
                variant="secondary"
                onClick={onDistributeFromResult}
                disabled={distributing}
              >
                {distributing ? "分发中…" : "分发到多平台（小红书 + 抖音）"}
              </Button>
            </div>
          )}

          {result.platform_versions && result.platform_versions.length > 0 && (
            <PlatformVersions versions={result.platform_versions} />
          )}
        </Card>
      )}

      {/* 分发任务进度 */}
      {(distLines.length > 0 || distributing) && (
        <Card>
          <div className="mb-2 flex items-center gap-2">
            <h2 className="text-base font-semibold tracking-tight text-text">分发进度</h2>
            {distributing && <Badge tone="neutral">running</Badge>}
          </div>
          <div
            ref={distLogRef}
            className="h-48 overflow-y-auto rounded-md bg-surface-2 p-3 font-mono text-xs space-y-0.5"
          >
            {distLines.map((l, i) => (
              <div key={i} className={lineClass[l.kind] ?? "text-text"}>
                {l.text}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* 分发结果（多平台版本） */}
      {distResult && distResult.platform_versions && distResult.platform_versions.length > 0 && (
        <Card className="space-y-5">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold tracking-tight text-text">多平台版本</h2>
            <Badge
              tone={
                distResult.status === "done"
                  ? "ok"
                  : distResult.status === "error"
                  ? "danger"
                  : "neutral"
              }
            >
              {distResult.status}
            </Badge>
          </div>
          {distResult.error && (
            <p className="rounded-md bg-red-950/30 px-3 py-2 text-sm text-red-400">
              {distResult.error}
            </p>
          )}
          <PlatformVersions versions={distResult.platform_versions} />
        </Card>
      )}

      {/* 带稿来：直接粘贴正文进行多平台分发 */}
      <Card className="space-y-5">
        <h2 className="text-base font-semibold tracking-tight text-text">带稿来 · 直接分发已有文章</h2>
        <p className="text-sm text-muted leading-relaxed">粘贴任意文章正文，自动改写为小红书和抖音风格版本。</p>
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted">文章正文（Markdown 或纯文本）</label>
          <Textarea
            value={srcText}
            onChange={(e) => setSrcText(e.target.value)}
            placeholder="在此粘贴文章内容…"
            className="min-h-[140px]"
          />
        </div>
        <div>
          <Button
            variant="primary"
            onClick={onDistributeFromText}
            disabled={distributing || !srcText.trim()}
          >
            {distributing ? "分发中…" : "开始分发"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
