"use client";

import React from "react";
import Link from "next/link";
import { ArrowRight, Globe } from "lucide-react";
import { useAppState } from "@/lib/i18n";
import { computeDcf, formatRupiah } from "@/lib/dcf-demo";
import { CountUp, Reveal } from "@/components/home/Reveal";
import { InteractiveSandboxPreview } from "@/components/home/InteractiveSandboxPreview";
import { BackgroundSection, SectionHeading, SolutionSection } from "@/components/home/LandingSections";
import { ImpactSection, ValidationSection } from "@/components/home/ImpactSections";
import { AgentRoster } from "@/components/advisor/AgentRoster";

const BASE_NPV = computeDcf(0.15, 0.75, 1).npv;

export default function CompanyProfileHomePage() {
  const { lang, setLang } = useAppState();
  const id = lang === "id";

  const nav = [
    { href: "#latar-belakang", label: id ? "Latar belakang" : "Background" },
    { href: "#solusi", label: id ? "Solusi" : "Solution" },
    { href: "#agen", label: id ? "8 Agen Muse" : "8 Muse Agents" },
    { href: "#coba", label: id ? "Coba" : "Try it" },
    { href: "#dampak", label: id ? "Dampak" : "Impact" },
    { href: "#validasi", label: id ? "Validasi" : "Validation" },
  ];

  const facts = [
    { value: <CountUp to={78.13} format={(v) => `${v.toFixed(1)}%`} />, label: id ? "Skor teknologi" : "Technology score" },
    { value: <CountUp to={77.5} format={(v) => `${v.toFixed(1)}%`} />, label: id ? "Kesiapan komersialisasi" : "Commercialization readiness" },
    { value: "TRL 6", label: id ? "Tingkat kesiapan teknologi" : "Technology readiness level" },
    { value: <CountUp to={BASE_NPV} format={formatRupiah} />, label: id ? "Nilai DCF dasar" : "Base DCF value" },
  ];

  return (
    <div className="min-h-screen bg-white text-slate-900">
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-3 sm:px-8">
          <Link href="/" className="text-lg font-semibold tracking-tight">
            TechVal AI
          </Link>
          <nav className="hidden items-center gap-7 text-sm text-slate-600 md:flex">
            {nav.map((n) => (
              <a key={n.href} href={n.href} className="transition-colors hover:text-slate-900">
                {n.label}
              </a>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setLang(id ? "en" : "id")}
              className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-sm text-slate-600 transition-colors hover:bg-slate-100"
              aria-label="Switch language"
            >
              <Globe className="h-4 w-4" />
              {id ? "ID" : "EN"}
            </button>
            <Link
              href="/demo"
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
            >
              {id ? "Coba Demo" : "Try Demo"}
            </Link>
          </div>
        </div>
      </header>

      <section className="py-20 sm:py-28">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <Reveal>
            <p className="text-sm font-medium text-blue-700">ITENAS Bandung</p>
            <h1 className="mt-4 max-w-3xl text-4xl font-semibold leading-[1.1] tracking-tight sm:text-6xl">
              {id
                ? "Dari dokumen paten ke nilai ekonomi yang bisa diperiksa."
                : "From patent document to an economic value you can verify."}
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-slate-600">
              {id
                ? "TechVal AI menilai kematangan teknologi, kesiapan komersialisasi, dan nilai ekonominya dalam Rupiah. Setiap skor disertai kutipan dari dokumen asli."
                : "TechVal AI assesses technology maturity, commercialization readiness, and economic value in Rupiah. Every score comes with a quote from the source document."}
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Link
                href="/demo"
                className="group inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 text-base font-medium text-white transition-colors hover:bg-blue-700"
              >
                {id ? "Coba Demo" : "Try the Demo"}
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
              <Link href="/advisor" className="text-base font-medium text-slate-700 transition-colors hover:text-slate-900">
                {id ? "Tanya Penasihat AI (Muse Spark)" : "Ask the AI Advisor (Muse Spark)"}
              </Link>
              <a href="#coba" className="text-base font-medium text-slate-700 transition-colors hover:text-slate-900">
                {id ? "Simulasi singkat ↓" : "Quick simulation ↓"}
              </a>
            </div>
          </Reveal>

          <Reveal delay={150}>
            <div className="mt-16 border-t border-slate-200 pt-8">
              <p className="text-sm text-slate-500">
                {id
                  ? "Kasus demo: Reaktor membran nanokomposit TiO2-zeolit untuk limbah cair tekstil (IDP000089421)"
                  : "Demo case: TiO2-zeolite nanocomposite membrane reactor for textile wastewater (IDP000089421)"}
              </p>
              <dl className="mt-6 grid grid-cols-2 gap-8 lg:grid-cols-4">
                {facts.map((f) => (
                  <div key={f.label}>
                    <dd className="text-2xl font-semibold tabular-nums tracking-tight sm:text-3xl">{f.value}</dd>
                    <dt className="mt-1 text-sm text-slate-500">{f.label}</dt>
                  </div>
                ))}
              </dl>
            </div>
          </Reveal>
        </div>
      </section>

      <BackgroundSection id={id} />
      <SolutionSection id={id} />

      <section id="agen" className="scroll-mt-20 py-20 sm:py-28">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div className="flex flex-wrap items-end justify-between gap-6">
            <Reveal>
              <SectionHeading
                eyebrow="Meta Muse"
                title={id ? "8 agen dan model yang digunakan." : "8 agents and the models they use."}
              >
                {id
                  ? "Setiap tahap memakai model dari katalog resmi api.meta.ai: enam agen teks pada /v1/chat/completions, satu model gambar pada /v1/images/generations, dan satu model transkripsi suara pada /v1/asr/transcribe."
                  : "Each stage maps to a model from the official api.meta.ai catalog: six text agents on /v1/chat/completions, one image model on /v1/images/generations, and one speech transcription model on /v1/asr/transcribe."}
              </SectionHeading>
            </Reveal>
            <Link
              href="/advisor"
              className="group inline-flex items-center gap-1.5 text-sm font-medium text-blue-700 hover:text-blue-800"
            >
              {id ? "Tanya salah satu agen" : "Ask an agent"}
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </div>
          <Reveal delay={100} className="mt-12">
            <AgentRoster id={id} />
          </Reveal>
        </div>
      </section>

      <section id="coba" className="scroll-mt-20 py-20 sm:py-28">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <Reveal>
            <SectionHeading
              eyebrow={id ? "Coba sendiri" : "Try it yourself"}
              title={id ? "Geser asumsi, lihat nilainya berubah." : "Move the assumptions, watch the value change."}
            />
          </Reveal>
          <Reveal delay={100} className="mt-10">
            <InteractiveSandboxPreview id={id} />
          </Reveal>
        </div>
      </section>

      <ImpactSection id={id} />
      <ValidationSection id={id} />

      <section className="py-20 sm:py-28">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <Reveal>
            <div className="rounded-2xl bg-slate-900 px-6 py-14 text-center sm:px-12">
              <h2 className="mx-auto max-w-xl text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                {id ? "Coba dengan kasus paten demo." : "Try it with the demo patent case."}
              </h2>
              <p className="mx-auto mt-4 max-w-lg text-slate-300">
                {id
                  ? "Tanpa login. Jalankan analisis, lihat bukti, dan unduh laporan."
                  : "No login needed. Run the analysis, inspect the evidence, and download the report."}
              </p>
              <Link
                href="/demo"
                className="group mt-8 inline-flex items-center gap-2 rounded-lg bg-white px-6 py-3 text-base font-medium text-slate-900 transition-colors hover:bg-slate-100"
              >
                {id ? "Buka Demo" : "Open the Demo"}
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
            </div>
          </Reveal>
        </div>
      </section>

      <footer className="border-t border-slate-200 py-8 text-sm text-slate-500">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-5 sm:px-8">
          <span>TechVal AI · Institut Teknologi Nasional Bandung</span>
          <div className="flex gap-5">
            <Link href="/demo" className="hover:text-slate-900">Demo</Link>
            <Link href="/methodology" className="hover:text-slate-900">{id ? "Metodologi" : "Methodology"}</Link>
            <Link href="/evaluation" className="hover:text-slate-900">{id ? "Evaluasi" : "Evaluation"}</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
