"use client";

import React from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Reveal } from "@/components/home/Reveal";
import { SectionHeading } from "@/components/home/LandingSections";

export function ImpactSection({ id }: { id: boolean }) {
  const groups = [
    {
      who: id ? "Kantor transfer teknologi" : "Technology transfer offices",
      what: id
        ? "Mengubah hasil riset menjadi dokumen penilaian yang siap dibawa ke calon mitra lisensi."
        : "Turns research output into an assessment ready to bring to licensing partners.",
    },
    {
      who: id ? "Pemeriksa dan pengelola KI" : "IP examiners and managers",
      what: id
        ? "Setiap skor punya kutipan dengan lokasi halaman atau paragraf, sehingga mudah diperiksa ulang."
        : "Every score carries a quote with its page or paragraph, so it is easy to re-check.",
    },
    {
      who: id ? "Industri" : "Industry",
      what: id
        ? "Melihat kesiapan teknis dan pasar sebelum menandatangani niat lisensi."
        : "Sees technical and market readiness before signing a licensing intent.",
    },
    {
      who: id ? "Pembiaya dan auditor" : "Funders and auditors",
      what: id
        ? "Menerima rentang nilai dalam Rupiah dari perhitungan yang bisa direproduksi."
        : "Receives a value range in Rupiah from a calculation that can be reproduced.",
    },
  ];

  return (
    <section id="dampak" className="scroll-mt-20 py-20 sm:py-28">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal>
          <SectionHeading
            eyebrow={id ? "Dampak" : "Impact"}
            title={id ? "Siapa yang terbantu." : "Who it helps."}
          />
        </Reveal>
        <dl className="mt-12 divide-y divide-slate-200 border-y border-slate-200">
          {groups.map((g, i) => (
            <Reveal key={g.who} delay={i * 70}>
              <div className="grid gap-2 py-6 md:grid-cols-3 md:gap-8">
                <dt className="text-base font-semibold text-slate-900">{g.who}</dt>
                <dd className="text-base leading-relaxed text-slate-600 md:col-span-2">{g.what}</dd>
              </div>
            </Reveal>
          ))}
        </dl>
      </div>
    </section>
  );
}

const BENCH = [
  { key: "llm", f1: 0.615, qwk: 0.178 },
  { key: "agent", f1: 0.941, qwk: 0.808 },
  { key: "full", f1: 1.0, qwk: 1.0 },
];

export function ValidationSection({ id }: { id: boolean }) {
  const labels: Record<string, string> = {
    llm: id ? "LLM tunggal" : "Single LLM",
    agent: id ? "Multi-agen" : "Multi-agent",
    full: id ? "Multi-agen + validasi" : "Multi-agent + validation",
  };

  return (
    <section id="validasi" className="scroll-mt-20 bg-slate-50 py-20 sm:py-28">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal>
          <SectionHeading
            eyebrow={id ? "Validasi" : "Validation"}
            title={id ? "Hasil uji pada data demonstrasi." : "Results on demonstration data."}
          >
            {id
              ? "Angka berikut berasal dari dataset sintetis untuk memverifikasi alur dan metrik. Ini bukan klaim akurasi di dunia nyata."
              : "These numbers come from a synthetic dataset used to verify the pipeline and metrics. They are not a real-world accuracy claim."}
          </SectionHeading>
        </Reveal>
        <Reveal delay={100}>
          <div className="mt-12 space-y-6 rounded-2xl border border-slate-200 bg-white p-6 sm:p-8">
            {BENCH.map((b) => (
              <div key={b.key} className="grid items-center gap-3 md:grid-cols-4">
                <div className="text-sm font-medium text-slate-900">{labels[b.key]}</div>
                <Bar label="F1" value={b.f1} />
                <Bar label="QWK" value={b.qwk} />
                <div />
              </div>
            ))}
          </div>
        </Reveal>
        <Link
          href="/evaluation"
          className="group mt-6 inline-flex items-center gap-1.5 text-sm font-medium text-blue-700 hover:text-blue-800"
        >
          {id ? "Lihat evaluasi lengkap" : "See the full evaluation"}
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </Link>
      </div>
    </section>
  );
}

function Bar({ label, value }: { label: string; value: number }) {
  return (
    <div className="md:col-span-1">
      <div className="flex justify-between text-xs text-slate-500">
        <span>{label}</span>
        <span className="tabular-nums text-slate-800">{value.toFixed(3)}</span>
      </div>
      <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-blue-600" style={{ width: `${value * 100}%` }} />
      </div>
    </div>
  );
}
