"use client";

import React from "react";
import Link from "next/link";
import { useAppState } from "@/lib/i18n";
import { InteractiveSandboxPreview } from "@/components/home/InteractiveSandboxPreview";
import {
  BackgroundAndArchitectureSection,
  ImpactAndBenchmarkSection,
} from "@/components/home/LandingSections";
import {
  Play,
  ArrowRight,
  Globe,
  ShieldCheck,
  Award,
  Sparkles,
  FileText,
  Calculator,
  Cpu,
  CheckCircle2,
  BookOpen,
  Microscope,
} from "lucide-react";

export default function CompanyProfileHomePage() {
  const { lang, setLang } = useAppState();
  const id = lang === "id";

  const navLinks = [
    { href: "#latar-belakang", label: id ? "Latar Belakang" : "Background" },
    { href: "#arsitektur", label: id ? "Inovasi 4-Output" : "4-Output Architecture" },
    { href: "#sandbox-demo", label: id ? "Simulasi Interaktif" : "Live Simulator" },
    { href: "#validasi", label: id ? "Bukti Ilmiah" : "Scientific Proof" },
    { href: "#dampak", label: id ? "Dampak Nasional" : "Ecosystem Impact" },
  ];

  const heroStats = [
    {
      value: "4 Output",
      sub: id ? "Terpisah Tanpa Konversi Skor-ke-Uang" : "Strictly Isolated (Zero Score-to-Cash)",
      accent: "text-blue-400",
    },
    {
      value: "QWK 1.00",
      sub: id ? "Kesepakatan Pakar Tervalidasi (ICC 1.0)" : "Validated Expert Agreement (ICC 1.0)",
      accent: "text-emerald-400",
    },
    {
      value: "MAE Rp 0",
      sub: id ? "Akurasi Mesin Finansial Deterministik WIPO" : "Deterministic WIPO IDR Engine Error",
      accent: "text-amber-300",
    },
    {
      value: "100%",
      sub: id ? "Lacak Kutipan Dokumen (page/para/table)" : "Verbatim Source Locator Traceability",
      accent: "text-indigo-300",
    },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-emerald-500 selection:text-slate-950">
      {/* Top Floating Navigation Bar */}
      <header className="sticky top-0 z-50 border-b border-slate-800/80 bg-slate-950/85 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3.5 sm:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-emerald-500 font-mono text-base font-black text-slate-950 shadow-md shadow-blue-500/20">
              TV
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-extrabold tracking-tight text-white">
                  TechVal AI
                </span>
                <span className="hidden rounded-md border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 font-mono text-[10px] font-semibold text-blue-300 sm:inline-block">
                  ITENAS • DJKI • WIPO
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                {id
                  ? "Platform Penilaian Sains & Valuasi Ekonomi KI"
                  : "Scientific IP Assessment & WIPO Valuation"}
              </p>
            </div>
          </div>

          <nav className="hidden items-center gap-6 text-xs font-semibold text-slate-300 lg:flex">
            {navLinks.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="transition hover:text-emerald-400"
              >
                {item.label}
              </a>
            ))}
          </nav>

          <div className="flex items-center gap-2.5">
            {/* Language Switcher */}
            <div className="flex items-center rounded-xl border border-slate-800 bg-slate-900 p-0.5 text-xs">
              <Globe className="ml-2 mr-1 h-3.5 w-3.5 text-slate-400" />
              {(["id", "en"] as const).map((code) => (
                <button
                  key={code}
                  type="button"
                  onClick={() => setLang(code)}
                  className={`rounded-lg px-2 py-1 font-mono font-bold transition ${
                    lang === code
                      ? "bg-blue-600 text-white"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  {code.toUpperCase()}
                </button>
              ))}
            </div>

            {/* Primary Demo CTA Button in Navbar */}
            <Link
              href="/demo"
              className="group relative inline-flex items-center gap-2 overflow-hidden rounded-xl bg-emerald-500 px-4 py-2 text-xs font-extrabold text-slate-950 shadow-lg shadow-emerald-500/25 transition hover:bg-emerald-400 sm:text-sm"
            >
              <Play className="h-3.5 w-3.5 fill-current transition-transform group-hover:scale-110" />
              <span>{id ? "Coba Demo Sekarang" : "Launch Live Demo"}</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden border-b border-slate-800/80 pt-10 pb-20 sm:pt-16 sm:pb-24">
        <div className="bg-dark-grid pointer-events-none absolute inset-0 opacity-60" />
        <div className="pointer-events-none absolute -top-32 left-1/2 h-96 w-[48rem] -translate-x-1/2 rounded-full bg-blue-600/15 blur-3xl" />
        <div className="pointer-events-none absolute top-40 right-10 h-72 w-72 rounded-full bg-emerald-500/10 blur-3xl" />

        <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-8">
          <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-12">
            {/* Left Column: Pitch & CTAs */}
            <div className="space-y-6 lg:col-span-7">
              <div className="inline-flex flex-wrap items-center gap-2 rounded-full border border-amber-400/30 bg-amber-400/10 px-3.5 py-1.5 text-xs font-mono font-semibold text-amber-300">
                <Award className="h-4 w-4 text-amber-400" />
                <span>
                  {id
                    ? "INOVASI RISET UNGGULAN — ITENAS BANDUNG • STANDAR WIPO & NASA ESTO"
                    : "AWARD-GRADE NATIONAL IP INNOVATION — ITENAS BANDUNG • WIPO & NASA ESTO"}
                </span>
              </div>

              <h1 className="text-4xl font-black tracking-tight text-white sm:text-5xl lg:text-[3.35rem] lg:leading-[1.12]">
                {id ? (
                  <>
                    Jembatan Ilmiah dari{" "}
                    <span className="bg-gradient-to-r from-blue-400 via-emerald-300 to-teal-200 bg-clip-text text-transparent">
                      Dokumen Paten
                    </span>{" "}
                    Menuju{" "}
                    <span className="underline decoration-emerald-500/60 decoration-wavy underline-offset-8">
                      Valuasi Rupiah
                    </span>{" "}
                    yang Terverifikasi.
                  </>
                ) : (
                  <>
                    The Scientific Bridge from{" "}
                    <span className="bg-gradient-to-r from-blue-400 via-emerald-300 to-teal-200 bg-clip-text text-transparent">
                      Patent Disclosures
                    </span>{" "}
                    to Auditable{" "}
                    <span className="underline decoration-emerald-500/60 decoration-wavy underline-offset-8">
                      WIPO Valuation
                    </span>
                    .
                  </>
                )}
              </h1>

              <p className="max-w-2xl text-base leading-relaxed text-slate-300 sm:text-lg">
                {id
                  ? "Platform pertama di Indonesia yang memisahkan secara ketat Penilaian Teknis NASA TRL 1–9, Kesiapan Komersialisasi TKDN, dan Mesin Finansial Deterministik WIPO dalam Rupiah (IDR) dengan pelacakan bukti kutipan dokumen 100% bebas halusinasi."
                  : "Indonesia's premier scientific technology assessment and IP valuation platform enforcing strict separation between native NASA TRL 1–9 maturity, market readiness, and deterministic WIPO financial models in IDR with 100% verbatim source provenance."}
              </p>

              {/* Prominent Action Buttons */}
              <div className="flex flex-wrap items-center gap-3.5 pt-2">
                <Link
                  href="/demo"
                  className="group relative inline-flex items-center gap-3 overflow-hidden rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-400 px-7 py-4 text-base font-black text-slate-950 shadow-xl shadow-emerald-500/25 transition duration-200 hover:-translate-y-0.5 hover:shadow-emerald-500/40"
                >
                  <span className="relative flex h-3 w-3">
                    <span className="animate-pulse-ring absolute inline-flex h-full w-full rounded-full bg-slate-950 opacity-75" />
                    <span className="relative inline-flex h-3 w-3 rounded-full bg-slate-950" />
                  </span>
                  <span>
                    {id
                      ? "Coba Demo Langsung (Tanpa Login)"
                      : "Try Interactive Demo Now (Zero Setup)"}
                  </span>
                  <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-1" />
                </Link>

                <a
                  href="#sandbox-demo"
                  className="inline-flex items-center gap-2 rounded-2xl border border-slate-700 bg-slate-900/90 px-5 py-4 text-sm font-bold text-slate-200 transition hover:border-blue-400 hover:bg-slate-900 hover:text-white"
                >
                  <Calculator className="h-4 w-4 text-blue-400" />
                  <span>
                    {id ? "Simulasi Cepat di Halaman Ini" : "Quick Simulator Below"}
                  </span>
                </a>
              </div>

              {/* Quick Module Jump Links */}
              <div className="flex flex-wrap items-center gap-2 pt-2 text-xs text-slate-400">
                <span className="font-mono uppercase text-slate-500">
                  {id ? "Akses Cepat Juri:" : "Judge Quick Access:"}
                </span>
                <Link
                  href="/pipeline"
                  className="rounded-lg border border-slate-800 bg-slate-900/70 px-2.5 py-1 font-mono text-slate-300 hover:border-blue-500/50 hover:text-blue-300"
                >
                  8-Agent LangGraph →
                </Link>
                <Link
                  href="/valuation"
                  className="rounded-lg border border-slate-800 bg-slate-900/70 px-2.5 py-1 font-mono text-slate-300 hover:border-emerald-500/50 hover:text-emerald-300"
                >
                  WIPO IDR Studio →
                </Link>
                <Link
                  href="/evaluation"
                  className="rounded-lg border border-slate-800 bg-slate-900/70 px-2.5 py-1 font-mono text-slate-300 hover:border-amber-500/50 hover:text-amber-300"
                >
                  QWK & ICC Benchmark →
                </Link>
                <Link
                  href="/reports"
                  className="rounded-lg border border-slate-800 bg-slate-900/70 px-2.5 py-1 font-mono text-slate-300 hover:border-indigo-500/50 hover:text-indigo-300"
                >
                  PDF Report Generator →
                </Link>
              </div>
            </div>

            {/* Right Column: Live Case Telemetry Dossier Card */}
            <div className="lg:col-span-5">
              <div className="animate-float-slow relative rounded-3xl border border-slate-800 bg-slate-900/95 p-6 shadow-2xl">
                <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                  <div>
                    <div className="font-mono text-[11px] font-bold uppercase tracking-wider text-emerald-400">
                      LIVE VERIFIED CASE DOSSIER
                    </div>
                    <div className="mt-0.5 text-sm font-bold text-white">
                      IDP000089421 • ITENAS-PAT-2026-001
                    </div>
                  </div>
                  <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 font-mono text-xs font-bold text-emerald-300">
                    TRL 6 / 9
                  </span>
                </div>

                <div className="mt-4 space-y-3">
                  <div className="rounded-2xl border border-slate-800 bg-slate-950 p-3.5">
                    <div className="text-xs font-semibold text-slate-400">
                      {id ? "Invensi Paten Teruji:" : "Evaluated Patent Invention:"}
                    </div>
                    <div className="mt-1 text-sm font-bold text-slate-100 leading-snug">
                      {id
                        ? "Reaktor Membran Nanokomposit Fotokatalitik TiO2-Zeolit untuk Limbah Cair Industri Tekstil"
                        : "Photocatalytic TiO2-Zeolite Nanocomposite Membrane Reactor for Industrial Textile Wastewater"}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-2xl border border-slate-800 bg-slate-950 p-3.5">
                      <div className="font-mono text-[11px] text-slate-400">
                        OUTPUT 1 • TECH SCORE
                      </div>
                      <div className="mt-1 font-mono text-2xl font-black text-blue-400">
                        78.1%
                      </div>
                      <div className="mt-0.5 text-[11px] text-slate-500">
                        94.2% COD Removal [page:1]
                      </div>
                    </div>

                    <div className="rounded-2xl border border-slate-800 bg-slate-950 p-3.5">
                      <div className="font-mono text-[11px] text-slate-400">
                        OUTPUT 2 • MARKET & TKDN
                      </div>
                      <div className="mt-1 font-mono text-2xl font-black text-indigo-400">
                        77.5%
                      </div>
                      <div className="mt-0.5 text-[11px] text-slate-500">
                        82% TKDN • 2 EPC LOIs [page:3]
                      </div>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/20 p-4">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[11px] font-bold uppercase text-emerald-300">
                        OUTPUT 3 • WIPO BASE DCF VALUATION (IDR)
                      </span>
                      <span className="font-mono text-[11px] text-slate-400">
                        α = 0.75 | r = 15%
                      </span>
                    </div>
                    <div className="mt-1 font-mono text-2xl font-black text-emerald-400 sm:text-3xl">
                      Rp 3.155.146.516
                    </div>
                    <div className="mt-1.5 flex items-center justify-between text-[11px] font-mono text-slate-400">
                      <span>Relief-from-Royalty: Rp 486,25 Jt</span>
                      <span>Cost: Rp 992,75 Jt</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-xs">
                    <span className="flex items-center gap-1.5 font-mono text-slate-300">
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                      Output 4: 100% Evidence Coverage (11/11)
                    </span>
                    <Link
                      href="/demo"
                      className="font-mono font-bold text-emerald-400 hover:underline"
                    >
                      {id ? "Buka Kasus →" : "Inspect →"}
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 4 Key Competition Metrics Strip */}
          <div className="mt-16 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {heroStats.map((st, idx) => (
              <div
                key={idx}
                className="rounded-2xl border border-slate-800/90 bg-slate-900/60 p-5 backdrop-blur"
              >
                <div className={`font-mono text-3xl font-black ${st.accent}`}>
                  {st.value}
                </div>
                <div className="mt-1 text-xs font-medium text-slate-300">
                  {st.sub}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Main Content Container */}
      <div className="mx-auto max-w-7xl space-y-28 px-4 py-20 sm:px-8">
        {/* Background, Urgency & 4-Output Architecture */}
        <BackgroundAndArchitectureSection id={id} />

        {/* Live Interactive Sandbox Section right on the Home Page */}
        <section id="sandbox-demo" className="scroll-mt-24 space-y-6">
          <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-xs font-mono font-semibold text-emerald-300">
                <Sparkles className="h-3.5 w-3.5" />
                {id
                  ? "SIMULASI LANGSUNG DI HALAMAN UTAMA"
                  : "INTERACTIVE SANDBOX ON THIS PAGE"}
              </div>
              <h2 className="mt-2.5 text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
                {id
                  ? "Uji Mesin Valuasi WIPO & 8-Agen LangGraph Sekarang"
                  : "Test-Drive the WIPO Valuation Engine & 8-Agent Trace"}
              </h2>
            </div>
            <Link
              href="/demo"
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-xs font-bold text-white shadow-lg shadow-blue-600/25 transition hover:bg-blue-500 sm:text-sm"
            >
              <Play className="h-4 w-4 fill-current" />
              {id
                ? "Buka Ruang Kerja Demo Lengkap"
                : "Enter Full Interactive Workspace"}
            </Link>
          </div>

          <InteractiveSandboxPreview id={id} />
        </section>

        {/* Empirical Validation & Ecosystem Impact */}
        <ImpactAndBenchmarkSection id={id} />

        {/* Bottom Competition Call-to-Action Banner */}
        <section className="relative overflow-hidden rounded-3xl border border-emerald-500/40 bg-gradient-to-r from-blue-950 via-slate-900 to-emerald-950 p-8 sm:p-12 shadow-2xl">
          <div className="bg-dark-grid pointer-events-none absolute inset-0 opacity-40" />
          <div className="relative z-10 flex flex-col items-start justify-between gap-8 lg:flex-row lg:items-center">
            <div className="max-w-2xl space-y-3">
              <div className="inline-flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 font-mono text-xs font-bold text-emerald-300">
                {id ? "SIAP DIUJI OLEH DEWAN JURI & PENGGUNA" : "READY FOR LIVE EVALUATION"}
              </div>
              <h2 className="text-3xl font-black tracking-tight text-white sm:text-4xl">
                {id
                  ? "Siap Mencoba Seluruh Fitur TechVal AI Secara Langsung?"
                  : "Ready to Experience the Complete TechVal AI Platform?"}
              </h2>
              <p className="text-sm leading-relaxed text-slate-300 sm:text-base">
                {id
                  ? "Masuk ke Ruang Kerja Demo untuk mengunggah dokumen paten baru, menjalankan orkestrasi 8-agen AI, mengkalibrasi matriks Saaty AHP, hingga mengunduh laporan PDF resmi dwibahasa."
                  : "Enter the Demo Workspace to upload patent documents, trigger the 8-agent LangGraph pipeline, calibrate Saaty AHP matrices, and export bilingual PDF valuation reports."}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <Link
                href="/demo"
                className="inline-flex items-center gap-3 rounded-2xl bg-emerald-400 px-7 py-4 text-base font-black text-slate-950 shadow-xl shadow-emerald-500/25 transition hover:bg-emerald-300"
              >
                <Play className="h-5 w-5 fill-current" />
                <span>{id ? "Masuk ke Demo Interaktif" : "Launch Full Demo Workspace"}</span>
              </Link>
              <Link
                href="/reports"
                className="inline-flex items-center gap-2 rounded-2xl border border-slate-700 bg-slate-900/90 px-5 py-4 text-sm font-bold text-white transition hover:border-slate-500"
              >
                <FileText className="h-4 w-4 text-blue-400" />
                <span>{id ? "Lihat Contoh Laporan PDF" : "View Sample PDF Reports"}</span>
              </Link>
            </div>
          </div>
        </section>
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-10 text-xs text-slate-500">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 sm:flex-row sm:px-8">
          <div>
            <strong className="text-slate-300">TechVal AI</strong> — Institut Teknologi Nasional (ITENAS) Bandung • Scientific Technology Assessment & WIPO IDR Valuation Platform.
          </div>
          <div className="flex flex-wrap items-center gap-4 font-mono">
            <Link href="/demo" className="text-slate-400 hover:text-emerald-400">
              /demo
            </Link>
            <Link href="/methodology" className="text-slate-400 hover:text-emerald-400">
              /methodology
            </Link>
            <Link href="/evaluation" className="text-slate-400 hover:text-emerald-400">
              /evaluation
            </Link>
            <Link href="/reports" className="text-slate-400 hover:text-emerald-400">
              /reports
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
