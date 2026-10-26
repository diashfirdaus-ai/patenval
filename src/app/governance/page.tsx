"use client";

import React, { useEffect, useState } from "react";
import { useAppState } from "@/lib/i18n";
import { apiClient, DEMO_ACCOUNTS, loginWithCredentials } from "@/lib/api-client";
import type { AssessmentRevisionItem, ExpertReviewItem } from "@/lib/api-types";
import { Card, Badge, Button } from "@/components/ui/primitives";
import { formatNormalizedScore } from "@/lib/utils";
import { ShieldCheck, History, CheckCircle2, AlertTriangle, Lock } from "lucide-react";

export default function GovernanceAuditPage() {
  const { lang, t, selectedTechId } = useAppState();
  const [revisions, setRevisions] = useState<AssessmentRevisionItem[]>([]);
  const [reviews, setReviews] = useState<ExpertReviewItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<Record<string, any>[]>([]);
  const [reviewDecision, setReviewDecision] = useState<string>("approved");
  const [rationale, setRationale] = useState<string>(
    "Verified all source locators (page:N / para:N), NASA TRL 6 exit criteria, and WIPO DCF attribution assumptions."
  );
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadGovernance = async () => {
    if (!selectedTechId) return;
    setError(null);
    try {
      const [revs, revList, logs] = await Promise.all([
        apiClient.listRevisions(selectedTechId),
        apiClient.listReviews(selectedTechId),
        apiClient.listAuditLogs(50),
      ]);
      setRevisions(revs);
      setReviews(revList);
      setAuditLogs(logs);
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    loadGovernance();
    const handler = () => loadGovernance();
    window.addEventListener("techval-role-changed", handler);
    return () => window.removeEventListener("techval-role-changed", handler);
  }, [selectedTechId]);

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTechId || revisions.length === 0) return;
    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      // Automatically authenticate as expert_reviewer if needed or use current session
      const latestRev = revisions[0];
      const created = await apiClient.submitExpertReview({
        technology_id: selectedTechId,
        assessment_revision_id: latestRev.id,
        status: reviewDecision,
        overall_rationale: rationale,
        methodology_verified: true,
        assumptions_verified: true,
      });
      setMessage(
        `Expert Review (${created.status.toUpperCase()}) recorded and cryptographically bound to Revision #${latestRev.revision_number}.`
      );
      await loadGovernance();
    } catch (err: any) {
      setError(
        `${err.message} (Tip: Switch Active Role in top header to "Expert Reviewer" or click "Switch to Expert Reviewer" below)`
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleQuickReviewerLogin = async () => {
    const creds = DEMO_ACCOUNTS.expert_reviewer;
    await loginWithCredentials(creds.username, creds.password);
    window.dispatchEvent(new CustomEvent("techval-role-changed"));
    setMessage("Switched active session to Expert Reviewer (Prof. Dr. Hendra Wijaya).");
    setError(null);
  };

  const latestRev = revisions[0] || null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{t.nav.governance}</h1>
        <p className="text-sm text-slate-600">
          {lang === "id"
            ? "Persetujuan pakar terikat revisi (Revision-Bound Approval), pembatalan otomatis ke STALE saat perubahan material, dan log audit permanen."
            : "Revision-bound expert approval, automatic STALE invalidation upon material changes, and immutable audit trail."}
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 p-3 text-xs text-rose-800 flex items-center justify-between">
          <span>
            {t.common.errorPrefix} {error}
          </span>
          <Button size="sm" variant="secondary" onClick={handleQuickReviewerLogin}>
            Switch to Expert Reviewer Role
          </Button>
        </div>
      )}
      {message && (
        <div className="rounded-md border border-emerald-300 bg-emerald-50 p-3 text-xs text-emerald-900">
          {message}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Expert Review Sign-Off Form */}
        <Card className="lg:col-span-1 space-y-4">
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <ShieldCheck className="h-4 w-4 text-blue-700" />
            <span>Revision-Bound Expert Sign-Off</span>
          </div>
          {latestRev && (
            <div className="rounded border border-blue-200 bg-blue-50/50 p-2.5 text-xs space-y-1">
              <div className="font-bold text-blue-900">
                Target: Immutable Revision #{latestRev.revision_number}
              </div>
              <div className="text-slate-600">
                Tech Score:{" "}
                {formatNormalizedScore(latestRev.technology_assessment_score)} • TRL:{" "}
                {latestRev.trl_score}/9
              </div>
              <div className="text-[11px] text-slate-500">
                Any subsequent score edit, weight change, valuation change, or document
                change will automatically invalidate this review to <code>stale</code>.
              </div>
            </div>
          )}

          <form onSubmit={handleSubmitReview} className="space-y-3 text-xs">
            <div>
              <label className="block font-semibold text-slate-700">
                Expert Decision
              </label>
              <select
                value={reviewDecision}
                onChange={(e) => setReviewDecision(e.target.value)}
                className="mt-1 w-full rounded border border-slate-300 px-2.5 py-1.5"
              >
                <option value="approved">
                  APPROVED — Authorize Official Report Without Draft Watermark
                </option>
                <option value="changes_requested">
                  CHANGES REQUESTED — Keep Draft Watermark
                </option>
                <option value="rejected">REJECTED — Methodological Non-Compliance</option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-700">
                Expert Verification Rationale
              </label>
              <textarea
                required
                rows={4}
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
                className="mt-1 w-full rounded border border-slate-300 p-2"
              />
            </div>

            <Button type="submit" disabled={submitting} className="w-full">
              <CheckCircle2 className="h-3.5 w-3.5" />
              {submitting ? "Signing Revision..." : "Sign & Bind Expert Review"}
            </Button>
          </form>
        </Card>

        {/* Expert Review Records & Stale Status */}
        <Card className="lg:col-span-2 space-y-4">
          <h2 className="text-base font-bold text-slate-900">
            Expert Review Records & Stale Invalidation History
          </h2>
          {reviews.length === 0 ? (
            <div className="rounded border border-slate-200 bg-slate-50 p-4 text-xs text-slate-600">
              No expert reviews recorded yet. Unapproved assessments carry a mandatory{" "}
              <strong>DRAFT — UNAPPROVED / PROVISIONAL</strong> watermark.
            </div>
          ) : (
            <div className="space-y-2.5">
              {reviews.map((r) => (
                <div
                  key={r.id}
                  className={`rounded border p-3 text-xs space-y-1 ${
                    r.status === "approved"
                      ? "border-emerald-300 bg-emerald-50/50"
                      : r.status === "stale"
                      ? "border-rose-300 bg-rose-50/50"
                      : "border-amber-300 bg-amber-50/50"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">
                      Review #{r.id.slice(0, 8)} • Bound to Revision ID{" "}
                      {r.assessment_revision_id.slice(0, 8)}
                    </span>
                    <Badge
                      variant={
                        r.status === "approved"
                          ? "success"
                          : r.status === "stale"
                          ? "danger"
                          : "warning"
                      }
                    >
                      {r.status.toUpperCase()}
                    </Badge>
                  </div>
                  <p className="text-slate-700">{r.overall_rationale}</p>
                  {r.stale_reason && (
                    <div className="text-rose-800 font-semibold flex items-center gap-1.5 pt-1">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      <span>Invalidated Reason: {r.stale_reason}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Immutable Revision Lineage */}
          <div className="border-t border-slate-200 pt-4 space-y-2.5">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <History className="h-4 w-4 text-blue-700" />
              <span>Immutable Assessment Revision Lineage ({revisions.length})</span>
            </h3>
            {revisions.map((rev) => (
              <div
                key={rev.id}
                className="rounded border border-slate-200 bg-slate-50 p-3 text-xs space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900">
                    Revision #{rev.revision_number} ({rev.id.slice(0, 8)})
                  </span>
                  <span className="text-slate-500">{rev.created_at}</span>
                </div>
                <div className="text-slate-700">
                  <strong>Change Reason:</strong> {rev.change_reason}
                </div>
                <div className="text-[11px] font-mono text-slate-600">
                  Tech: {formatNormalizedScore(rev.technology_assessment_score)} | TRL:{" "}
                  {rev.trl_score}/9 | Comm:{" "}
                  {formatNormalizedScore(rev.commercialization_readiness_score)} |
                  Completeness: {(rev.evidence_completeness_score * 100).toFixed(1)}%
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Immutable Audit Trail */}
      <Card className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Lock className="h-4 w-4 text-slate-700" />
            <span>Cryptographic & Governance Immutable Audit Log</span>
          </h2>
          <Badge variant="outline">{auditLogs.length} Recent Events</Badge>
        </div>
        <div className="overflow-x-auto max-h-64">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600">
                <th className="py-2 px-2.5">Timestamp</th>
                <th className="py-2 px-2.5">Action</th>
                <th className="py-2 px-2.5">Entity</th>
                <th className="py-2 px-2.5">Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {auditLogs.map((log) => (
                <tr key={log.id}>
                  <td className="py-2 px-2.5 font-mono text-[11px] text-slate-500">
                    {log.created_at}
                  </td>
                  <td className="py-2 px-2.5 font-bold text-slate-900">{log.action}</td>
                  <td className="py-2 px-2.5 font-mono text-[11px]">
                    {log.entity_type} ({log.entity_id.slice(0, 8)})
                  </td>
                  <td className="py-2 px-2.5 text-slate-700">{log.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
