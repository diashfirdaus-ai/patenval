"use client";

import React, { useEffect, useState } from "react";
import { useAppState } from "@/lib/i18n";
import { apiClient } from "@/lib/api-client";
import type { AnalysisRunItem, DocumentItem } from "@/lib/api-types";
import { Card, Badge, Button } from "@/components/ui/primitives";
import {
  Play,
  RotateCcw,
  XCircle,
  ShieldCheck,
  CheckCircle2,
  Cpu,
  AlertTriangle,
} from "lucide-react";

export default function PipelineMonitorPage() {
  const { lang, t, selectedTechId } = useAppState();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [runs, setRuns] = useState<AnalysisRunItem[]>([]);
  const [selectedRun, setSelectedRun] = useState<AnalysisRunItem | null>(null);
  const [provider, setProvider] = useState<string>("meta_ai");
  const [modelName, setModelName] = useState<string>("muse-spark-1.3");
  const [apiKeyOverride, setApiKeyOverride] = useState<string>("");
  const [consentChecked, setConsentChecked] = useState<boolean>(true);
  const [syncExecution, setSyncExecution] = useState<boolean>(true);
  const [running, setRunning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    if (!selectedTechId) return;
    try {
      const [docs, runList] = await Promise.all([
        apiClient.listDocuments(selectedTechId, false),
        apiClient.listAnalysisRuns(selectedTechId),
      ]);
      setDocuments(docs);
      setRuns(runList);
      if (runList.length > 0) {
        const detail = await apiClient.getAnalysisRun(runList[0].id);
        setSelectedRun(detail);
      } else {
        setSelectedRun(null);
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedTechId]);

  const handleProviderChange = (nextProvider: string) => {
    setProvider(nextProvider);
    if (nextProvider === "meta_ai")
      setModelName("muse-spark-1.3");
    else if (nextProvider === "fixture")
      setModelName("fixture-deterministic-v1");
    else if (nextProvider === "ollama") setModelName("qwen2.5:7b-instruct");
    else if (nextProvider === "openai") setModelName("gpt-4o-2024-11-20");
    else if (nextProvider === "anthropic")
      setModelName("claude-3-5-sonnet-20241022");
  };

  const handleStartPipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTechId) return;
    setRunning(true);
    setError(null);
    try {
      const docIds = documents.map((d) => d.id);
      const scope =
        provider === "fixture"
          ? "local_fixture_only"
          : provider === "ollama"
          ? "local_ollama_inference"
          : `external_cloud_api_${provider}`;

      const consent = await apiClient.createConsent({
        technology_id: selectedTechId,
        provider,
        model_name: modelName,
        transmission_scope: scope,
        document_ids: docIds,
        consent_granted: consentChecked,
        config_options: { strict_evidence_verification: true },
      });

      const run = await apiClient.triggerAnalysisRun({
        technology_id: selectedTechId,
        consent_record_id: consent.id,
        provider,
        model_name: modelName,
        config_options: {
          strict_evidence_verification: true,
          api_key_override: apiKeyOverride.trim() || undefined,
        },
        execute_synchronously: syncExecution,
      });

      const detail = await apiClient.getAnalysisRun(run.id);
      setSelectedRun(detail);
      await loadData();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  };

  const handleRetry = async (runId: string) => {
    setRunning(true);
    setError(null);
    try {
      const retried = await apiClient.retryAnalysisRun(runId, true);
      const detail = await apiClient.getAnalysisRun(retried.id);
      setSelectedRun(detail);
      await loadData();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  };

  const handleCancel = async (runId: string) => {
    try {
      await apiClient.cancelAnalysisRun(runId);
      await loadData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const contradictions =
    selectedRun?.partial_results_json?.extraction?.contradictions_detected || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">{t.nav.pipeline}</h1>
        <p className="mt-1 text-base text-slate-600">
          {lang === "id"
            ? "AI akan membaca dokumen Anda dan menyiapkan penilaian. Cukup centang persetujuan lalu tekan tombol mulai."
            : "AI will read your documents and prepare the assessment. Just tick the consent box and press start."}
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 p-3 text-xs text-rose-800">
          {t.common.errorPrefix} {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Consent & Run Trigger */}
        <Card className="lg:col-span-1 space-y-4">
          <div className="flex items-center gap-2 text-lg font-semibold text-slate-900">
            <ShieldCheck className="h-5 w-5 text-blue-700" />
            <span>{lang === "id" ? "Mulai analisis" : "Start analysis"}</span>
          </div>
          <p className="text-sm text-slate-600">
            {lang === "id"
              ? `${documents.length} dokumen siap dianalisis.`
              : `${documents.length} document(s) ready to analyze.`}
          </p>

          <form onSubmit={handleStartPipeline} className="space-y-4 text-sm">
            <details className="rounded-xl border border-slate-200 bg-slate-50">
              <summary className="cursor-pointer list-none px-4 py-3 text-sm font-semibold text-slate-800">
                {lang === "id" ? "Pengaturan lanjutan ▾" : "Advanced settings ▾"}
              </summary>
              <div className="space-y-3 border-t border-slate-200 p-4">
            <div>
              <label className="block font-semibold text-slate-700">
                Execution Provider
              </label>
              <select
                value={provider}
                onChange={(e) => handleProviderChange(e.target.value)}
                className="mt-1 w-full rounded border border-slate-300 px-2.5 py-1.5"
              >
                <option value="meta_ai">
                  Meta AI — dev.meta.ai (api.meta.ai/v1 • Configured in .env.local)
                </option>
                <option value="fixture">
                  Deterministic Local Fixture (Explicit Demo/Testing Mode)
                </option>
                <option value="ollama">Local Ollama Server (Zero External API)</option>
                <option value="openai">OpenAI Cloud API (Requires API Key)</option>
                <option value="anthropic">Anthropic Cloud API (Requires API Key)</option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-700">Model Identifier</label>
              {provider === "meta_ai" ? (
                <select
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  className="mt-1 w-full rounded border border-slate-300 px-2.5 py-1.5 font-mono"
                >
                  <option value="muse-spark-1.3">muse-spark-1.3 (Meta Muse Spark 1.3 — Multi-Agent Orchestrator)</option>
                  <option value="muse-wonder-1.0">muse-wonder-1.0 (Meta Muse Wonder 1.0 — Scientific Reasoning)</option>
                  <option value="muse-code">muse-code (Meta Muse Code — Technical & Patent Claim Parser)</option>
                  <option value="muse-image">muse-image (Meta Muse Image — Diagram & Visual Inspector)</option>
                  <option value="sam-3.1">sam-3.1 (Meta SAM 3.1 — Document & Figure Segmentation)</option>
                  <option value="muse-spark-1.3-contributor">muse-spark-1.3-contributor</option>
                  <option value="muse-spark-1.2">muse-spark-1.2</option>
                  <option value="muse-spark-1.1">muse-spark-1.1</option>
                </select>
              ) : (
                <input
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  className="mt-1 w-full rounded border border-slate-300 px-2.5 py-1.5 font-mono"
                />
              )}
            </div>

            {provider !== "fixture" && provider !== "ollama" && (
              <div>
                <label className="block font-semibold text-slate-700">
                  API Key Override (Optional — Defaults to META_AI_API_KEY in .env.local)
                </label>
                <input
                  type="password"
                  value={apiKeyOverride}
                  onChange={(e) => setApiKeyOverride(e.target.value)}
                  placeholder="Leave blank to use META_AI_API_KEY from frontend/.env.local"
                  className="mt-1 w-full rounded border border-slate-300 px-2.5 py-1.5 font-mono"
                />
              </div>
            )}

            <div className="rounded-lg border border-slate-200 bg-white p-2.5 space-y-1">
              <div className="font-semibold text-slate-800">
                Document SHA-256 ({documents.length}):
              </div>
              {documents.map((d) => (
                <div key={d.id} className="truncate font-mono text-[11px] text-slate-600">
                  • {d.original_filename}: {d.sha256_hash.slice(0, 20)}...
                </div>
              ))}
            </div>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={syncExecution}
                onChange={(e) => setSyncExecution(e.target.checked)}
              />
              <span className="text-slate-700">
                {lang === "id" ? "Tunggu sampai selesai" : "Wait until finished"}
              </span>
            </label>
              </div>
            </details>

            <label className="flex items-start gap-3 cursor-pointer rounded-xl border border-slate-200 p-4">
              <input
                type="checkbox"
                checked={consentChecked}
                onChange={(e) => setConsentChecked(e.target.checked)}
                className="mt-1 h-4 w-4"
              />
              <span className="text-slate-700">
                {lang === "id"
                  ? "Saya setuju dokumen di atas diproses oleh AI. Jika layanan AI tidak tersedia, analisis akan berhenti dan tidak memakai data contoh."
                  : "I agree for the documents above to be processed by AI. If the AI service is unavailable, the analysis will stop instead of using sample data."}
              </span>
            </label>

            {documents.length === 0 && (
              <p className="text-sm text-amber-700">
                {lang === "id"
                  ? "Unggah dokumen terlebih dahulu di menu Unggah Dokumen."
                  : "Please upload a document first in Upload Documents."}
              </p>
            )}

            <Button
              type="submit"
              size="lg"
              disabled={!consentChecked || running || documents.length === 0}
              className="w-full"
            >
              <Play className="h-4 w-4" />
              {running
                ? lang === "id" ? "Sedang menganalisis..." : "Analyzing..."
                : lang === "id" ? "Mulai Analisis" : "Start Analysis"}
            </Button>
          </form>
        </Card>

        {/* Active Run Execution Monitor */}
        <Card className="lg:col-span-2 space-y-4">
          {selectedRun ? (
            <>
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <Cpu className="h-4 w-4 text-blue-700" />
                    <span className="font-bold text-sm text-slate-900">
                      Analysis Run #{selectedRun.id.slice(0, 8)}
                    </span>
                    <Badge
                      variant={
                        selectedRun.status === "completed"
                          ? "success"
                          : selectedRun.status === "failed"
                          ? "danger"
                          : "info"
                      }
                    >
                      {selectedRun.status.toUpperCase()} ({selectedRun.progress_percent}%)
                    </Badge>
                  </div>
                  <div className="text-[11px] font-mono text-slate-500 mt-1">
                    Requested: {selectedRun.requested_provider}/
                    {selectedRun.requested_model} → Returned:{" "}
                    {selectedRun.actual_provider_returned || "N/A"}/
                    {selectedRun.actual_model_returned || "N/A"}
                  </div>
                  <div className="text-[11px] font-mono text-slate-500">
                    Run Config Hash: {selectedRun.run_config_hash.slice(0, 24)}... • Prompt
                    Hash: {selectedRun.prompt_hash.slice(0, 24)}...
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleRetry(selectedRun.id)}
                  >
                    <RotateCcw className="h-3.5 w-3.5" /> Retry Run
                  </Button>
                  {selectedRun.status === "running" || selectedRun.status === "queued" ? (
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => handleCancel(selectedRun.id)}
                    >
                      <XCircle className="h-3.5 w-3.5" /> Cancel
                    </Button>
                  ) : null}
                </div>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-slate-200 h-2.5 rounded-full overflow-hidden">
                <div
                  className="bg-blue-600 h-full transition-all duration-300"
                  style={{ width: `${selectedRun.progress_percent}%` }}
                />
              </div>

              {selectedRun.error_message && (
                <div className="rounded border border-rose-300 bg-rose-50 p-3 text-xs text-rose-800">
                  <strong>Provider / Execution Failure:</strong>{" "}
                  {selectedRun.error_message}
                </div>
              )}

              {selectedRun.partial_results_json?.meta_ai_live_verification && (
                <div className="rounded-xl border border-emerald-300 bg-emerald-50 p-4 text-xs text-emerald-950 space-y-2.5">
                  <div className="flex flex-wrap items-center justify-between gap-2 font-bold">
                    <span className="text-sm text-emerald-950">
                      Meta AI Multi-Model Verification ({selectedRun.partial_results_json.meta_ai_live_verification.model})
                    </span>
                    <span className="font-mono text-[11px] text-emerald-800">
                      ID: {selectedRun.partial_results_json.meta_ai_live_verification.completion_id} • Tokens:{" "}
                      {selectedRun.partial_results_json.meta_ai_live_verification.usage?.total_tokens ?? "N/A"} • Docs:{" "}
                      {selectedRun.partial_results_json.meta_ai_live_verification.documents_analyzed ?? documents.length}
                    </span>
                  </div>
                  <div className="rounded-lg border border-emerald-200 bg-white/80 p-3 space-y-1">
                    <div className="text-[11px] font-bold uppercase tracking-wider text-blue-800">
                      Stage 1 — {selectedRun.partial_results_json.meta_ai_live_verification.stage1_model || "muse-spark-1.3"} (Evidence & Locator Extraction)
                    </div>
                    <p className="text-slate-800 leading-relaxed">
                      {selectedRun.partial_results_json.meta_ai_live_verification.content}
                    </p>
                  </div>
                  {selectedRun.partial_results_json.meta_ai_live_verification.stage2_synthesis && (
                    <div className="rounded-lg border border-indigo-200 bg-white/80 p-3 space-y-1">
                      <div className="text-[11px] font-bold uppercase tracking-wider text-indigo-800">
                        Stage 2 — {selectedRun.partial_results_json.meta_ai_live_verification.stage2_model || "muse-wonder-1.0"} (NASA TRL 1–9 & WIPO Commercialization Synthesis)
                      </div>
                      <p className="text-slate-800 leading-relaxed">
                        {selectedRun.partial_results_json.meta_ai_live_verification.stage2_synthesis}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {contradictions.length > 0 && (
                <div className="rounded border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900 space-y-1">
                  <div className="font-bold flex items-center gap-1.5">
                    <AlertTriangle className="h-4 w-4" /> Contradictory Evidence Detected
                    Across Document Sections:
                  </div>
                  {contradictions.map((c: any, idx: number) => (
                    <div key={idx}>• {c.description}</div>
                  ))}
                </div>
              )}

              {/* 8 Agent Nodes Trace */}
              <div className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  LangGraph 8-Node Checkpoint & Agent Execution Trace
                </h3>
                <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                  {selectedRun.agent_executions.map((ag, idx) => (
                    <div
                      key={ag.id}
                      className="rounded border border-slate-200 bg-slate-50 p-2.5 text-xs flex items-start justify-between"
                    >
                      <div>
                        <div className="font-bold text-slate-900 flex items-center gap-1.5">
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                          <span>
                            {idx + 1}. {ag.agent_name}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-500 font-mono mt-0.5">
                          {ag.provider_used}/{ag.model_used} • {ag.latency_ms} ms
                        </div>
                      </div>
                      <Badge variant="success">{ag.status}</Badge>
                    </div>
                  ))}
                </div>
              </div>

              {/* Rejected Claims Audit */}
              <div className="space-y-2 pt-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Source Location & Numeric Claim Verification Gate
                </h3>
                {selectedRun.rejected_claims_json.length === 0 ? (
                  <div className="rounded border border-emerald-200 bg-emerald-50/60 p-2.5 text-xs text-emerald-900">
                    All extracted evidence items resolved to exact document locators (
                    <code>page:N</code> / <code>para:N</code> / <code>table:N</code>) and
                    passed verbatim quote + numeric verification. Zero unsupported claims.
                  </div>
                ) : (
                  <div className="rounded border border-amber-300 bg-amber-50 p-2.5 text-xs text-amber-900 space-y-1">
                    <div className="font-bold">
                      Rejected Unsupported / Unresolved Claims (
                      {selectedRun.rejected_claims_json.length}):
                    </div>
                    {selectedRun.rejected_claims_json.map((rc, i) => (
                      <div key={i} className="font-mono text-[11px]">
                        • [{rc.indicator_code}] {rc.location_ref}: {rc.reason}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="py-8 text-center text-sm text-slate-500">
              No analysis runs found for this technology.
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
