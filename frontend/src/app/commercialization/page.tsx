"use client";

import React, { useEffect, useState } from "react";
import { useAppState } from "@/lib/i18n";
import { apiClient } from "@/lib/api-client";
import type { AssessmentRevisionItem, IndicatorDefinitionItem } from "@/lib/api-types";
import { Card, Badge, Button } from "@/components/ui/primitives";
import { formatNormalizedScore } from "@/lib/utils";
import { TrendingUp, Scale, ShieldAlert, Search, CheckCircle2 } from "lucide-react";

const DEFAULT_COMM_CODES = [
  "COMM_MARKET_DEMAND",
  "COMM_COMPETITIVE_POSITION",
  "COMM_REGULATORY",
  "COMM_SUPPLY_CHAIN",
  "COMM_IP_LICENSING_READINESS",
];

export default function CommercializationAhpPage() {
  const { lang, t, selectedTechId } = useAppState();
  const [revision, setRevision] = useState<AssessmentRevisionItem | null>(null);
  const [definitions, setDefinitions] = useState<IndicatorDefinitionItem[]>([]);
  const [ahpMatrix, setAhpMatrix] = useState<number[][]>([
    [1, 2, 2, 3, 2],
    [0.5, 1, 1, 2, 1],
    [0.5, 1, 1, 2, 1],
    [1 / 3, 0.5, 0.5, 1, 0.5],
    [0.5, 1, 1, 2, 1],
  ]);
  const [ahpResult, setAhpResult] = useState<Record<string, any> | null>(null);
  const [patentNumber, setPatentNumber] = useState<string>("IDP000089421");
  const [patentResult, setPatentResult] = useState<Record<string, any> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    if (!selectedTechId) return;
    try {
      const [rev, defs] = await Promise.all([
        apiClient.getLatestRevision(selectedTechId),
        apiClient.listIndicators(),
      ]);
      setRevision(rev);
      setDefinitions(defs);
      setPatentResult(rev.ip_patent_signals_json || null);
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedTechId]);

  const handleCellChange = (r: number, c: number, val: number) => {
    if (r === c || val <= 0) return;
    const copy = ahpMatrix.map((row) => [...row]);
    copy[r][c] = val;
    copy[c][r] = Number((1 / val).toFixed(4));
    setAhpMatrix(copy);
  };

  const handleRunAhp = async () => {
    setError(null);
    try {
      const res = await apiClient.computeAhp({
        dimension: "commercialization_readiness",
        indicator_codes: DEFAULT_COMM_CODES,
        matrix: ahpMatrix,
        persist_as_weight_set: false,
        expert_rationale:
          "Saaty 1-9 pairwise calibration for Commercialization Readiness indicators.",
      });
      setAhpResult(res);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handlePatentLookup = async () => {
    setError(null);
    try {
      const res = await apiClient.lookupPatentSignals({
        patent_number: patentNumber,
        jurisdiction: "ID",
        manual_signals: {
          patent_status: "patent_pending",
          family_size: 2,
          forward_citations_5yr: 3,
           backward_citations: 11,
          independent_claims_count: 3,
          legal_status: "Substantive Examination (DJKI Indonesia)",
        },
      });
      setPatentResult(res);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const commScores =
    revision?.indicator_scores.filter(
      (s) => s.dimension === "commercialization_readiness"
    ) || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{t.nav.commercialization}</h1>
        <p className="text-sm text-slate-600">
          {lang === "id"
            ? "Dimensi 2: Kesiapan Komersialisasi, Sinyal Paten Kontekstual (Harhoff et al., 2003), dan Kalibrasi Bobot Saaty AHP (CR <= 0.10)."
            : "Dimension 2: Commercialization Readiness, Contextual Patent Signals (Harhoff et al., 2003), and Saaty AHP Weight Calibration (CR <= 0.10)."}
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 p-3 text-xs text-rose-800">
          {t.common.errorPrefix} {error}
        </div>
      )}

      {/* Commercialization Indicators */}
      <Card className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-indigo-700" />
            <span>
              Commercialization Readiness Indicators — Composite:{" "}
              {formatNormalizedScore(revision?.commercialization_readiness_score)}
            </span>
          </h2>
          <Badge variant="info">
            Completeness: {((revision?.comm_completeness_score || 0) * 100).toFixed(1)}%
          </Badge>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 uppercase">
                <th className="py-2 px-3">Indicator</th>
                <th className="py-2 px-3">Status</th>
                <th className="py-2 px-3">Raw (1–5)</th>
                <th className="py-2 px-3">Normalized [0, 1]</th>
                <th className="py-2 px-3">Renorm Weight</th>
                <th className="py-2 px-3">Rationale</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {commScores.map((s) => {
                const def = definitions.find((d) => d.code === s.indicator_code);
                return (
                  <tr key={s.id}>
                    <td className="py-2.5 px-3">
                      <div className="font-bold text-slate-900">{s.indicator_code}</div>
                      <div className="text-slate-500">
                        {lang === "id" ? def?.name_id : def?.name_en}
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <Badge
                        variant={s.status === "observed" ? "success" : "warning"}
                      >
                        {s.status}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 font-bold">{s.raw_score ?? "—"}</td>
                    <td className="py-2.5 px-3 font-mono">
                      {s.normalized_score !== null ? s.normalized_score.toFixed(4) : "—"}
                    </td>
                    <td className="py-2.5 px-3 font-mono">
                      {s.renormalized_weight.toFixed(4)}
                    </td>
                    <td className="py-2.5 px-3 text-slate-700 max-w-md">
                      {lang === "id" ? s.rationale_id : s.rationale_en}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Saaty AHP Calculator */}
        <Card className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Scale className="h-4 w-4 text-blue-700" />
              <span>Saaty AHP Pairwise Weight Calibration (CR &le; 0.10)</span>
            </h2>
            <Button size="sm" onClick={handleRunAhp}>
              Compute Eigenvector & CR
            </Button>
          </div>
          <p className="text-xs text-slate-600">
            Modify upper-triangle reciprocal ratios $a_{"{ij}"} \in [1/9, 9]$. Lower
            triangle updates automatically as $a_{"{ji}"} = 1/a_{"{ij}"}$.
          </p>

          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-[11px]">
              <thead>
                <tr className="bg-slate-100 text-slate-700">
                  <th className="border p-1.5">Indicator</th>
                  {DEFAULT_COMM_CODES.map((c) => (
                    <th key={c} className="border p-1.5 font-mono">
                      {c.replace("COMM_", "")}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {DEFAULT_COMM_CODES.map((rowCode, r) => (
                  <tr key={rowCode}>
                    <td className="border p-1.5 font-mono font-bold bg-slate-50">
                      {rowCode.replace("COMM_", "")}
                    </td>
                    {DEFAULT_COMM_CODES.map((colCode, c) => (
                      <td key={colCode} className="border p-1 text-center">
                        {r < c ? (
                          <input
                            type="number"
                            step="0.25"
                            min="0.111"
                            max="9"
                            value={ahpMatrix[r][c]}
                            onChange={(e) =>
                              handleCellChange(r, c, Number(e.target.value))
                            }
                            className="w-14 rounded border border-blue-300 bg-blue-50/40 px-1 py-0.5 text-center font-mono"
                          />
                        ) : (
                          <span className="font-mono text-slate-600">
                            {ahpMatrix[r][c].toFixed(3)}
                          </span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {ahpResult && (
            <div
              className={`rounded border p-3 text-xs space-y-1.5 ${
                ahpResult.is_consistent
                  ? "border-emerald-300 bg-emerald-50 text-emerald-900"
                  : "border-rose-300 bg-rose-50 text-rose-900"
              }`}
            >
              <div className="flex items-center justify-between font-bold">
                <span>
                  Principal Eigenvalue &lambda;_max ={" "}
                  {ahpResult.lambda_max.toFixed(4)} | CI ={" "}
                  {ahpResult.consistency_index.toFixed(4)} | CR ={" "}
                  {ahpResult.consistency_ratio.toFixed(4)}
                </span>
                <Badge variant={ahpResult.is_consistent ? "success" : "danger"}>
                  {ahpResult.is_consistent
                    ? "CONSISTENT (CR <= 0.10)"
                    : "REJECTED (CR > 0.10)"}
                </Badge>
              </div>
              <div className="font-mono text-[11px]">
                Eigenvector Weights:{" "}
                {Object.entries(ahpResult.weights)
                  .map(([k, v]) => `${k.replace("COMM_", "")}: ${Number(v).toFixed(3)}`)
                  .join(" | ")}
              </div>
            </div>
          )}
        </Card>

        {/* Patent Signals & Commercialization Pathway */}
        <Card className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900">
              EPO OPS / Manual Patent Signals & Pathway
            </h2>
            <div className="flex items-center gap-1.5">
              <input
                value={patentNumber}
                onChange={(e) => setPatentNumber(e.target.value)}
                className="w-36 rounded border border-slate-300 px-2 py-1 text-xs font-mono"
              />
              <Button size="sm" variant="outline" onClick={handlePatentLookup}>
                <Search className="h-3.5 w-3.5" /> Lookup
              </Button>
            </div>
          </div>

          <div className="rounded border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-900 flex items-start gap-2">
            <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5 text-amber-700" />
            <span>
              <strong>Harhoff et al. (2003) Contextual Rule:</strong> Patent citations,
              family size, and claim counts are treated strictly as contextual technology
              signals and are never converted into IDR monetary values. Non-patent
              technologies mark patent indicators <code>not_applicable</code> without
              penalty.
            </span>
          </div>

          {patentResult && (
            <div className="rounded border border-slate-200 bg-slate-50 p-3 text-xs space-y-1">
              <div className="font-bold text-slate-900">
                Source: {patentResult.source || "manual_or_disclosed"} • Patent:{" "}
                {patentResult.patent_number || patentNumber}
              </div>
              <pre className="whitespace-pre-wrap font-mono text-[11px] text-slate-700">
                {JSON.stringify(patentResult, null, 2)}
              </pre>
            </div>
          )}

          {revision?.commercialization_pathway_json && (
            <div className="border-t border-slate-200 pt-3 text-xs space-y-1.5">
              <div className="font-bold text-slate-900">
                Recommended Pathway:{" "}
                {revision.commercialization_pathway_json.recommended_pathway ||
                  "Non-Exclusive Industrial Licensing + Pilot Service"}
              </div>
              <p className="text-slate-600">
                {revision.commercialization_pathway_json.rationale ||
                  "Enables rapid adoption across regional fabricators while preserving core sol-gel coating IP."}
              </p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
