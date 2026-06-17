"use client";

import { useEffect, useState } from "react";
import {
  AccountState,
  CatalogItem,
  bindWeChat,
  getAccount,
  getPersonas,
  getThemes,
  saveStyle,
  unbindWeChat,
} from "@/lib/api";
import { Badge, Button, Card, Input, Select } from "@/components/ui";
import { useToast } from "@/components/ui/Toast";

export default function SettingsPage() {
  const [account, setAccount] = useState<AccountState | null>(null);
  const [personas, setPersonas] = useState<CatalogItem[]>([]);
  const [themes, setThemes] = useState<CatalogItem[]>([]);
  const [msg, setMsg] = useState("");
  const toast = useToast();

  // style form
  const [accountName, setAccountName] = useState("");
  const [persona, setPersona] = useState("midnight-friend");
  const [theme, setTheme] = useState("professional-clean");
  const [audience, setAudience] = useState("");
  const [tone, setTone] = useState("");

  // wechat form
  const [appid, setAppid] = useState("");
  const [secret, setSecret] = useState("");
  const [author, setAuthor] = useState("");

  useEffect(() => {
    getPersonas().then(setPersonas).catch(() => {});
    getThemes().then(setThemes).catch(() => {});
    getAccount()
      .then((a) => {
        setAccount(a);
        setAccountName(a.account_name);
        setPersona(a.writing_persona);
        setTheme(a.theme);
        setAudience(a.audience);
        setTone(a.tone);
        setAuthor(a.wechat_author);
      })
      .catch(() => {});
  }, []);

  async function onSaveStyle() {
    setMsg("");
    try {
      const a = await saveStyle({
        account_name: accountName,
        writing_persona: persona,
        theme,
        audience,
        tone,
      });
      setAccount(a);
      setMsg("风格已保存 ✓");
      toast.notice("风格已保存");
    } catch (e) {
      setMsg("保存失败：" + String(e));
      toast.error("保存失败：" + String(e));
    }
  }

  async function onBind() {
    setMsg("");
    try {
      const a = await bindWeChat({ appid, secret, author });
      setAccount(a);
      setAppid("");
      setSecret("");
      setMsg("公众号已绑定 ✓（appid/secret 已加密存储）");
      toast.notice("公众号已绑定（appid/secret 已加密存储）");
    } catch (e) {
      setMsg("绑定失败：" + String(e));
      toast.error("绑定失败：" + String(e));
    }
  }

  async function onUnbind() {
    setMsg("");
    try {
      const a = await unbindWeChat();
      setAccount(a);
      setMsg("已解绑公众号");
      toast.notice("已解绑公众号");
    } catch (e) {
      setMsg("解绑失败：" + String(e));
      toast.error("解绑失败：" + String(e));
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-text">设置</h1>
        <p className="mt-1 text-sm text-muted leading-relaxed">配置一次，之后每篇文章自动沿用。</p>
      </div>

      {msg && (
        <p className="text-sm text-muted bg-surface-2 rounded-md px-3 py-2 border border-border">
          {msg}
        </p>
      )}

      <Card>
        <h2 className="text-base font-semibold tracking-tight text-text mb-4">公众号风格</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted">公众号名称</label>
            <Input
              value={accountName}
              onChange={(e) => setAccountName(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted">写作人格</label>
            <Select
              value={persona}
              onValueChange={setPersona}
              options={personas.map((p) => ({ value: p.id, label: p.label, description: p.description }))}
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted">默认排版主题</label>
            <Select
              value={theme}
              onValueChange={setTheme}
              options={themes.map((t) => ({ value: t.id, label: t.id, description: t.description || undefined }))}
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted">目标读者（可选）</label>
            <Input
              value={audience}
              onChange={(e) => setAudience(e.target.value)}
              placeholder="如：关注 AI 的产品经理"
            />
          </div>
        </div>
        <div className="mt-4 space-y-1.5">
          <label className="text-xs font-medium text-muted">语气补充（可选）</label>
          <Input
            value={tone}
            onChange={(e) => setTone(e.target.value)}
            placeholder="如：专业但不端着，多用具体例子"
          />
        </div>
        <div className="mt-4">
          <Button variant="primary" onClick={onSaveStyle}>
            保存风格
          </Button>
        </div>
      </Card>

      <Card>
        <div className="flex items-center gap-2 mb-3">
          <h2 className="text-base font-semibold tracking-tight text-text">微信公众号绑定</h2>
          {account?.wechat_bound ? (
            <Badge tone="ok">已绑定</Badge>
          ) : (
            <Badge tone="neutral">未绑定</Badge>
          )}
        </div>
        <p className="text-sm text-muted leading-relaxed mb-4">
          推送到<strong className="text-text">你自己的</strong>公众号草稿箱需要你自己的 appid/secret —— 这是平台无法代为提供的唯一一项。
          其余（LLM、AI 配图）均由平台统一承担，你无需任何配置。凭证将<strong className="text-text">加密存储</strong>，仅在生成时临时注入。
        </p>
        {account?.wechat_bound ? (
          <div className="space-y-3">
            <p className="text-sm text-muted">
              当前署名：<span className="text-text">{account.wechat_author || "（未设置）"}</span>
            </p>
            <Button variant="danger" onClick={onUnbind}>
              解绑公众号
            </Button>
          </div>
        ) : (
          <div className="space-y-5">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted">AppID</label>
                <Input
                  value={appid}
                  onChange={(e) => setAppid(e.target.value)}
                  placeholder="wx..."
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted">AppSecret</label>
                <Input
                  type="password"
                  value={secret}
                  onChange={(e) => setSecret(e.target.value)}
                  placeholder="••••••••"
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted">默认署名（可选）</label>
              <Input value={author} onChange={(e) => setAuthor(e.target.value)} />
            </div>
            <Button variant="primary" onClick={onBind} disabled={!appid || !secret}>
              绑定公众号
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}
