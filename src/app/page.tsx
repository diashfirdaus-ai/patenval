"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useAppState } from "@/lib/i18n";
import { apiClient } from "@/lib/api-client";
import type { TechnologyItem } from "@/lib/api-types";
import { Card, Badge, Button, FourOutputsGrid } from "@/components/ui/primitives";
import { formatNormalizedScore } from "@/lib/utils";
import { PlusCircle, ArrowRight, FileCheck2, Sparkles, ShieldAlert } from "lucide-react";

export default function PortfolioOverviewPage() {
  const { lang, t, selectedTechId, setSelectedTechId } = useAppState();
  const [technologies, setTechnologies] = useState<TechnologyItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [showCreateForm, setShowCreateForm] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [newCode, setNewCode] = useState("ITENAS-PAT-2026-002");
  const [newTitleEn, setNewTitleEn] = useState("");
  const [newTitleId, setNewTitleId] = useState("");
  const [newDomain, setNewDomain] = useState("Environmental & Chemical Engineering");
  const [newDescEn, setNewDescEn] = useState("");
  const [newClaimedTrl, setNewClaimedTrl] = useState<number>(6);
  const [newPatentStatus, setNewPatentStatus] = useState("patent_pending");

  const loadPortfolio = async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await apiClient.listTechnologies();
      setTechnologies(items);
      if (items.length > 0 && !selectedTechId) {
        setSelectedTechId(items[0].id);
      }
    } catch (e: any) {
      setError(e.message || "Failed to load portfolio");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPortfolio();
  }, []);

  const handleCreateTech = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const created = await apiClient.createTechnology({
        code: newCode,
        title_en: newTitleEn,
        title_id: newTitleId || newTitleEn,
        domain: newDomain,
        inventor_organization: "ITENAS Bandung",
        description_en: newDescEn,
        description_id: newDescEn,
        claimed_trl: Number(newClaimedTrl),
        patent_status: newPatentStatus,
        is_synthetic_demo: false,
      });
      setShowCreateForm(false);
      setSelectedTechId(created.id);
      await loadPortfolio();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const activeTech =
    technologies.find((x) => x.id === selectedTechId) || technologies[0] || null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{t.nav.portfolio}</h1>
          <p className="text-sm text-slate-600">
            {lang === "id"
              ? "Pemantauan portofolio teknologi dengan pemisahan empat keluaran ilmiah dan finansial."
              : "Technology portfolio monitoring with strict four-output scientific and financial separation."}
          </p>
        </div>
        <Button onClick={() => setShowCreateForm(!showCreateForm)}>
          <PlusCircle className="h-4 w-4" />
          {lang === "id" ? "Daftarkan Teknologi Baru" : "Register New Technology"}
        </Button>
      </div>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 p-3 text-xs text-rose-800">
          {t.common.errorPrefix} {error}
        </div>
      )}

      {showCreateForm && (
        <Card className="border-blue-200 bg-blue-50/30">
          <h2 className="text-base font-bold text-slate-900 mb-3">
            {lang === "id"
              ? "Pendaftaran Pengungkapan Teknologi Baru"
              : "Register New Technology Disclosure"}
          </h2>
          <form onSubmit={handleCreateTech} className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold text-slate-700">
                Technology Code
              </label>
              <input
                required
                value={newCode}
                onChange={(e) => setNewCode(e.target.value)}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700">Domain</label>
              <input
                required
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700">
                Title (English)
              </label>
              <input
                required
                value={newTitleEn}
                onChange={(e) => setNewTitleEn(e.target.value)}
                placeholder="e.g., Hybrid Photocatalytic Wastewater Reactor"
                className="mt-1 w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700">
                Title (Bahasa Indonesia)
              </label>
              <input
                value={newTitleId}
                onChange={(e) => setNewTitleId(e.target.value)}
                placeholder="Opsional"
                className="mt-1 w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700">
                Claimed NASA TRL (1–9)
              </label>
              <input
                type="number"
                min={1}
                max={9}
                value={newClaimedTrl}
                onChange={(e) => setNewClaimedTrl(Number(e.target.value))}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700">
                Patent Status
              </label>
              <select
                value={newPatentStatus}
                onChange={(e) => setNewPatentStatus(e.target.value)}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
              >
                <option value="patent_pending">Patent Pending</option>
                <option value="granted">Granted Patent</option>
                <option value="invention_disclosure">Invention Disclosure (Unfiled)</option>
                <option value="non_patent_ip">Non-Patent Know-How / Software</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs font-semibold text-slate-700">
                Technical Summary
              </label>
              <textarea
                required
                rows={3}
                value={newDescEn}
                onChange={(e) => setNewDescEn(e.target.value)}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div className="md:col-span-2 flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowCreateForm(false)}
              >
                {t.common.cancel}
              </Button>
              <Button type="submit">Create Technology Record</Button>
            </div>
          </form>
        </Card>
      )}

      {activeTech && (
        <div className="space-y-4">
          <FourOutputsGrid
            outputs={activeTech.four_separate_outputs}
            isDemo={activeTech.is_synthetic_demo}
            expertStatus={activeTech.expert_review_status}
          />
        </div>
      )}

      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold text-slate-900">
            {lang === "id"
              ? "Daftar Portofolio Teknologi Terdaftar"
              : "Registered Technology Portfolio"}
          </h2>
          <span className="text-xs text-slate-500">
            {technologies.length} {lang === "id" ? "teknologi" : "technologies"}
          </span>
        </div>

        {loading ? (
          <div className="py-8 text-center text-sm text-slate-500">{t.common.loading}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 uppercase">
                  <th className="py-2.5 px-3">Code & Title</th>
                  <th className="py-2.5 px-3">1. Tech Assessment / TRL</th>
                  <th className="py-2.5 px-3">2. Comm. Readiness</th>
                  <th className="py-2.5 px-3">3. Economic Valuation (IDR)</th>
                  <th className="py-2.5 px-3">4. Completeness</th>
                  <th className="py-2.5 px-3">Governance</th>
                  <th className="py-2.5 px-3 text-right">Workflow</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {technologies.map((tech) => {
                  const fo = tech.four_separate_outputs;
                  const isSelected = tech.id === selectedTechId;
                  return (
                    <tr
                      key={tech.id}
                      onClick={() => setSelectedTechId(tech.id)}
                      className={`cursor-pointer transition ${
                        isSelected ? "bg-blue-50/60" : "hover:bg-slate-50"
                      }`}
                    >
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-1.5 font-bold text-slate-900">
                          <span>{tech.code}</span>
                          {tech.is_synthetic_demo && (
                            <Badge variant="warning">
                              <Sparkles className="h-3 w-3" /> Demo
                            </Badge>
                          )}
                        </div>
                        <div className="text-slate-700 font-medium mt-0.5">
                          {lang === "id" && tech.title_id ? tech.title_id : tech.title_en}
                        </div>
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          {tech.domain} • {tech.active_document_count} vaulted docs • Rev #
                          {tech.latest_revision_number}
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <div className="font-semibold text-slate-900">
                          {formatNormalizedScore(fo.technology_assessment.normalized_score)}
                        </div>
                        <div className="text-[11px] text-blue-700 font-medium">
                          NASA TRL: {fo.technology_assessment.trl_native_1_to_9 ?? "N/A"} / 9
                        </div>
                      </td>
                      <td className="py-3 px-3 font-semibold text-slate-900">
                        {formatNormalizedScore(
                          fo.commercialization_readiness.normalized_score
                        )}
                      </td>
                      <td className="py-3 px-3">
                        <div className="font-bold text-emerald-800">
                          {fo.economic_valuation.dcf_base_formatted}
                        </div>
                        <div className="text-[10px] text-slate-500">
                          WIPO Base DCF (No Score Conv.)
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <div className="font-semibold text-slate-900">
                          {(
                            fo.evidence_completeness.weighted_completeness_score * 100
                          ).toFixed(1)}
                          %
                        </div>
                        <div className="text-[11px] text-slate-500">
                          {fo.evidence_completeness.observed_count} obs /{" "}
                          {fo.evidence_completeness.missing_count} miss
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        {tech.expert_review_status === "approved" ? (
                          <Badge variant="success">Approved</Badge>
                        ) : tech.expert_review_status === "stale" ? (
                          <Badge variant="danger">STALE</Badge>
                        ) : (
                          <Badge variant="outline">Draft</Badge>
                        )}
                      </td>
                      <td className="py-3 px-3 text-right">
                        <div className="inline-flex items-center gap-1.5">
                          <Link
                            href="/assessment"
                            className="inline-flex items-center gap-1 rounded bg-blue-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-blue-700"
                          >
                            Inspect <ArrowRight className="h-3 w-3" />
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
