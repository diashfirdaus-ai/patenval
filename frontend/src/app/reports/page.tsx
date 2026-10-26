"use client";

import React, { useEffect, useState } from "react";
import { useAppState } from "@/lib/i18n";
import { apiClient, getSavedSession } from "@/lib/api-client";
import type { ReportSnapshotItem } from "@/lib/api-types";
import { Card, Badge, Button } from "@/components/ui/primitives";
import { FileText, Download, ShieldCheck, Globe, Sparkles } from "lucide-react";

export default function BilingualReportsPage() {
  const { lang, t, selectedTechId } = useAppState();
  const [reports, setReports] = useState<ReportSnapshotItem[]>([]);
  const [generating, setGenerating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadReports = async () => {
    if (!selectedTechId) return;
    setError(null);
    try {
      const list = await apiClient.listReports(selectedTechId);
      setReports(list);
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    loadReports();
  }, [selectedTechId]);

  const handleGenerate = async (reportLang: "en" | "id") => {
    if (!selectedTechId) return;
    setGenerating(true);
    setError(null);
    try {
      await apiClient.generateReport({
        technology_id: selectedTechId,
        language: reportLang,
      });
      await loadReports();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleDownloadPdf = async (report: ReportSnapshotItem) => {
    try {
      const session = getSavedSession();
      const res = await fetch(apiClient.getReportDownloadUrl(report.id), {
        headers: session ? { Authorization: `Bearer ${session.access_token}` } : {},
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `TechVal_Report_${report.language.toUpperCase()}_${
        report.is_draft ? "DRAFT" : "APPROVED"
      }_${report.id.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{t.nav.reports}</h1>
          <p className="text-sm text-slate-600">
            {lang === "id"
              ? "Pembuatan Laporan PDF Dwibahasa (EN / ID) dengan pelestarian kutipan asli, watermark DRAF otomatis, dan manifes provenans SHA-256."
              : "Bilingual PDF Report Generation (EN / ID) retaining original source quotes and publication titles, automatic DRAFT watermark, and SHA-256 provenance manifest."}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={() => handleGenerate("en")}
            disabled={generating}
            variant="primary"
          >
            <Globe className="h-4 w-4" /> Generate English (EN) PDF
          </Button>
          <Button
            onClick={() => handleGenerate("id")}
            disabled={generating}
            variant="secondary"
          >
            <Globe className="h-4 w-4" /> Buat Laporan Bahasa Indonesia (ID) PDF
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 p-3 text-xs text-rose-800">
          {t.common.errorPrefix} {error}
        </div>
      )}

      <Card className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <FileText className="h-4 w-4 text-blue-700" />
            <span>Generated PDF Report Snapshots & Cryptographic Provenance</span>
          </h2>
          <Badge variant="info">{reports.length} Snapshots</Badge>
        </div>

        {reports.length === 0 ? (
          <div className="py-8 text-center text-sm text-slate-500">
            Click &ldquo;Generate English (EN) PDF&rdquo; or &ldquo;Buat Laporan Bahasa
            Indonesia (ID) PDF&rdquo; above to compile a complete multi-page report.
          </div>
        ) : (
          <div className="space-y-4">
            {reports.map((rep) => (
              <div
                key={rep.id}
                className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="info">{rep.language.toUpperCase()}</Badge>
                    {rep.is_draft ? (
                      <Badge variant="warning">{rep.watermark_text}</Badge>
                    ) : (
                      <Badge variant="success">
                        <ShieldCheck className="h-3 w-3" /> {rep.watermark_text}
                      </Badge>
                    )}
                    <span className="text-xs font-mono text-slate-500">
                      Revision ID: {rep.assessment_revision_id.slice(0, 8)} • Created:{" "}
                      {rep.created_at}
                    </span>
                  </div>
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={() => handleDownloadPdf(rep)}
                  >
                    <Download className="h-3.5 w-3.5" /> Download PDF
                  </Button>
                </div>

                <div className="grid grid-cols-1 gap-2 md:grid-cols-2 text-xs font-mono bg-white p-3 rounded border border-slate-200">
                  <div>
                    <strong>PDF SHA-256:</strong> {rep.file_sha256}
                  </div>
                  <div>
                    <strong>Provider / Model:</strong>{" "}
                    {rep.provenance_json.requested_provider}/
                    {rep.provenance_json.requested_model} &rarr;{" "}
                    {rep.provenance_json.actual_provider_returned}/
                    {rep.provenance_json.actual_model_returned}
                  </div>
                  <div>
                    <strong>Prompt Hash:</strong> {rep.provenance_json.prompt_hash}
                  </div>
                  <div>
                    <strong>Run Config Hash:</strong>{" "}
                    {rep.provenance_json.run_config_hash}
                  </div>
                  <div>
                    <strong>Rubric / Weight Version:</strong>{" "}
                    {rep.provenance_json.rubric_version_tag} /{" "}
                    {rep.provenance_json.weight_set_version}
                  </div>
                  <div>
                    <strong>App Version:</strong> {rep.provenance_json.app_version}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
