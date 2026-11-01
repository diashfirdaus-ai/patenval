"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  Play,
  ArrowRight,
  Cpu,
  Calculator,
  Microscope,
  CheckCircle2,
  ShieldCheck,
  FileText,
  Sparkles,
  RefreshCw,
} from "lucide-react";

const AGENT_NODES = [
  { id: 1, code: "DOC_INGEST", labelEn: "Vault SHA-256 & OCR Gate", labelId: "Gerbang SHA-256 & OCR", ms: 42 },
  { id: 2, code: "LOC_RESOLVE", labelEn: "Page/Para/Table Locator", labelId: "Pelacak Halaman/Tabel", ms: 118 },
  { id: 3, code: "TRL_VERIFIER", labelEn: "NASA ESTO TRL 1–9 Auditor", labelId: "Auditor TKT/TRL 1–9 NASA", ms: 164 },
  { id: 4, code: "RUBRIC_TECH", labelEn: "Technical Rubric Normalizer", labelId: "Normalisasi Rubrik Teknis", ms: 135 },
  { id: 5, code: "RUBRIC_COMM", labelEn: "Market & TKDN Readiness", labelId: "Kesiapan Pasar & TKDN", ms: 129 },
  { id: 6, code: "AHP_WEIGHT", labelEn: "Saaty AHP Eigenvector (CR≤0.10)", labelId: "Eigenvector AHP Saaty", ms: 19 },
  { id: 7, code: "WIPO_FIN_IDR", labelEn: "WIPO Deterministic DCF (IDR)", labelId: "Mesin DCF WIPO (IDR)", ms: 28 },
  { id: 8, code: "AUDIT_SEAL", labelEn: "Claim Citation & Stale Guard", labelId: "Segel Sitasi & Tata Kelola", ms: 34 },
];

