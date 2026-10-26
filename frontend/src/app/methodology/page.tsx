"use client";

import React, { useEffect, useState } from "react";
import { useAppState } from "@/lib/i18n";
import { apiClient } from "@/lib/api-client";
import type { IndicatorDefinitionItem, ScientificReferenceItem } from "@/lib/api-types";
import { Card, Badge } from "@/components/ui/primitives";
import { BookOpen, CheckCircle2, AlertTriangle, ExternalLink } from "lucide-react";

export default function ScientificMethodologyPage() {
  const { lang, t } = useAppState();
  const [references, setReferences] = useState<ScientificReferenceItem[]>([]);
  const [indicators, setIndicators] = useState<IndicatorDefinitionItem[]>([]);
  const [specs, setSpecs] = useState<Record<string, any> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      apiClient.listReferences(),
      apiClient.listIndicators(),
      apiClient.getMethodologySpecs(),
    ])
      .then(([refs, inds, sp]) => {
        setReferences(refs);
        setIndicators(inds);
        setSpecs(sp);
      })
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{t.nav.methodology}</h1>
        <p className="text-sm text-slate-600">
          {lang === "id"
            ? "Spesifikasi matematika formal, klasifikasi asal indikator, dan registri verifikasi literatur ilmiah."
            : "Formal mathematical specifications, indicator origin classifications, and scientific literature verification registry."}
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 p-3 text-xs text-rose-800">
          {t.common.errorPrefix} {error}
        </div>
      )}

      {/* Mathematical Specifications */}
      {specs && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Card className="space-y-2">
            <h2 className="text-sm font-bold text-slate-900">
              1. Score Normalization & Native TRL Scale
            </h2>
            <p className="text-xs font-mono bg-slate-50 p-2 rounded border">
              {specs.normalization?.ordinal_1_to_5}
            </p>
            <p className="text-xs text-slate-600">{specs.normalization?.trl_1_to_9}</p>
          </Card>

          <Card className="space-y-2">
            <h2 className="text-sm font-bold text-slate-900">
              2. Missing / N-A Weight Renormalization & Completeness
            </h2>
            <p className="text-xs font-mono bg-slate-50 p-2 rounded border">
              {specs.missing_data_renormalization?.renormalized_weight_formula}
            </p>
            <p className="text-xs font-mono bg-slate-50 p-2 rounded border">
              {specs.missing_data_renormalization?.completeness_formula}
            </p>
          </Card>

          <Card className="space-y-2">
            <h2 className="text-sm font-bold text-slate-900">
              3. Saaty AHP Weight Calibration (CR &le; 0.10)
            </h2>
            <p className="text-xs font-mono bg-slate-50 p-2 rounded border">
              {specs.ahp_consistency?.consistency_index_formula} |{" "}
              {specs.ahp_consistency?.consistency_ratio_formula}
            </p>
            <p className="text-xs text-slate-600">
              Reciprocal rule: {specs.ahp_consistency?.reciprocal_rule}
            </p>
          </Card>

          <Card className="space-y-2">
            <h2 className="text-sm font-bold text-slate-900">
              4. WIPO Economic Valuation Formulas (IDR)
            </h2>
            <p className="text-xs font-mono bg-slate-50 p-2 rounded border">
              {specs.economic_valuation_wipo?.dcf_npv}
            </p>
            <p className="text-xs font-mono bg-slate-50 p-2 rounded border">
              {specs.economic_valuation_wipo?.relief_from_royalty}
            </p>
          </Card>
        </div>
      )}

      {/* Scientific Reference Verification Registry */}
      <Card className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-blue-700" />
            <span>
              Scientific Reference Registry & Methodology Verification Status
            </span>
          </h2>
          <Badge variant="info">{references.length} Registered Sources</Badge>
        </div>
        <p className="text-xs text-slate-600">
          Only sources marked <code>methodology_verified</code> with explicit verified
          sections/pages are used to justify scoring rules or formulas. Sources where
          only bibliographic metadata is available are labeled{" "}
          <code>bibliographically_verified_only</code>.
        </p>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 uppercase">
                <th className="py-2.5 px-3">Code & Citation</th>
                <th className="py-2.5 px-3">Verification Status</th>
                <th className="py-2.5 px-3">Verified Sections / Pages</th>
                <th className="py-2.5 px-3">Cross-Domain & Methodology Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {references.map((ref) => (
                <tr key={ref.id}>
                  <td className="py-3 px-3">
                    <div className="font-bold text-slate-900">
                      [{ref.code}] {ref.authors} ({ref.publication_year})
                    </div>
                    <div className="text-slate-700 italic">{ref.title}</div>
                    <div className="text-[11px] text-slate-500">
                      {ref.venue_or_publisher} •{" "}
                      <a
                        href={ref.doi_or_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-blue-700 underline inline-flex items-center gap-0.5"
                      >
                        Source Link <ExternalLink className="h-2.5 w-2.5" />
                      </a>
                    </div>
                  </td>
                  <td className="py-3 px-3">
                    {ref.methodology_verification_status === "methodology_verified" ? (
                      <Badge variant="success">
                        <CheckCircle2 className="h-3 w-3" /> methodology_verified
                      </Badge>
                    ) : (
                      <Badge variant="warning">
                        <AlertTriangle className="h-3 w-3" />{" "}
                        bibliographically_verified_only
                      </Badge>
                    )}
                  </td>
                  <td className="py-3 px-3 font-mono text-[11px] text-slate-700">
                    {ref.verified_sections_pages || "Metadata Only (No Formula Claimed)"}
                  </td>
                  <td className="py-3 px-3 text-slate-600 max-w-md">
                    <div>{ref.summary_quote}</div>
                    {ref.cross_domain_adaptation_notes && (
                      <div className="mt-1 text-[11px] text-amber-800">
                        <strong>Adaptation:</strong> {ref.cross_domain_adaptation_notes}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Indicator Origin Classification Matrix */}
      <Card className="space-y-4">
        <h2 className="text-base font-bold text-slate-900">
          Indicator Origin Classification & Source Mapping Matrix
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 uppercase">
                <th className="py-2 px-3">Indicator Code</th>
                <th className="py-2 px-3">Dimension</th>
                <th className="py-2 px-3">Scale</th>
                <th className="py-2 px-3">Origin Classification</th>
                <th className="py-2 px-3">Source Section / Page Locator</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {indicators.map((ind) => (
                <tr key={ind.id}>
                  <td className="py-2.5 px-3 font-bold text-slate-900">
                    {ind.code}
                    <div className="font-normal text-slate-600">
                      {lang === "id" ? ind.name_id : ind.name_en}
                    </div>
                  </td>
                  <td className="py-2.5 px-3">{ind.dimension}</td>
                  <td className="py-2.5 px-3 font-mono">{ind.scale_type}</td>
                  <td className="py-2.5 px-3">
                    <Badge
                      variant={
                        ind.origin_classification === "directly_sourced"
                          ? "success"
                          : ind.origin_classification === "adapted"
                          ? "info"
                          : "warning"
                      }
                    >
                      {ind.origin_classification}
                    </Badge>
                  </td>
                  <td className="py-2.5 px-3 font-mono text-[11px] text-slate-700">
                    {ind.source_locator || "Proposed — Requires Expert Calibration"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
