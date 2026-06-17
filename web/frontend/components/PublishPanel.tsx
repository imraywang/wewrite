"use client";

import { useEffect, useRef, useState } from "react";
import {
  LoginChallenge,
  PlatformStatus,
  getPlatforms,
  loginStatus,
  logoutPlatform,
  publishTo,
  startLogin,
} from "@/lib/api";
import { Badge, Button, Card, Dialog, Tooltip, useToast } from "@/components/ui";

// 任务成稿后的「发布到各平台」面板。
export default function PublishPanel({ jobId }: { jobId: string }) {
  const [platforms, setPlatforms] = useState<PlatformStatus[]>([]);
  const [qr, setQr] = useState<{ platform: string; ch: LoginChallenge } | null>(null);
  const [busy, setBusy] = useState<string>("");
  const [msg, setMsg] = useState<Record<string, string>>({});
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const toast = useToast();

  async function refresh() {
    try {
      setPlatforms(await getPlatforms());
    } catch {
      /* ignore */
    }
  }
  useEffect(() => {
    refresh();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  function setPlatMsg(id: string, text: string) {
    setMsg((m) => ({ ...m, [id]: text }));
  }

  async function onLogin(platform: string) {
    setBusy(platform);
    setPlatMsg(platform, "");
    try {
      const ch = await startLogin(platform);
      setQr({ platform, ch });
      // 轮询登录状态
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        try {
          const st = await loginStatus(platform);
          if (st.logged_in) {
            if (pollRef.current) clearInterval(pollRef.current);
            setQr(null);
            setPlatMsg(platform, `已登录${st.user_name ? "：" + st.user_name : ""} ✓`);
            refresh();
          }
        } catch {
          /* keep polling */
        }
      }, 2500);
    } catch (e) {
      setPlatMsg(platform, "登录失败：" + String(e));
      toast.error("登录失败：" + String(e));
    } finally {
      setBusy("");
    }
  }

  async function onLogout(platform: string) {
    await logoutPlatform(platform);
    setPlatMsg(platform, "已登出");
    refresh();
  }

  async function onPublish(platform: string) {
    setBusy(platform);
    setPlatMsg(platform, "");
    try {
      const r = await publishTo(platform, { job_id: jobId });
      const text = r.ok ? `发布成功 ✓ ${r.url || ""}` : `发布失败：${r.detail}`;
      setPlatMsg(platform, text);
      if (r.ok) {
        toast.notice(text);
      } else {
        toast.error(`发布失败：${r.detail}`);
      }
    } catch (e) {
      const text = "发布失败：" + String(e);
      setPlatMsg(platform, text);
      toast.error(text);
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="mt-4 border-t border-border pt-4">
      <h2 className="mb-3 text-base font-semibold text-text">发布到平台</h2>
      <div className="flex flex-col gap-2.5">
        {platforms.map((p) => (
          <Card key={p.id} className="flex flex-wrap items-center gap-3 py-2.5 px-3.5">
            <strong className="min-w-[90px] text-text">
              {p.note ? (
                <Tooltip content={p.note}>{p.label}</Tooltip>
              ) : (
                p.label
              )}
            </strong>

            {!p.available ? (
              <Badge tone="neutral">未开放</Badge>
            ) : p.logged_in ? (
              <Badge tone="ok">
                已登录{p.user_name ? "：" + p.user_name : ""}
              </Badge>
            ) : (
              <Badge tone="warn">未登录</Badge>
            )}

            <span className="flex-1 text-xs text-muted">
              {msg[p.id] || ""}
            </span>

            {p.available && p.login_kind === "qrcode" && !p.logged_in && (
              <Button
                variant="secondary"
                size="sm"
                disabled={busy === p.id}
                onClick={() => onLogin(p.id)}
              >
                {busy === p.id ? "…" : "扫码登录"}
              </Button>
            )}
            {p.available && p.logged_in && p.login_kind === "qrcode" && (
              <Button variant="ghost" size="sm" onClick={() => onLogout(p.id)}>
                登出
              </Button>
            )}
            {p.available && p.id !== "wechat" && (
              <Button
                variant="primary"
                size="sm"
                disabled={busy === p.id || !p.logged_in}
                onClick={() => onPublish(p.id)}
              >
                发布
              </Button>
            )}
            {p.id === "wechat" && (
              <span className="text-xs text-muted">
                （创建任务时勾选「推送草稿箱」由管道发布）
              </span>
            )}
          </Card>
        ))}
      </div>

      {/* QR 登录弹窗 */}
      <Dialog
        open={qr !== null}
        onOpenChange={(open) => {
          if (!open) setQr(null);
        }}
        title={qr ? `扫码登录 · ${qr.platform}` : "扫码登录"}
      >
        {qr && (
          <div className="flex flex-col items-center gap-3 text-center">
            {qr.ch.qrcode_image ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={qr.ch.qrcode_image}
                alt="二维码"
                className="rounded-lg bg-white"
                style={{ width: 220, height: 220 }}
              />
            ) : (
              <p className="text-sm text-muted">未返回二维码：{qr.ch.detail}</p>
            )}
            {qr.ch.detail && (
              <p className="text-sm text-muted">{qr.ch.detail}</p>
            )}
          </div>
        )}
      </Dialog>
    </div>
  );
}
