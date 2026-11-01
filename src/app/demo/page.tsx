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
import {
  PlusCircle,
  ArrowRight,
  FileUp,
  Cpu,
  FileText,
  Sparkles,
  CheckCircle2,
  Building2,
  Play,
  Calculator,
  Microscope,
} from "lucide-react";

const inputClass =
  "mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-200";
const labelClass = "block text-sm font-medium text-slate-800";

export default function DemoWorkspacePage() {
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
      title: id ? "1. Unggah & Audit Dokumen" : "1. Upload & Audit Documents",
      desc: id
        ? "Tambahkan spesifikasi paten/teknis dengan verifikasi SHA-256 & brankas terenkripsi."
        : "Add patent or technical files with SHA-256 verification and encrypted vault storage.",
    },
    {
      href: "/pipeline",
      icon: Cpu,
      title: id ? "2. Eksekusi 8-Agen LangGraph" : "2. Run 8-Agent LangGraph",
      desc: id
        ? "AI mengekstrak bukti kutipan persis (page:N / para:N) dan memvalidasi TRL 1–9."
        : "AI extracts exact verbatim quotes (page:N / para:N) and validates NASA TRL 1–9.",
    },
    {
      href: "/valuation",
      icon: Calculator,
      title: id ? "3. Simulasi Valuasi WIPO (IDR)" : "3. WIPO Valuation Studio (IDR)",
      desc: id
        ? "Uji skenario DCF, Relief-from-Royalty, Cost, & Monte Carlo dalam Rupiah."
        : "Simulate DCF, Relief-from-Royalty, Cost, & Monte Carlo scenarios in IDR.",
    },
    {
      href: "/reports",
      icon: FileText,
      title: id ? "4. Unduh Laporan Resmi PDF" : "4. Download Official PDF Report",
      desc: id
        ? "Ekspor laporan valuasi dwibahasa siap audit untuk DJKI, TTO, atau mitra industri."
        : "Export audit-ready bilingual PDF reports for DJKI, TTOs, or industrial partners.",
    },
  ];

  return (
    <div className="space-y-8">
      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="max-w-2xl space-y-1.5">
            <div className="text-sm font-medium text-blue-700">
              {id ? "Mode demo" : "Demo mode"}
            </div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
              {id ? "Ruang kerja penilaian & valuasi" : "Assessment & valuation workspace"}
            </h1>
            <p className="text-sm leading-relaxed text-slate-600">
              {id
                ? "Kasus paten reaktor membran TiO2-zeolit (IDP000089421) sudah dimuat lengkap dengan bukti dokumen, skor TRL 6, dan valuasi DCF."
                : "The TiO2-zeolite membrane reactor patent case (IDP000089421) is pre-loaded with document evidence, a TRL 6 score, and a DCF valuation."}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/pipeline"
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700"
            >
              <Play className="h-4 w-4" />
              {id ? "Jalankan analisis AI" : "Run AI analysis"}
            </Link>
            <Link
              href="/"
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
            >
              <Building2 className="h-4 w-4" />
              {id ? "Profil perusahaan" : "Company profile"}
            </Link>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">
            {id ? "Portofolio Teknologi Aktif" : "Active Technology Portfolio"}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {id
              ? "Pilih kasus teknologi di bawah atau tambahkan invensi baru untuk diuji dari awal."
              : "Select an existing technology case below or add a new invention to test from scratch."}
          </p>
        </div>
        <Button size="lg" onClick={() => setShowCreateForm(!showCreateForm)}>
          <PlusCircle className="h-5 w-5" />
          {id ? "Tambah Teknologi Baru" : "Add New Technology"}
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
                <div>
                  <div className="text-xs font-mono uppercase tracking-wider text-blue-700">
                    {activeTech.code} • {activeTech.patent_application_number || activeTech.patent_status}
                  </div>
                  <h3 className="text-xl font-bold text-slate-900">{titleOf(activeTech)}</h3>
                </div>
                <div className="flex items-center gap-3">
                  <Link
                    href="/assessment"
                    className="inline-flex items-center gap-1.5 rounded-xl border border-blue-200 bg-blue-50 px-3.5 py-2 text-xs font-bold text-blue-700 transition hover:bg-blue-100"
                  >
                    <Microscope className="h-4 w-4" />
                    {id ? "Rincian Bukti & Skor" : "Inspect Evidence & Scores"}
                  </Link>
                  <Link
                    href="/valuation"
                    className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-2 text-xs font-bold text-emerald-800 transition hover:bg-emerald-100"
                  >
                    <Calculator className="h-4 w-4" />
                    {id ? "Buka Kalkulator WIPO" : "Open WIPO Calculator"}
                  </Link>
                </div>
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
              {id ? "Alur Pengujian Demo End-to-End" : "End-to-End Demo Walkthrough"}
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {steps.map((s) => {
                const Icon = s.icon;
                return (
                  <Link
                    key={s.href}
                    href={s.href}
                    className="group flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 transition duration-200 hover:-translate-y-0.5 hover:border-blue-400 hover:shadow-md"
                  >
                    <div>
                      <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-700 transition group-hover:bg-blue-600 group-hover:text-white">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="mt-3.5 text-base font-bold text-slate-900">{s.title}</div>
                      <p className="mt-1.5 text-xs leading-relaxed text-slate-600">{s.desc}</p>
                    </div>
                    <div className="mt-4 inline-flex items-center gap-1 text-xs font-bold text-blue-700 group-hover:translate-x-1 transition-transform">
                      {id ? "Buka modul" : "Open module"} <ArrowRight className="h-3.5 w-3.5" />
                    </div>
                  </Link>
                );
              })}
            </div>
          </section>

          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-slate-900">
                {id ? "Daftar Invensi dalam Portofolio" : "Inventions in Portfolio"}
              </h2>
              <span className="text-sm text-slate-500">
                {technologies.length} {id ? "teknologi terdaftar" : "registered technologies"}
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
