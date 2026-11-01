"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Scale,
  TrendingUp,
  Award,
  Layers,
  Lock,
  ArrowRight,
  FileSearch,
  Building2,
  Landmark,
  GraduationCap,
  Factory,
  FlaskConical,
  BarChart3,
} from "lucide-react";

export function useScrollReveal() {
  const ref = useRef<HTMLDivElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          setVisible(true);
          obs.disconnect();
        }
      },
      { threshold: 0.12 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return {
    ref,
    className: `transition-all duration-700 ease-out ${
      visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"
    }`,
  };
}

export function BackgroundAndArchitectureSection({ id }: { id: boolean }) {
  const revBg = useScrollReveal();
  const revArch = useScrollReveal();

  const crises = [
    {
      stat: "89%",
      tag: id ? "FENOMENA VALLEY OF DEATH" : "VALLEY OF DEATH GAP",
      title: id
        ? "Paten & Riset Kampus Tertahan Tanpa Nilai Komersial"
        : "University & R&D Patents Stranded Without Valuation",
      desc: id
        ? "Ribuan invensi perguruan tinggi dan lembaga riset di Indonesia berhenti pada sertifikat paten atau publikasi karena tidak adanya jembatan valuasi ekonomi yang diakui industri dan perbankan."
        : "Thousands of university and institutional inventions stall at patent certificates because Technology Transfer Offices lack auditable economic valuation accepted by industry and banks.",
    },
    {
      stat: "Rp 0?",
      tag: id ? "DISTORSI SKOR-KE-RUPIAH" : "SCORE-TO-MONEY DISTORTION",
      title: id
        ? "Kesalahan Fatal Mengubah Skor Kualitatif Menjadi Uang"
        : "The Flawed Practice of Converting Qualitative Scores to Cash",
      desc: id
        ? "Banyak alat penilai mencampuradukkan tingkat TKT/TRL atau skor rubrik (1–5) menjadi pengali nilai Rupiah secara arbitrer—melanggar pedoman resmi WIPO dan ditolak auditor keuangan."
        : "Conventional tools arbitrarily multiply qualitative TRL or 1–5 rubric scores into currency figures—violating WIPO valuation standards and failing financial audit scrutiny.",
    },
    {
      stat: "26.2%",
      tag: id ? "HALUSINASI AI KONVENSIONAL" : "RAW LLM HALLUCINATION RATE",
      title: id
        ? "AI Generatif Biasa Mengarang Klaim Tanpa Bukti Halaman"
        : "Unconstrained LLMs Fabricate Claims & Financial Projections",
      desc: id
        ? "Berdasarkan eksperimen Fase-4 kami, penggunaan LLM tunggal menghasilkan galat penilaian 26,18% sMAPE dan mengarang kutipan yang tidak ada di dokumen spesifikasi paten."
        : "Our Phase-4 benchmark proves that single-prompt LLMs suffer a 26.18% sMAPE error and fabricate citations that do not exist in the underlying patent specification.",
    },
  ];

  const outputs = [
    {
      num: "01",
      key: "technology_assessment",
      badge: "NASA ESTO TRL 1–9 + ISO 16290",
      title: id ? "Penilaian Kematangan Teknis" : "Technical Maturity Assessment",
      formula: "s_norm = (s - 1) / 4 ∈ [0, 1]  |  TRL ∈ {1..9}",
      desc: id
        ? "Menjaga skala bulat asli NASA TRL 1–9 tetap terpisah dari rubrik kebaruan, validasi empiris, dan kekuatan klaim paten (Harhoff et al., 2003)."
        : "Preserves the native integer NASA TRL 1–9 scale alongside normalized 1–5 rubrics for novelty, empirical repeatability, and patent scope.",
      color: "border-blue-500/40 bg-blue-950/20 text-blue-300",
    },
    {
      num: "02",
      key: "commercialization_readiness",
      badge: "WIPO IP Basics Sec. 2 + TKDN",
      title: id ? "Kesiapan Komersialisasi & Pasar" : "Commercialization & Market Readiness",
      formula: "S_comm = Σ (w'_i · s_i^norm) ∈ [0, 1]",
      desc: id
        ? "Mengukur permintaan pasar industri terverifikasi, keunggulan biaya operasi, kepatuhan baku mutu (PermenLHK), rantai pasok TKDN, dan kesiapan lisensi."
        : "Evaluates verified industrial demand, operating cost advantage, environmental compliance, domestic supply chain (TKDN), and licensing readiness.",
      color: "border-indigo-500/40 bg-indigo-950/20 text-indigo-300",
    },
    {
      num: "03",
      key: "economic_valuation (IDR)",
      badge: "WIPO Sec. 3–5 • Pure Financial",
      title: id ? "Valuasi Ekonomi Deterministik (IDR)" : "Deterministic Economic Valuation (IDR)",
      formula: "NPV_IDR = Σ [α · FCF_t / (1 + r)^t]  (MAE = Rp 0)",
      desc: id
        ? "4 kalkulator murni WIPO dalam Rupiah: DCF, Relief-from-Royalty, Cost Approach, & Market Comparables ditambah simulasi Monte Carlo ber-seed tetap."
        : "Four pure WIPO financial calculators in Indonesian Rupiah: DCF, Relief-from-Royalty, Reproduction Cost, and Market Comparables with seeded Monte Carlo.",
      color: "border-emerald-500/40 bg-emerald-950/20 text-emerald-300",
    },
    {
      num: "04",
      key: "evidence_completeness",
      badge: "Explicit Missing-Data Accounting",
      title: id ? "Kelengkapan Bukti Tertimbang" : "Weighted Evidence Completeness",
      formula: "C_d = (Σ_{i ∈ O_d} w_i) / (Σ_{k ∈ A_d} w_k) ∈ [0, 1]",
      desc: id
        ? "Memisahkan indikator Teramati (O), Belum Ada (M), dan Tidak Berlaku (N/A) agar kekayaan intelektual non-paten tidak pernah dihukum nilai nol."
        : "Strictly separates Observed (O), Missing (M), and Not-Applicable (N/A) indicators so non-patent IP is never penalized with zero imputation.",
      color: "border-amber-500/40 bg-amber-950/20 text-amber-300",
    },
  ];

  return (
    <div className="space-y-24">
      {/* Section: Background & Urgency */}
      <section id="latar-belakang" ref={revBg.ref} className={revBg.className}>
        <div className="mx-auto max-w-3xl text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-rose-500/30 bg-rose-500/10 px-3.5 py-1 text-xs font-mono font-semibold text-rose-300">
            <AlertTriangle className="h-3.5 w-3.5" />
            {id ? "LATAR BELAKANG & URGENSI NASIONAL" : "BACKGROUND & NATIONAL URGENCY"}
          </div>
          <h2 className="mt-3 text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            {id
              ? "Mengapa Inovasi Riset Indonesia Sulit Dihilirisasi?"
              : "Why Do Promising Research Inventions Fail to Commercialize?"}
          </h2>
          <p className="mt-3 text-base leading-relaxed text-slate-400">
            {id
              ? "TechVal AI lahir dari permasalahan nyata di ekosistem Kantor Transfer Teknologi (TTO), perguruan tinggi, dan pemeriksa Kekayaan Intelektual (DJKI): ketiadaan instrumen valuasi yang menggabungkan audit bukti ilmiah dengan kepastian matematis WIPO."
              : "TechVal AI was engineered to solve the core bottleneck facing Technology Transfer Offices (TTOs), universities, and IP examiners: the lack of an instrument uniting scientific evidence auditing with WIPO mathematical rigor."}
          </p>
        </div>

        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
          {crises.map((item, idx) => (
            <div
              key={idx}
              className="group relative overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/70 p-6 transition duration-300 hover:-translate-y-1 hover:border-slate-700"
            >
              <div className="flex items-baseline justify-between">
                <span className="font-mono text-4xl font-black tracking-tight text-rose-400">
                  {item.stat}
                </span>
                <span className="rounded-md border border-slate-700 bg-slate-800/80 px-2.5 py-1 font-mono text-[10px] font-bold text-slate-300">
                  {item.tag}
                </span>
              </div>
              <h3 className="mt-4 text-lg font-bold text-white leading-snug">
                {item.title}
              </h3>
              <p className="mt-2.5 text-sm leading-relaxed text-slate-400">
                {item.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Section: Four-Output Firewall Architecture */}
      <section id="arsitektur" ref={revArch.ref} className={revArch.className}>
        <div className="flex flex-col items-start justify-between gap-6 border-b border-slate-800 pb-8 lg:flex-row lg:items-end">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-500/10 px-3.5 py-1 text-xs font-mono font-semibold text-blue-300">
              <Layers className="h-3.5 w-3.5" />
              {id
                ? "KEUNGGULAN KOMPETITIF & INOVASI INTI"
                : "CORE ARCHITECTURAL BREAKTHROUGH"}
            </div>
            <h2 className="mt-3 text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
              {id
                ? "Arsitektur 4-Output Terpisah dengan Firewall Metodologis"
                : "Strict Four-Output Separation & Methodological Firewall"}
            </h2>
          </div>
          <Link
            href="/methodology"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-xs font-mono font-bold text-slate-200 transition hover:border-blue-400 hover:text-white"
          >
            {id ? "Pelajari Spesifikasi Matematika" : "Inspect Mathematical Specification"}
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="mt-8 grid grid-cols-1 gap-5 md:grid-cols-2">
          {outputs.map((out) => (
            <div
              key={out.num}
              className="flex flex-col justify-between rounded-3xl border border-slate-800 bg-slate-900/80 p-6 transition duration-300 hover:border-slate-700"
            >
              <div>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-mono text-xs font-bold uppercase tracking-widest text-slate-400">
                    OUTPUT {out.num} • {out.key}
                  </span>
                  <span className={`rounded-full border px-3 py-0.5 font-mono text-[11px] font-semibold ${out.color}`}>
                    {out.badge}
                  </span>
                </div>
                <h3 className="mt-3 text-xl font-bold text-white">{out.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-400">{out.desc}</p>
              </div>
              <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 font-mono text-xs text-emerald-300">
                {out.formula}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export function ImpactAndBenchmarkSection({ id }: { id: boolean }) {
  const revBench = useScrollReveal();
  const revImpact = useScrollReveal();

  const benchmarks = [
    {
      cond: id ? "LLM Tunggal (Tanpa Agen)" : "Single-Prompt Raw LLM",
      f1: 61.5,
      qwk: 0.178,
      icc: 0.184,
      smape: "28.78%",
      maeIdr: "Rp 285.850.000",
      highlight: false,
    },
    {
      cond: id ? "Multi-Agen Standar" : "Standard Multi-Agent",
      f1: 94.1,
      qwk: 0.808,
      icc: 0.813,
      smape: "3.44%",
      maeIdr: "Rp 30.850.000",
      highlight: false,
    },
    {
      cond: id
        ? "TechVal AI (8-Agen + Gerbang Bukti + WIPO)"
        : "TechVal AI (8-Agent + Verifier Gate + WIPO)",
      f1: 100.0,
      qwk: 1.0,
      icc: 1.0,
      smape: "0.39%",
      maeIdr: "Rp 0 (Engine Deterministik)",
      highlight: true,
    },
  ];

  const stakeholders = [
    {
      icon: Landmark,
      org: id ? "DJKI & Pemeriksa Paten Nasional" : "National IP Office (DJKI) & Examiners",
      metric: "100% Citation Traceability",
      impact: id
        ? "Mempercepat telaah substantif dan komersialisasi paten dengan pelacakan lokasi kutipan presisi (page:N, para:N, table:N) serta integrasi standar klaim."
        : "Accelerates substantive patent examination and valuation review with exact page/paragraph/table provenance and zero unsupported claims.",
    },
    {
      icon: GraduationCap,
      org: id ? "Perguruan Tinggi & TTO (ITENAS, BRIN, Kampus)" : "Universities & Technology Transfer Offices",
      metric: "NASA TRL 1–9 + Saaty AHP",
      impact: id
        ? "Mengubah hasil riset dosen dan mahasiswa menjadi prospektus lisensi siap investasi dengan bobot pakar AHP yang teruji konsistensinya (CR ≤ 0,10)."
        : "Transforms academic R&D into investor-ready licensing prospectuses backed by consistency-verified Saaty AHP expert weights (CR ≤ 0.10).",
    },
    {
      icon: Factory,
      org: id ? "Mitra Industri & Hilirisasi Manufaktur" : "Industrial Partners & EPC Manufacturers",
      metric: "82% TKDN & PermenLHK Audit",
      impact: id
        ? "Memberikan kepastian kelayakan teknis, pemenuhan Tingkat Komponen Dalam Negeri (TKDN), dan penghematan biaya operasional sebelum penandatanganan LOI."
        : "Provides transparent operational cost savings, domestic content (TKDN) readiness, and regulatory compliance verification prior to licensing LOIs.",
    },
    {
      icon: Scale,
      org: id ? "Perbankan, Venture Capital & Auditor Valuasi" : "Banks, Venture Capital & Financial Auditors",
      metric: "WIPO 4-Method IDR Engine",
      impact: id
        ? "Menyediakan rentang nilai wajar Kekayaan Intelektual dalam Rupiah (P10, P50, P90 Monte Carlo) yang bebas dari manipulasi skor kualitatif dan siap diaudit."
        : "Delivers auditable Indonesian Rupiah valuation ranges (P10/P50/P90 Monte Carlo) free from qualitative score distortion and double-counting.",
    },
  ];

  return (
    <div className="space-y-24">
      {/* Section: Phase-4 Scientific Validation Benchmark */}
      <section id="validasi" ref={revBench.ref} className={revBench.className}>
        <div className="rounded-3xl border border-slate-800 bg-gradient-to-b from-slate-900 to-slate-950 p-6 sm:p-10">
          <div className="flex flex-wrap items-end justify-between gap-4 border-b border-slate-800 pb-6">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-xs font-mono font-semibold text-emerald-300">
                <FlaskConical className="h-3.5 w-3.5" />
                {id
                  ? "BUKTI ILMIAH & EVALUASI EKSPERIMENTAL FASE-4"
                  : "PHASE-4 EMPIRICAL & SCIENTIFIC BENCHMARK"}
              </div>
              <h2 className="mt-3 text-2xl font-extrabold text-white sm:text-3xl">
                {id
                  ? "Terbukti Secara Statistik Melampaui AI Konvensional"
                  : "Statistically Proven Superiority Over Single-Prompt LLMs"}
              </h2>
              <p className="mt-1.5 max-w-2xl text-sm text-slate-400">
                {id
                  ? "Hasil pengujian terkontrol terhadap tolok ukur pakar manusia menggunakan Quadratic Weighted Kappa (QWK), Shrout & Fleiss ICC(2,1), dan galat valuasi Rupiah."
                  : "Controlled ablation benchmark against human expert ground truth measuring Extraction F1, Quadratic Weighted Kappa (QWK), Shrout & Fleiss ICC(2,1), and IDR valuation error."}
              </p>
            </div>
            <Link
              href="/evaluation"
              className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-2.5 text-xs font-mono font-bold text-emerald-300 transition hover:bg-emerald-500 hover:text-slate-950"
            >
              <BarChart3 className="h-4 w-4" />
              {id ? "Buka Dasbor Evaluasi Riset" : "Explore Full Evaluation Suite"}
            </Link>
          </div>

          <div className="mt-8 grid grid-cols-1 gap-5 lg:grid-cols-3">
            {benchmarks.map((b, i) => (
              <div
                key={i}
                className={`rounded-2xl border p-5 transition ${
                  b.highlight
                    ? "border-emerald-500/60 bg-emerald-950/20 shadow-lg shadow-emerald-500/10"
                    : "border-slate-800 bg-slate-900/60"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-bold text-white">{b.cond}</span>
                  {b.highlight && (
                    <span className="rounded-full bg-emerald-400 px-2.5 py-0.5 font-mono text-[10px] font-black text-slate-950">
                      WINNER
                    </span>
                  )}
                </div>

                <div className="mt-5 space-y-3 text-xs font-mono">
                  <div>
                    <div className="flex justify-between text-slate-300">
                      <span>Extraction F1-Score</span>
                      <span className="font-bold text-white">{b.f1.toFixed(1)}%</span>
                    </div>
                    <div className="mt-1 h-2 w-full rounded-full bg-slate-800">
                      <div
                        className={`h-full rounded-full ${
                          b.highlight ? "bg-emerald-400" : "bg-slate-500"
                        }`}
                        style={{ width: `${b.f1}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-slate-300">
                      <span>Expert Agreement (QWK)</span>
                      <span className="font-bold text-white">{b.qwk.toFixed(3)}</span>
                    </div>
                    <div className="mt-1 h-2 w-full rounded-full bg-slate-800">
                      <div
                        className={`h-full rounded-full ${
                          b.highlight ? "bg-blue-400" : "bg-slate-500"
                        }`}
                        style={{ width: `${b.qwk * 100}%` }}
                      />
                    </div>
                  </div>

                  <div className="flex justify-between border-t border-slate-800 pt-2.5 text-slate-400">
                    <span>Shrout-Fleiss ICC(2,1):</span>
                    <strong className="text-slate-200">{b.icc.toFixed(3)}</strong>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Valuation sMAPE:</span>
                    <strong className={b.highlight ? "text-emerald-400" : "text-rose-400"}>
                      {b.smape}
                    </strong>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Engine Financial MAE:</span>
                    <strong className={b.highlight ? "text-emerald-300" : "text-slate-300"}>
                      {b.maeIdr}
                    </strong>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Section: Real-World National & Industrial Impact */}
      <section id="dampak" ref={revImpact.ref} className={revImpact.className}>
        <div className="mx-auto max-w-3xl text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3.5 py-1 text-xs font-mono font-semibold text-amber-300">
            <TrendingUp className="h-3.5 w-3.5" />
            {id ? "DAMPAK NYATA & MANFAAT EKOSISTEM" : "REAL-WORLD ECOSYSTEM IMPACT"}
          </div>
          <h2 className="mt-3 text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            {id
              ? "Dampak Strategis bagi Hilirisasi Inovasi Indonesia"
              : "Strategic Impact Across Indonesia's Innovation Ecosystem"}
          </h2>
          <p className="mt-3 text-base text-slate-400">
            {id
              ? "Dirancang khusus untuk menjawab kebutuhan nyata regulator, akademisi, industri nasional, dan lembaga pembiayaan dengan tata kelola keamanan tingkat tinggi."
              : "Purpose-built to serve national IP regulators, research universities, domestic manufacturers, and financing institutions with enterprise-grade governance."}
          </p>
        </div>

        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-2">
          {stakeholders.map((st, idx) => {
            const Icon = st.icon;
            return (
              <div
                key={idx}
                className="group rounded-3xl border border-slate-800 bg-slate-900/75 p-6 transition duration-300 hover:-translate-y-1 hover:border-blue-500/40"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-blue-500/30 bg-blue-500/10 text-blue-400">
                    <Icon className="h-6 w-6" />
                  </div>
                  <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 font-mono text-xs font-bold text-emerald-300">
                    {st.metric}
                  </span>
                </div>
                <h3 className="mt-4 text-lg font-bold text-white">{st.org}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-400">{st.impact}</p>
              </div>
            );
          })}
        </div>

        {/* Security & Governance Pillar Bar */}
        <div className="mt-8 grid grid-cols-1 gap-4 rounded-3xl border border-slate-800 bg-slate-900/50 p-6 sm:grid-cols-3">
          <div className="flex items-start gap-3">
            <Lock className="mt-0.5 h-5 w-5 shrink-0 text-emerald-400" />
            <div>
              <div className="text-sm font-bold text-white">
                {id ? "Brankas Dokumen Terenkripsi AES-256" : "AES-256 Encrypted Document Vault"}
              </div>
              <p className="mt-1 text-xs text-slate-400">
                {id
                  ? "Dokumen paten rahasia disimpan di luar web-root dengan verifikasi magic-byte dan penguncian hash SHA-256."
                  : "Confidential patent files are encrypted outside web roots with magic-byte checks and SHA-256 consent binding."}
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-blue-400" />
            <div>
              <div className="text-sm font-bold text-white">
                {id ? "Persetujuan Pakar Terikat Revisi" : "Revision-Bound Expert Approval"}
              </div>
              <p className="mt-1 text-xs text-slate-400">
                {id
                  ? "Setiap perubahan skor, bobot AHP, atau asumsi kas otomatis mengubah status persetujuan lama menjadi Stale."
                  : "Any edit to scores, AHP weights, or financial inputs automatically invalidates prior approvals to Stale."}
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <FileSearch className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
            <div>
              <div className="text-sm font-bold text-white">
                {id ? "Nol Fallback Diam-diam (Zero Silent Fallback)" : "Zero Silent Fixture Fallback"}
              </div>
              <p className="mt-1 text-xs text-slate-400">
                {id
                  ? "Persetujuan eksplisit per-dokumen; sistem tidak pernah mengganti hasil analisis dengan data contoh secara sembunyi."
                  : "Explicit per-document consent; the pipeline never silently substitutes synthetic data if an API call fails."}
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
