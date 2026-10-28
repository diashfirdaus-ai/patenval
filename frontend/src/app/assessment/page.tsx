"use client";

import React, { useEffect, useState } from "react";
import { useAppState } from "@/lib/i18n";
import { apiClient } from "@/lib/api-client";
import type {
  AssessmentRevisionItem,
  IndicatorDefinitionItem,
  IndicatorScoreItem,
} from "@/lib/api-types";
import { Card, Badge, Button } from "@/components/ui/primitives";
import { formatNormalizedScore } from "@/lib/utils";
import { Microscope, BookOpenCheck, Save, CheckCircle2, FileSearch } from "lucide-react";

export default function TechAssessmentPage() {
  const { lang, t, selectedTechId } = useAppState();
  const [revision, setRevision] = useState<AssessmentRevisionItem | null>(null);
  const [definitions, setDefinitions] = useState<IndicatorDefinitionItem[]>([]);
  const [editedScores, setEditedScores] = useState<Record<string, IndicatorScoreItem>>({});
  const [selectedIndicator, setSelectedIndicator] = useState<string>("TECH_TRL_NATIVE");
  const [changeReason, setChangeReason] = useState<string>(
    "Analyst updated indicator assessment and verified evidence locators."
  );
  const [saving, setSaving] = useState<boolean>(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadAssessment = async () => {
    if (!selectedTechId) return;
    setError(null);
    try {
      const [rev, defs] = await Promise.all([
        apiClient.getLatestRevision(selectedTechId),
        apiClient.listIndicators(),
      ]);
      setRevision(rev);
      setDefinitions(defs);
      const map: Record<string, IndicatorScoreItem> = {};
      rev.indicator_scores.forEach((s) => {
        map[s.indicator_code] = { ...s };
      });
      setEditedScores(map);
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    loadAssessment();
  }, [selectedTechId]);

  const handleScoreFieldChange = (
    code: string,
    field: keyof IndicatorScoreItem,
    value: any
  ) => {
    setEditedScores((prev) => ({
      ...prev,
      [code]: {
        ...prev[code],
        [field]: value,
      },
    }));
  };

  const handleSaveNewRevision = async () => {
    if (!selectedTechId || !revision) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const updates = Object.values(editedScores).map((s) => ({
        indicator_code: s.indicator_code,
        status: s.status,
        raw_score: s.status === "observed" ? Number(s.raw_score) : null,
        rationale_en: s.rationale_en,
        rationale_id: s.rationale_id,
      }));
      const newRev = await apiClient.createNewRevision(selectedTechId, {
        change_reason: changeReason,
        weight_set_id: revision.weight_set_id,
        indicator_updates: updates,
      });
      setRevision(newRev);
      setMessage(
        `Created immutable Revision #${newRev.revision_number}. Any prior expert approval was automatically marked STALE.`
      );
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const techIndicators =
    revision?.indicator_scores.filter((s) => s.dimension === "technology_assessment") ||
    [];
  const activeDef = definitions.find((d) => d.code === selectedIndicator);
  const activeEvidence =
    revision?.evidence_items.filter((e) => e.indicator_code === selectedIndicator) || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">{t.nav.assessment}</h1>
          <p className="mt-1 text-base text-slate-600">
            {lang === "id"
              ? "Lihat skor kesiapan teknologi (NASA TRL 1–9), indikator teknis, dan kutipan bukti langsung dari dokumen Anda."
              : "Review your technology readiness level (NASA TRL 1–9), technical indicators, and direct evidence quotes from your documents."}
          </p>
        </div>
        {revision && (
          <div className="flex items-center gap-2">
            <Badge variant="info">
              {lang === "id" ? `Revisi #${revision.revision_number}` : `Revision #${revision.revision_number}`}
            </Badge>
            {revision.is_provisional && (
              <Badge variant="warning">{t.fourOutputs.provisionalBadge}</Badge>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 p-3 text-xs text-rose-800">
          {t.common.errorPrefix} {error}
        </div>
      )}
      {message && (
        <div className="rounded-md border border-emerald-300 bg-emerald-50 p-3 text-xs text-emerald-900">
          {message}
        </div>
      )}

      {revision && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Card className="border-l-4 border-l-blue-600">
            <div className="text-xs font-semibold uppercase text-slate-500">
              Composite Technology Assessment Score
            </div>
            <div className="mt-1 text-2xl font-bold text-slate-900">
              {formatNormalizedScore(revision.technology_assessment_score)}
            </div>
            <div className="mt-1 text-xs text-slate-500">
              Normalized [0, 1] from 1–5 ordinal indicators (excluding native TRL)
            </div>
          </Card>

          <Card className="border-l-4 border-l-indigo-600">
            <div className="text-xs font-semibold uppercase text-slate-500">
              NASA TRL (1–9 Native Scale)
            </div>
            <div className="mt-1 text-2xl font-bold text-indigo-700">
              TRL {revision.trl_score ?? "Unavailable"} / 9
            </div>
            <div className="mt-1 text-xs text-slate-500">
              Grounded in NASA ESTO / ISO 16290:2013 exit criteria
            </div>
          </Card>

          <Card className="border-l-4 border-l-amber-600">
            <div className="text-xs font-semibold uppercase text-slate-500">
              Dimension Evidence Completeness
            </div>
            <div className="mt-1 text-2xl font-bold text-slate-900">
              {(revision.tech_completeness_score * 100).toFixed(1)}%
            </div>
            <div className="mt-1 text-xs text-slate-500">
              Weighted observed coverage across applicable indicators
            </div>
          </Card>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Indicator Table & Revision Editor */}
        <Card className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Microscope className="h-4 w-4 text-blue-700" />
              <span>Technology Assessment Indicators & Renormalized Weights</span>
            </h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 uppercase">
                  <th className="py-2 px-2.5">Indicator</th>
                  <th className="py-2 px-2.5">Status</th>
                  <th className="py-2 px-2.5">Raw Score</th>
                  <th className="py-2 px-2.5">Normalized</th>
                  <th className="py-2 px-2.5">Base / Renorm Weight</th>
                  <th className="py-2 px-2.5">Evidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {techIndicators.map((ind) => {
                  const def = definitions.find((d) => d.code === ind.indicator_code);
                  const editState = editedScores[ind.indicator_code] || ind;
                  const isSelected = selectedIndicator === ind.indicator_code;
                  return (
                    <tr
                      key={ind.id}
                      onClick={() => setSelectedIndicator(ind.indicator_code)}
                      className={`cursor-pointer ${
                        isSelected ? "bg-blue-50/70" : "hover:bg-slate-50"
                      }`}
                    >
                      <td className="py-2.5 px-2.5">
                        <div className="font-bold text-slate-900">
                          {ind.indicator_code}
                        </div>
                        <div className="text-slate-600">
                          {lang === "id" && def ? def.name_id : def?.name_en}
                        </div>
                        {def && (
                          <Badge variant="outline" className="mt-1 text-[10px]">
                            Origin: {def.origin_classification}
                          </Badge>
                        )}
                      </td>
                      <td className="py-2.5 px-2.5">
                        <select
                          value={editState.status}
                          onChange={(e) =>
                            handleScoreFieldChange(
                              ind.indicator_code,
                              "status",
                              e.target.value
                            )
                          }
                          className="rounded border border-slate-300 px-2 py-1 text-xs"
                        >
                          <option value="observed">observed</option>
                          <option value="missing">missing</option>
                          <option value="not_applicable">not_applicable</option>
                        </select>
                      </td>
                      <td className="py-2.5 px-2.5">
                        {editState.status === "observed" ? (
                          <input
                            type="number"
                            min={ind.scale_type === "1-9_trl" ? 1 : 1}
                            max={ind.scale_type === "1-9_trl" ? 9 : 5}
                            step={ind.scale_type === "1-9_trl" ? 1 : 0.5}
                            value={editState.raw_score ?? 3}
                            onChange={(e) =>
                              handleScoreFieldChange(
                                ind.indicator_code,
                                "raw_score",
                                Number(e.target.value)
                              )
                            }
                            className="w-16 rounded border border-slate-300 px-2 py-1 font-bold text-slate-900"
                          />
                        ) : (
                          <span className="text-slate-400 italic">Excluded</span>
                        )}
                        <span className="ml-1 text-[10px] text-slate-500">
                          ({ind.scale_type})
                        </span>
                      </td>
                      <td className="py-2.5 px-2.5 font-mono">
                        {ind.scale_type === "1-9_trl"
                          ? `TRL ${ind.raw_score ?? "-"} / 9`
                          : ind.normalized_score !== null
                          ? ind.normalized_score.toFixed(4)
                          : "—"}
                      </td>
                      <td className="py-2.5 px-2.5 font-mono text-[11px]">
                        {ind.base_weight.toFixed(3)} →{" "}
                        <strong className="text-blue-700">
                          {ind.renormalized_weight.toFixed(3)}
                        </strong>
                      </td>
                      <td className="py-2.5 px-2.5">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setSelectedIndicator(ind.indicator_code)}
                        >
                          <FileSearch className="h-3.5 w-3.5" /> View Quote
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="border-t border-slate-200 pt-3 flex flex-wrap items-center justify-between gap-3">
            <input
              value={changeReason}
              onChange={(e) => setChangeReason(e.target.value)}
              placeholder="Mandatory change reason for new immutable revision..."
              className="flex-1 rounded border border-slate-300 px-3 py-1.5 text-xs"
            />
            <Button onClick={handleSaveNewRevision} disabled={saving}>
              <Save className="h-3.5 w-3.5" />
              {saving ? "Creating Revision..." : t.common.save}
            </Button>
          </div>
        </Card>

        {/* Side-by-side Evidence & Rubric Viewer */}
        <Card className="lg:col-span-1 space-y-4">
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <BookOpenCheck className="h-4 w-4 text-blue-700" />
            <span>Evidence & Rubric Viewer: {selectedIndicator}</span>
          </div>

          {activeDef && (
            <div className="rounded border border-slate-200 bg-slate-50 p-3 text-xs space-y-1.5">
              <div className="font-bold text-slate-900">
                {lang === "id" ? activeDef.name_id : activeDef.name_en}
              </div>
              <p className="text-slate-600">
                {lang === "id" ? activeDef.description_id : activeDef.description_en}
              </p>
              <div className="text-[11px] text-slate-500">
                Source Locator: <strong>{activeDef.source_locator || "Proposed"}</strong>
              </div>
              {activeDef.cross_domain_note && (
                <div className="text-[11px] text-amber-800 bg-amber-50 p-1.5 rounded border border-amber-200">
                  Cross-Domain Note: {activeDef.cross_domain_note}
                </div>
              )}
            </div>
          )}

          <div className="space-y-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Verified Source Locators & Verbatim Quotes (Original Language)
            </h3>
            {activeEvidence.length === 0 ? (
              <div className="rounded border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
                No resolved evidence quotes linked to this indicator.
              </div>
            ) : (
              activeEvidence.map((ev) => (
                <div
                  key={ev.id}
                  className="rounded border border-blue-200 bg-blue-50/40 p-3 text-xs space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-blue-800">
                      Locator: [{ev.location_ref}]
                    </span>
                    <Badge variant="success">
                      <CheckCircle2 className="h-3 w-3" /> {ev.resolution_status}
                    </Badge>
                  </div>
                  <blockquote className="border-l-2 border-blue-600 pl-2.5 italic text-slate-800">
                    “{ev.quoted_text}”
                  </blockquote>
                  <div className="text-[11px] text-slate-600">{ev.claim_summary}</div>
                </div>
              ))
            )}
          </div>

          {revision && revision.trl_exit_criteria_met_json.length > 0 && (
            <div className="border-t border-slate-200 pt-3 space-y-1.5">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                NASA TRL {revision.trl_score} Exit Criteria Verified
              </h3>
              {revision.trl_exit_criteria_met_json.map((crit, i) => (
                <div key={i} className="text-xs text-slate-700 flex items-start gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0 mt-0.5" />
                  <span>{crit}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
