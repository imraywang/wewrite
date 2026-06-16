"use client";

import { PlatformVersion } from "@/lib/api";

export default function PlatformVersions({ versions }: { versions: PlatformVersion[] }) {
  if (!versions?.length) return null;
  return (
    <div className="platform-versions">
      {versions.map((v) => (
        <div key={v.platform} className="version-card">
          <div className="version-head">
            <strong>{v.label}</strong>
            {v.status === "failed" ? (
              <span className="pv-badge pv-warn">未产出</span>
            ) : (
              <span className={`pv-badge ${v.passed ? "pv-ok" : "pv-warn"}`}>
                {v.max_similarity != null
                  ? `相似度 ${Math.round(v.max_similarity * 100)}%`
                  : ""}
                {v.humanness != null
                  ? ` · 拟人 ${Math.round(v.humanness * 100)}%`
                  : ""}
                {v.passed ? "" : " · 待微调"}
              </span>
            )}
          </div>
          {v.warning && <p className="muted">{v.warning}</p>}
          {v.status !== "failed" && (
            <>
              <pre className="version-md">{v.markdown}</pre>
              <button
                className="btn secondary"
                style={{ marginTop: 8 }}
                onClick={() => navigator.clipboard.writeText(v.markdown)}
              >
                复制
              </button>
            </>
          )}
        </div>
      ))}
    </div>
  );
}