function formatRupiah(val: number): string {
  const rounded = Math.round(val);
  return "Rp " + Math.abs(rounded).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

export function InteractiveSandboxPreview({ id }: { id: boolean }) {
  const [activeTab, setActiveTab] = useState<"dcf" | "agents" | "evidence">("dcf");
  const [discountRate, setDiscountRate] = useState<number>(15);
  const [attributionPct, setAttributionPct] = useState<number>(75);
  const [revMultiplier, setRevMultiplier] = useState<number>(100);
  const [activeAgentIdx, setActiveAgentIdx] = useState<number>(7);
  const [simulating, setSimulating] = useState<boolean>(false);

  // Base 5-year projections from ITENAS-PAT-2026-001 (IDR)
  const baseRevs = [1200000000, 2500000000, 4200000000, 5800000000, 7000000000];
  const baseCosts = [750000000, 1400000000, 2150000000, 2850000000, 3400000000];
  const baseCapex = [350000000, 150000000, 100000000, 100000000, 100000000];
  const baseWc = [50000000, 75000000, 90000000, 80000000, 60000000];
  const taxRate = 0.22;

  const r = discountRate / 100;
  const alpha = attributionPct / 100;
  const mult = revMultiplier / 100;

  let npvIdr = 0;
  const yearlyPv: { year: number; fcf: number; pv: number }[] = [];
  for (let t = 0; t < 5; t++) {
    const rev = baseRevs[t] * mult;
    const ebit = rev - baseCosts[t];
    const nopat = ebit >= 0 ? ebit * (1 - taxRate) : ebit;
    const rawFcf = nopat - baseCapex[t] - baseWc[t];
    const attrFcf = rawFcf * alpha;
    const pv = attrFcf / Math.pow(1 + r, t + 1);
    npvIdr += pv;
    yearlyPv.push({ year: 2026 + t, fcf: attrFcf, pv });
  }

  const runLiveAgentReplay = () => {
    if (simulating) return;
    setSimulating(true);
    setActiveAgentIdx(0);
    let step = 0;
    const timer = setInterval(() => {
      step += 1;
      if (step >= AGENT_NODES.length) {
        clearInterval(timer);
        setSimulating(false);
        setActiveAgentIdx(AGENT_NODES.length - 1);
      } else {
        setActiveAgentIdx(step);
      }
    }, 320);
  };

  useEffect(() => {
    if (activeTab === "agents") {
      runLiveAgentReplay();
    }
  }, [activeTab]);

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 sm:p-8 shadow-2xl backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-mono font-semibold text-emerald-300">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
            {id ? "SIMULATOR LANGSUNG — TANPA LOGIN" : "LIVE INTERACTIVE ENGINE — NO LOGIN REQUIRED"}
          </div>
          <h3 className="mt-2 text-xl font-bold text-white sm:text-2xl">
            {id
              ? "Uji Coba Instan: Kasus Paten IDP000089421 (ITENAS Bandung)"
              : "Instant Test Drive: Patent Case IDP000089421 (ITENAS Bandung)"}
          </h3>
          <p className="mt-1 text-xs sm:text-sm text-slate-400">
            {id
              ? "Reaktor Membran Nanokomposit Fotokatalitik TiO2-Zeolit untuk Limbah Cair Industri Tekstil (TKT/TRL 6)"
              : "Photocatalytic TiO2-Zeolite Nanocomposite Membrane Reactor for Industrial Textile Wastewater (NASA TRL 6)"}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setActiveTab("dcf")}
            className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-bold transition ${
              activeTab === "dcf"
                ? "bg-emerald-500 text-slate-950 shadow-lg shadow-emerald-500/20"
                : "border border-slate-700 bg-slate-800/80 text-slate-300 hover:bg-slate-800"
            }`}
          >
            <Calculator className="h-3.5 w-3.5" />
            {id ? "1. Kalkulator DCF WIPO" : "1. WIPO DCF Calculator"}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("agents")}
            className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-bold transition ${
              activeTab === "agents"
                ? "bg-blue-500 text-white shadow-lg shadow-blue-500/20"
                : "border border-slate-700 bg-slate-800/80 text-slate-300 hover:bg-slate-800"
            }`}
          >
            <Cpu className="h-3.5 w-3.5" />
            {id ? "2. Orkestrasi 8-Agen" : "2. 8-Agent Trace"}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("evidence")}
            className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-bold transition ${
              activeTab === "evidence"
                ? "bg-amber-400 text-slate-950 shadow-lg shadow-amber-400/20"
                : "border border-slate-700 bg-slate-800/80 text-slate-300 hover:bg-slate-800"
            }`}
          >
            <Microscope className="h-3.5 w-3.5" />
            {id ? "3. Bukti Kutipan Dokumen" : "3. Document Provenance"}
          </button>
        </div>
      </div>

      {/* Tab 1: Interactive WIPO DCF Calculator */}
      {activeTab === "dcf" && (
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="space-y-5 lg:col-span-5 rounded-2xl border border-slate-800 bg-slate-950/70 p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono uppercase tracking-wider text-emerald-400">
                {id ? "Parameter Finansial WIPO" : "WIPO Financial Parameters"}
              </span>
              <span className="rounded bg-slate-800 px-2 py-0.5 text-[11px] font-mono text-slate-300">
                WIPO Sec. 4.1
              </span>
            </div>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-200">
                  <span>{id ? "Tingkat Diskonto (r)" : "Discount Rate (r)"}</span>
                  <span className="font-mono text-emerald-400">{discountRate.toFixed(1)}%</span>
                </div>
                <input
                  type="range"
                  min={8}
                  max={25}
                  step={0.5}
                  value={discountRate}
                  onChange={(e) => setDiscountRate(Number(e.target.value))}
                  className="mt-2 h-2 w-full cursor-pointer appearance-none rounded-lg bg-slate-800 accent-emerald-400"
                />
                <div className="mt-1 flex justify-between text-[10px] font-mono text-slate-500">
                  <span>8.0% (Low Risk)</span>
                  <span>15.0% (Base)</span>
                  <span>25.0% (Venture)</span>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-200">
                  <span>{id ? "Faktor Atribusi Teknologi (α)" : "IP Attribution Factor (α)"}</span>
                  <span className="font-mono text-blue-400">{attributionPct}%</span>
                </div>
                <input
                  type="range"
                  min={25}
                  max={100}
                  step={5}
                  value={attributionPct}
                  onChange={(e) => setAttributionPct(Number(e.target.value))}
                  className="mt-2 h-2 w-full cursor-pointer appearance-none rounded-lg bg-slate-800 accent-blue-400"
                />
                <div className="mt-1 flex justify-between text-[10px] font-mono text-slate-500">
                  <span>25% (Minor)</span>
                  <span>75% (BOM Verified)</span>
                  <span>100% (Direct IP)</span>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-200">
                  <span>{id ? "Sensitivitas Proyeksi Pendapatan" : "Revenue Trajectory Sensitivity"}</span>
                  <span className="font-mono text-amber-300">{revMultiplier}%</span>
                </div>
                <input
                  type="range"
                  min={75}
                  max={130}
                  step={5}
                  value={revMultiplier}
                  onChange={(e) => setRevMultiplier(Number(e.target.value))}
                  className="mt-2 h-2 w-full cursor-pointer appearance-none rounded-lg bg-slate-800 accent-amber-400"
                />
                <div className="mt-1 flex justify-between text-[10px] font-mono text-slate-500">
                  <span>-25% Downside</span>
                  <span>100% Base</span>
                  <span>+30% Upside</span>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-slate-800/90 bg-slate-900/90 p-3.5 text-[11px] leading-relaxed text-slate-400">
              <strong className="text-slate-200">
                {id ? "Firewall Metodologis Aktif:" : "Methodological Firewall Active:"}
              </strong>{" "}
              {id
                ? "Skor teknis (78,1%) dan TKT 6 tidak pernah dimasukkan sebagai pengali uang. Valuasi dihitung murni dari arus kas bebas (FCF) terdokumentasi."
                : "Technical scores (78.1%) and TRL 6 are never used as monetary multipliers. Valuation is computed strictly from documented free cash flows."}
            </div>
          </div>

          <div className="flex flex-col justify-between rounded-2xl border border-slate-800 bg-slate-950/70 p-5 lg:col-span-7">
            <div>
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <div>
                  <div className="text-xs font-mono uppercase tracking-wider text-slate-400">
                    {id ? "Nilai Kini Bersih Indikatif (NPV WIPO)" : "Indicative Net Present Value (WIPO NPV)"}
                  </div>
                  <div className="mt-1 text-3xl font-black tracking-tight text-emerald-400 sm:text-4xl font-mono">
                    {formatRupiah(npvIdr)}
                  </div>
                </div>
                <div className="text-right font-mono text-xs text-slate-400">
                  <div>Tax τ = 22% (ID Corporate)</div>
                  <div>Horizon T = 5 Years</div>
                </div>
              </div>

              <div className="mt-6 space-y-2.5">
                <div className="text-xs font-mono uppercase tracking-wider text-slate-400">
                  {id
                    ? "Arus Kas Teratribusi & Nilai Kini per Tahun (IDR)"
                    : "Annual Attributed FCF & Present Value Breakdown (IDR)"}
                </div>
                {yearlyPv.map((row, idx) => {
                  const maxPv = 1800000000;
                  const pct = Math.max(6, Math.min(100, (row.pv / maxPv) * 100));
                  return (
                    <div key={row.year} className="space-y-1">
                      <div className="flex items-center justify-between text-xs font-mono">
                        <span className="text-slate-300">
                          Y{idx + 1} ({row.year})
                        </span>
                        <span className="text-slate-400">
                          FCF: {formatRupiah(row.fcf)} →{" "}
                          <strong className="text-emerald-300">PV: {formatRupiah(row.pv)}</strong>
                        </span>
                      </div>
                      <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-800">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-blue-500 to-emerald-400 transition-all duration-300"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 pt-4">
              <div className="text-xs text-slate-400">
                {id
                  ? "Ingin mencoba simulasi Monte Carlo 1.000 iterasi & 4 metode WIPO penuh?"
                  : "Want to run 1,000-iteration Monte Carlo & all 4 WIPO valuation methods?"}
              </div>
              <Link
                href="/valuation"
                className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-500/20 border border-emerald-500/40 px-3.5 py-2 text-xs font-bold text-emerald-300 transition hover:bg-emerald-500 hover:text-slate-950"
              >
                {id ? "Buka Studio Valuasi Penuh" : "Open Full Valuation Studio"}
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: 8-Agent LangGraph Execution Trace */}
      {activeTab === "agents" && (
        <div className="mt-6 space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-xs sm:text-sm text-slate-300">
              {id
                ? "Setiap dokumen paten melewati 8 simpul agen deterministik dengan gerbang penolakan klaim tanpa bukti."
                : "Every patent disclosure passes through 8 deterministic agent checkpoints with zero-hallucination claim gates."}
            </div>
            <button
              type="button"
              onClick={runLiveAgentReplay}
              disabled={simulating}
              className="inline-flex items-center gap-1.5 rounded-xl border border-blue-500/40 bg-blue-500/10 px-3 py-1.5 text-xs font-mono font-semibold text-blue-300 transition hover:bg-blue-500/20 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${simulating ? "animate-spin" : ""}`} />
              {simulating
                ? id
                  ? "Mengeksekusi Simpul..."
                  : "Executing Checkpoints..."
                : id
                ? "Putar Ulang Pipeline"
                : "Replay Agent Pipeline"}
            </button>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {AGENT_NODES.map((node, i) => {
              const isDone = i <= activeAgentIdx;
              const isCurrent = i === activeAgentIdx && simulating;
              return (
                <div
                  key={node.id}
                  className={`rounded-2xl border p-4 transition-all duration-300 ${
                    isCurrent
                      ? "border-blue-400 bg-blue-950/60 ring-2 ring-blue-400/30"
                      : isDone
                      ? "border-emerald-500/30 bg-slate-950/80"
                      : "border-slate-800 bg-slate-950/40 opacity-50"
                  }`}
                >
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-400">NODE 0{node.id}</span>
                    <span className={isDone ? "text-emerald-400" : "text-slate-500"}>
                      {node.ms} ms
                    </span>
                  </div>
                  <div className="mt-1.5 font-mono text-xs font-bold text-blue-300">
                    {node.code}
                  </div>
                  <div className="mt-1 text-sm font-semibold text-white">
                    {id ? node.labelId : node.labelEn}
                  </div>
                  <div className="mt-3 flex items-center gap-1.5 text-[11px] font-mono">
                    <CheckCircle2
                      className={`h-3.5 w-3.5 ${
                        isDone ? "text-emerald-400" : "text-slate-600"
                      }`}
                    />
                    <span className={isDone ? "text-emerald-300" : "text-slate-500"}>
                      {isCurrent
                        ? id
                          ? "MEMVERIFIKASI..."
                          : "VERIFYING..."
                        : isDone
                        ? "CHECKPOINT PASSED"
                        : "QUEUED"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 3: Verbatim Document Provenance */}
      {activeTab === "evidence" && (
        <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
          {[
            {
              code: "TECH_TRL_NATIVE",
              loc: "page:2 • Spec_ITENAS_001.pdf",
              score: "TRL 6 / 9 (Native Integer)",
              quote:
                "\"Pilot Validation (TRL 6): The 15 m3/day subsystem prototype was operated continuously for 450 cumulative hours in an industrial textile wastewater environment.\"",
              status: id ? "Kutipan & Angka Terverifikasi" : "Verbatim & Numeric Verified",
            },
            {
              code: "TECH_NOVELTY",
              loc: "page:1 • Spec_ITENAS_001.pdf",
              score: "4.5 / 5.0 (Norm: 87.5%)",
              quote:
                "\"The hybrid TiO2-zeolite nanocomposite membrane achieves 94.2% COD degradation and 97.8% reactive azo dye decolorization.\"",
              status: id ? "Kutipan & Angka Terverifikasi" : "Verbatim & Numeric Verified",
            },
            {
              code: "COMM_MARKET_DEMAND",
              loc: "para:1 • Market_Citarum_002.pdf",
              score: "4.0 / 5.0 (Norm: 75.0%)",
              quote:
                "\"Target Market Segment: Over 420 medium-to-large textile dyeing facilities operating in the Citarum River basin require compact tertiary wastewater retrofits.\"",
              status: id ? "Kutipan & Angka Terverifikasi" : "Verbatim & Numeric Verified",
            },
          ].map((ev) => (
            <div
              key={ev.code}
              className="flex flex-col justify-between rounded-2xl border border-slate-800 bg-slate-950/80 p-4"
            >
              <div>
                <div className="flex items-center justify-between gap-2">
                  <span className="rounded bg-blue-500/10 px-2 py-0.5 font-mono text-xs font-bold text-blue-300">
                    {ev.code}
                  </span>
                  <span className="font-mono text-[11px] text-amber-300">{ev.loc}</span>
                </div>
                <div className="mt-2 text-sm font-bold text-white">{ev.score}</div>
                <blockquote className="mt-2.5 border-l-2 border-emerald-500/60 pl-3 text-xs italic leading-relaxed text-slate-300">
                  {ev.quote}
                </blockquote>
              </div>
              <div className="mt-4 flex items-center gap-1.5 text-[11px] font-mono text-emerald-400">
                <ShieldCheck className="h-3.5 w-3.5" />
                {ev.status}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
