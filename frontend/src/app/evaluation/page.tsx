"use client";

import React, { useEffect, useState } from "react";
import { useAppState } from "@/lib/i18n";
import { apiClient, getSavedSession } from "@/lib/api-client";
import { Card, Badge, Button } from "@/components/ui/primitives";
import { FlaskConical, Play, Download, CheckCircle2, Sparkles } from "lucide-react";

export default function ResearchEvaluationPage() {
  const { lang, t } = useAppState();
  const [evalData, setEvalData] = useState<Record<string, any> | null>(null);
  const [running, setRunning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunEvaluation = async () => {
    setRunning(true);
    setError(null);
    try {
      const res = await apiClient.runEvaluationSuite();
      setEvalData(res);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  };

  useEffect(() => {
    handleRunEvaluation();
  }, []);

  const handleExport = async (format: "json" | "csv") => {
    if (!evalData?.id) return;
    try {
      const session = getSavedSession();
      const res = await fetch(
        apiClient.getEvaluationExportUrl(evalData.id, format),
        {
          headers: session
            ? { Authorization: `Bearer ${session.access_token}` }
            : {},
        }
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `techval_phase4_evaluation_${evalData.id.slice(0, 8)}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const summary = evalData?.metrics_summary || {};
  const conds = summary.conditions_summary || {};
  const mainCond = conds.multi_agent_validated || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{t.nav.evaluation}</h1>
          <p className="text-sm text-slate-600">
            {lang === "id"
              ? "Suite Evaluasi Riset Fase 4: Precision/Recall/F1, QWK, ICC(2,1)/ICC(3,1) dengan 95% Bootstrap CI, MAE/RMSE/sMAPE Finansial, dan Studi 4 Kondisi."
              : "Phase 4 Research Evaluation Suite: Precision/Recall/F1, QWK, ICC(2,1)/ICC(3,1) with 95% Bootstrap CIs, Financial MAE/RMSE/sMAPE, and 4-Condition Comparison."}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button onClick={handleRunEvaluation} disabled={running}>
            <Play className="h-4 w-4" />
            {running ? "Running Benchmark..." : "Re-Run Evaluation Suite"}
          </Button>
          <Button variant="outline" onClick={() => handleExport("csv")}>
            <Download className="h-4 w-4" /> Export CSV
          </Button>
          <Button variant="outline" onClick={() => handleExport("json")}>
            <Download className="h-4 w-4" /> Export JSON
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 p-3 text-xs text-rose-800">
          {t.common.errorPrefix} {error}
        </div>
      )}

      {evalData && mainCond.extraction && (
        <>
          <div className="flex items-center justify-between rounded-md border border-amber-300 bg-amber-50 px-4 py-2.5 text-xs text-amber-900">
            <span className="flex items-center gap-2 font-semibold">
              <Sparkles className="h-4 w-4" />
              {summary.synthetic_warning_banner}
            </span>
            <Badge variant="warning">Synthetic Benchmark Corpus</Badge>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {/* IE Metrics */}
            <Card className="space-y-2 border-l-4 border-l-blue-600">
              <div className="text-xs font-bold uppercase text-slate-500">
                1. Information Extraction (multi_agent_validated)
              </div>
              <div className="text-2xl font-bold text-slate-900">
                F1: {(Number(mainCond.extraction.f1) * 100).toFixed(2)}%
              </div>
              <div className="text-xs text-slate-600">
                Precision: {(Number(mainCond.extraction.precision) * 100).toFixed(2)}% |
                Recall: {(Number(mainCond.extraction.recall) * 100).toFixed(2)}%
              </div>
            </Card>

            {/* Expert Agreement */}
            <Card className="space-y-2 border-l-4 border-l-indigo-600">
              <div className="text-xs font-bold uppercase text-slate-500">
                2. Expert Scoring Agreement (QWK & ICC)
              </div>
              <div className="text-2xl font-bold text-indigo-800">
                QWK: {Number(mainCond.agreement_qwk?.qwk || 0).toFixed(4)}
              </div>
              <div className="text-xs text-slate-600">
                ICC(2,1):{" "}
                {Number(mainCond.agreement_icc?.icc_2_1_absolute_agreement || 0).toFixed(
                  4
                )}{" "}
                | ICC(3,1):{" "}
                {Number(mainCond.agreement_icc?.icc_3_1_consistency || 0).toFixed(4)}
              </div>
            </Card>

            {/* Financial Engine Determinism */}
            <Card className="space-y-2 border-l-4 border-l-emerald-600">
              <div className="text-xs font-bold uppercase text-slate-500">
                3. Financial Engine Determinism (IDR)
              </div>
              <div className="text-2xl font-bold text-emerald-800">
                MAE: Rp {Number(mainCond.valuation_error_idr?.mae || 0).toFixed(2)}
              </div>
              <div className="text-xs text-slate-600">
                RMSE: Rp {Number(mainCond.valuation_error_idr?.rmse || 0).toFixed(2)} |
                sMAPE:{" "}
                {Number(mainCond.valuation_error_idr?.smape_percent || 0).toFixed(2)}%
              </div>
              <div className="text-[11px] text-emerald-700 font-semibold flex items-center gap-1">
                <CheckCircle2 className="h-3.5 w-3.5" /> Exact match to independent
                hand-calculated WIPO fixtures
              </div>
            </Card>
          </div>

          {/* 4-Condition Comparison Table */}
          <Card className="space-y-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <FlaskConical className="h-4 w-4 text-blue-700" />
              <span>
                Four-Condition Research Evaluation Matrix (human_expert vs. llm_only vs.
                multi_agent vs. multi_agent_validated)
              </span>
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 uppercase">
                    <th className="py-2.5 px-3">Condition</th>
                    <th className="py-2.5 px-3">IE F1</th>
                    <th className="py-2.5 px-3">QWK</th>
                    <th className="py-2.5 px-3">ICC(2,1)</th>
                    <th className="py-2.5 px-3">Citation Resolution</th>
                    <th className="py-2.5 px-3">Unsupported Claim Rejection</th>
                    <th className="py-2.5 px-3">Valuation MAE (IDR)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {Object.values(conds).map((row: any) => (
                    <tr
                      key={row.condition}
                      className={
                        row.condition === "multi_agent_validated"
                          ? "bg-blue-50/60 font-semibold"
                          : ""
                      }
                    >
                      <td className="py-2.5 px-3 font-mono text-slate-900">
                        {row.condition}
                      </td>
                      <td className="py-2.5 px-3 font-mono">
                        {(Number(row.extraction.f1) * 100).toFixed(2)}%
                      </td>
                      <td className="py-2.5 px-3 font-mono">
                        {Number(row.agreement_qwk?.qwk || 0).toFixed(4)}
                      </td>
                      <td className="py-2.5 px-3 font-mono">
                        {Number(
                          row.agreement_icc?.icc_2_1_absolute_agreement || 0
                        ).toFixed(4)}
                      </td>
                      <td className="py-2.5 px-3 font-mono">
                        {(
                          Number(
                            row.citation_traceability?.citation_resolution_precision ||
                              0
                          ) * 100
                        ).toFixed(1)}
                        %
                      </td>
                      <td className="py-2.5 px-3 font-mono">
                        {(
                          Number(
                            row.citation_traceability
                              ?.unsupported_claim_rejection_rate || 0
                          ) * 100
                        ).toFixed(1)}
                        %
                      </td>
                      <td className="py-2.5 px-3 font-mono">
                        Rp {Number(row.valuation_error_idr?.mae || 0).toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
