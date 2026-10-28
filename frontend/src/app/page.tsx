"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useAppState } from "@/lib/i18n";
import { apiClient } from "@/lib/api-client";
import type { TechnologyItem } from "@/lib/api-types";
import {
  Card,
  Badge,
  Button,
  FourOutputsGrid,
  EmptyState,
  Collapsible,
} from "@/components/ui/primitives";
import { PlusCircle, ArrowRight, FileUp, Cpu, FileText } from "lucide-react";

const inputClass =
  "mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-200";
const labelClass = "block text-sm font-medium text-slate-800";

export default function PortfolioOverviewPage() {
  const { lang, t, selectedTechId, setSelectedTechId } = useAppState();
  const id = lang === "id";
  const [technologies, setTechnologies] = useState<TechnologyItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [showCreateForm, setShowCreateForm] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

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
    setSuccess(null);
    setSaving(true);
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
      setSuccess(
        id
          ? "Teknologi berhasil ditambahkan. Langkah berikutnya: unggah dokumen."
          : "Technology added. Next step: upload your documents."
      );
      setNewTitleEn("");
      setNewTitleId("");
      setNewDescEn("");
      await loadPortfolio();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const activeTech =
    technologies.find((x) => x.id === selectedTechId) || technologies[0] || null;
  const titleOf = (tech: TechnologyItem) =>
    id && tech.title_id ? tech.title_id : tech.title_en;

  const steps = [
    {
      href: "/submission",
      icon: FileUp,
      title: id ? "1. Unggah dokumen" : "1. Upload documents",
      desc: id ? "Tambahkan dokumen teknis atau paten." : "Add your technical or patent files.",
    },
    {
      href: "/pipeline",
      icon: Cpu,
      title: id ? "2. Jalankan analisis" : "2. Run the analysis",
      desc: id ? "AI membaca dan menilai dokumen Anda." : "AI reads and scores your documents.",
    },
    {
      href: "/reports",
      icon: FileText,
      title: id ? "3. Unduh laporan" : "3. Get your report",
      desc: id ? "Simpan hasil sebagai laporan PDF." : "Save the results as a PDF report.",
    },
  ];

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">
            {id ? "Selamat datang" : "Welcome"}
          </h1>
          <p className="mt-1 text-base text-slate-600">
            {id
              ? "Lihat ringkasan penilaian teknologi Anda dalam sekali pandang."
              : "See a quick summary of your technology assessment."}
          </p>
        </div>
        <Button size="lg" onClick={() => setShowCreateForm(!showCreateForm)}>
          <PlusCircle className="h-5 w-5" />
          {id ? "Tambah Teknologi" : "Add Technology"}
        </Button>
      </div>

      {error && (
        <div role="alert" className="rounded-xl border border-rose-300 bg-rose-50 p-4 text-sm text-rose-800">
          {t.common.errorPrefix} {error}
        </div>
      )}
      {success && (
        <div role="status" className="rounded-xl border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-800">
          {success}
        </div>
      )}

      {showCreateForm && (
        <Card>
          <h2 className="mb-1 text-xl font-semibold text-slate-900">
            {id ? "Tambah teknologi baru" : "Add a new technology"}
          </h2>
          <p className="mb-5 text-sm text-slate-600">
            {id ? "Isi informasi dasar saja. Anda bisa melengkapinya nanti." : "Just the basics. You can fill in the rest later."}
          </p>
          <form onSubmit={handleCreateTech} className="space-y-5">
            <div>
              <label className={labelClass} htmlFor="title-en">
                {id ? "Nama teknologi" : "Technology name"}
              </label>
              <input
                id="title-en"
                required
                value={newTitleEn}
                onChange={(e) => setNewTitleEn(e.target.value)}
                placeholder="e.g., Hybrid Photocatalytic Wastewater Reactor"
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass} htmlFor="desc">
                {id ? "Deskripsi singkat" : "Short description"}
              </label>
              <textarea
                id="desc"
                required
                rows={3}
                value={newDescEn}
                onChange={(e) => setNewDescEn(e.target.value)}
                placeholder={id ? "Apa yang dilakukan teknologi ini?" : "What does this technology do?"}
                className={inputClass}
              />
            </div>
            <Collapsible title={t.common.advanced}>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <label className={labelClass} htmlFor="code">{id ? "Kode teknologi" : "Technology code"}</label>
                  <input id="code" required value={newCode} onChange={(e) => setNewCode(e.target.value)} className={inputClass} />
                </div>
                <div>
                  <label className={labelClass} htmlFor="domain">{id ? "Bidang" : "Field"}</label>
                  <input id="domain" required value={newDomain} onChange={(e) => setNewDomain(e.target.value)} className={inputClass} />
                </div>
                <div>
                  <label className={labelClass} htmlFor="title-id">{id ? "Nama (Bahasa Indonesia)" : "Name (Bahasa Indonesia)"}</label>
                  <input id="title-id" value={newTitleId} onChange={(e) => setNewTitleId(e.target.value)} placeholder={id ? "Opsional" : "Optional"} className={inputClass} />
                </div>
                <div>
                  <label className={labelClass} htmlFor="trl">{id ? "Tingkat kesiapan (TRL 1–9)" : "Readiness level (TRL 1–9)"}</label>
                  <input id="trl" type="number" min={1} max={9} value={newClaimedTrl} onChange={(e) => setNewClaimedTrl(Number(e.target.value))} className={inputClass} />
                </div>
                <div className="md:col-span-2">
                  <label className={labelClass} htmlFor="patent">{id ? "Status paten" : "Patent status"}</label>
                  <select id="patent" value={newPatentStatus} onChange={(e) => setNewPatentStatus(e.target.value)} className={inputClass}>
                    <option value="patent_pending">{id ? "Dalam proses paten" : "Patent pending"}</option>
                    <option value="granted">{id ? "Paten diberikan" : "Granted patent"}</option>
                    <option value="invention_disclosure">{id ? "Belum didaftarkan" : "Not filed yet"}</option>
                    <option value="non_patent_ip">{id ? "Know-how / Perangkat lunak" : "Know-how / Software"}</option>
                  </select>
                </div>
              </div>
            </Collapsible>
            <div className="flex flex-wrap justify-end gap-3">
              <Button type="button" variant="outline" onClick={() => setShowCreateForm(false)}>
                {t.common.cancel}
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? (id ? "Menyimpan..." : "Saving...") : id ? "Simpan Teknologi" : "Save Technology"}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {loading ? (
        <div className="py-12 text-center text-base text-slate-500">{t.common.loading}</div>
      ) : technologies.length === 0 ? (
        <EmptyState
          title={id ? "Belum ada teknologi" : "No technologies yet"}
          description={
            id
              ? "Mulai dengan menambahkan teknologi pertama Anda."
              : "Start by adding your first technology."
          }
          action={
            <Button onClick={() => setShowCreateForm(true)}>
              <PlusCircle className="h-5 w-5" />
              {id ? "Tambah Teknologi" : "Add Technology"}
            </Button>
          }
        />
      ) : (
        <>
          {activeTech && (
            <section className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-xl font-semibold text-slate-900">{titleOf(activeTech)}</h2>
                <Link
                  href="/assessment"
                  className="inline-flex items-center gap-1 text-sm font-semibold text-blue-700 hover:underline"
                >
                  {id ? "Lihat detail" : "View details"} <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
              <FourOutputsGrid
                outputs={activeTech.four_separate_outputs}
                isDemo={activeTech.is_synthetic_demo}
                expertStatus={activeTech.expert_review_status}
              />
            </section>
          )}

          <section className="space-y-3">
            <h2 className="text-xl font-semibold text-slate-900">
              {id ? "Langkah berikutnya" : "What to do next"}
            </h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              {steps.map((s) => {
                const Icon = s.icon;
                return (
                  <Link
                    key={s.href}
                    href={s.href}
                    className="group rounded-2xl border border-slate-200 bg-white p-5 transition hover:border-blue-300 hover:shadow-md"
                  >
                    <Icon className="h-6 w-6 text-blue-600" />
                    <div className="mt-3 text-base font-semibold text-slate-900">{s.title}</div>
                    <p className="mt-1 text-sm text-slate-600">{s.desc}</p>
                  </Link>
                );
              })}
            </div>
          </section>

          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-slate-900">
                {id ? "Semua teknologi" : "All technologies"}
              </h2>
              <span className="text-sm text-slate-500">
                {technologies.length} {id ? "teknologi" : "technologies"}
              </span>
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {technologies.map((tech) => {
                const isSelected = tech.id === (activeTech?.id ?? null);
                const fo = tech.four_separate_outputs;
                return (
                  <button
                    key={tech.id}
                    type="button"
                    onClick={() => setSelectedTechId(tech.id)}
                    aria-pressed={isSelected}
                    className={`rounded-2xl border p-5 text-left transition ${
                      isSelected
                        ? "border-blue-500 bg-blue-50/60 ring-2 ring-blue-100"
                        : "border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="truncate text-base font-semibold text-slate-900">{titleOf(tech)}</div>
                        <div className="mt-0.5 text-sm text-slate-500">{tech.domain}</div>
                      </div>
                      {tech.expert_review_status === "approved" ? (
                        <Badge variant="success">{t.common.approvedStatus}</Badge>
                      ) : tech.expert_review_status === "stale" ? (
                        <Badge variant="danger">{t.common.staleStatus}</Badge>
                      ) : (
                        <Badge variant="outline">{t.common.draftWatermark}</Badge>
                      )}
                    </div>
                    <div className="mt-4 grid grid-cols-3 gap-2 text-sm">
                      <div>
                        <div className="text-xs text-slate-500">{t.fourOutputs.techAssessment}</div>
                        <div className="font-semibold text-slate-900">
                          {((fo.technology_assessment.normalized_score ?? 0) * 100).toFixed(0)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-500">{t.fourOutputs.commReadiness}</div>
                        <div className="font-semibold text-slate-900">
                          {((fo.commercialization_readiness.normalized_score ?? 0) * 100).toFixed(0)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-500">{t.fourOutputs.econValuation}</div>
                        <div className="truncate font-semibold text-emerald-700">
                          {fo.economic_valuation.dcf_base_formatted}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
