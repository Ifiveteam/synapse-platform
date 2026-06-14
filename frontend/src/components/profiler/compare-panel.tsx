import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ApiError } from "@/api/client";
import { compareSnapshots, getSnapshots } from "@/api/profiler";
import { AXIS_LABELS, formatPercent, LAYER_B_LABELS } from "@/lib/profiler/labels";
import type { CompareResponse } from "@/api/types/profiler";
import { SYNAPSE_AXIS_KEYS } from "@/api/types/profiler";

interface ComparePanelProps {
  userId: string;
}

export function ComparePanel({ userId }: ComparePanelProps) {
  const [versions, setVersions] = useState<string[]>([]);
  const [fromVersion, setFromVersion] = useState("");
  const [toVersion, setToVersion] = useState("");
  const [compare, setCompare] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await getSnapshots(userId);
        if (cancelled) return;
        setVersions(res.versions);
        if (res.versions.length >= 2) {
          setFromVersion(res.versions[0]);
          setToVersion(res.versions[res.versions.length - 1]);
        } else if (res.versions.length === 1) {
          setFromVersion(res.versions[0]);
          setToVersion(res.versions[0]);
        }
      } catch {
        if (!cancelled) setVersions([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [userId]);

  const runCompare = useCallback(async () => {
    if (!fromVersion || !toVersion) return;
    setLoading(true);
    setError(null);
    try {
      const data = await compareSnapshots(userId, fromVersion, toVersion);
      setCompare(data);
    } catch (err) {
      setCompare(null);
      setError(err instanceof ApiError ? err.message : "비교에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }, [userId, fromVersion, toVersion]);

  useEffect(() => {
    if (versions.length >= 2 && fromVersion && toVersion && fromVersion !== toVersion) {
      void runCompare();
    }
  }, [versions, fromVersion, toVersion, runCompare]);

  if (versions.length < 2) {
    return (
      <Card>
        <CardContent className="text-muted-foreground py-8 text-center text-sm">
          이 페르소나에는 비교할 스냅샷이 2개 이상 없습니다.
          <br />
          <code className="text-xs">mock_jiyeon</code>은 v1·v2 데모 데이터가 있습니다.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="text-muted-foreground mb-1 block text-xs">From</span>
          <select
            className="border-input bg-background rounded-md border px-2 py-1.5 text-sm"
            value={fromVersion}
            onChange={(e) => setFromVersion(e.target.value)}
          >
            {versions.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="text-muted-foreground mb-1 block text-xs">To</span>
          <select
            className="border-input bg-background rounded-md border px-2 py-1.5 text-sm"
            value={toVersion}
            onChange={(e) => setToVersion(e.target.value)}
          >
            {versions.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
        </label>
        <Button type="button" size="sm" onClick={() => void runCompare()} disabled={loading}>
          {loading ? "비교 중…" : "비교"}
        </Button>
      </div>

      {error && (
        <p className="text-destructive text-sm" role="alert">
          {error}
        </p>
      )}

      {compare && (
        <>
          {compare.anomalies.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">이상 징후</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {compare.anomalies.map((item) => (
                  <p
                    key={item.code}
                    className={`rounded-md border px-3 py-2 text-sm ${
                      item.severity === "alert"
                        ? "border-destructive/50 bg-destructive/5"
                        : "border-border"
                    }`}
                  >
                    {item.message}
                  </p>
                ))}
              </CardContent>
            </Card>
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">8축 변화</CardTitle>
                <CardDescription>
                  {compare.delta.from_version} → {compare.delta.to_version}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm">
                  {SYNAPSE_AXIS_KEYS.map((key) => {
                    const delta = compare.delta.axes_delta[key];
                    return (
                      <li key={key} className="flex justify-between gap-2">
                        <span>{AXIS_LABELS[key]}</span>
                        <span
                          className={`font-mono ${
                            delta > 0 ? "text-green-700" : delta < 0 ? "text-red-700" : ""
                          }`}
                        >
                          {formatPercent(delta, true)}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Layer B 변화</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm">
                  {(
                    Object.keys(LAYER_B_LABELS) as Array<keyof typeof LAYER_B_LABELS>
                  ).map((key) => {
                    const delta =
                      compare.delta.layer_b_delta[
                        key as keyof typeof compare.delta.layer_b_delta
                      ];
                    const isIndex = key === "taste_diversity_index";
                    return (
                      <li key={key} className="flex justify-between gap-2">
                        <span>{LAYER_B_LABELS[key]}</span>
                        <span className="font-mono">
                          {isIndex
                            ? `${delta >= 0 ? "+" : ""}${delta.toFixed(1)}`
                            : formatPercent(delta, true).replace("점", "p")}
                        </span>
                      </li>
                    );
                  })}
                </ul>
                {(compare.delta.top5_added.length > 0 ||
                  compare.delta.top5_removed.length > 0) && (
                  <div className="border-t mt-4 pt-4 text-xs">
                    {compare.delta.top5_added.length > 0 && (
                      <p className="text-green-700">
                        추가: {compare.delta.top5_added.join(", ")}
                      </p>
                    )}
                    {compare.delta.top5_removed.length > 0 && (
                      <p className="text-red-700 mt-1">
                        제거: {compare.delta.top5_removed.join(", ")}
                      </p>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
