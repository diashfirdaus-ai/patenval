"use client";

import React from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Reveal } from "@/components/home/Reveal";

export function SectionHeading({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="max-w-2xl">
      <div className="text-sm font-medium text-blue-700">{eyebrow}</div>
      <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
        {title}
      </h2>
      {children && <p className="mt-4 text-base leading-relaxed text-slate-600">{children}</p>}
    </div>
  );
}

export function BackgroundSection({ id }: { id: boolean }) {
  const points = [
    {
      title: id ? "Paten berhenti di sertifikat" : "Patents stop at the certificate",
      desc: id
        ? "Perguruan tinggi dan lembaga riset menghasilkan invensi, tetapi kantor transfer teknologi jarang punya nilai ekonomi yang bisa diaudit dan dipercaya industri maupun perbankan."
        : "Universities and research institutes produce inventions, but technology transfer offices rarely have an auditable economic value that industry and banks can trust.",
    },
    {
      title: id ? "Skor sering dipaksa jadi Rupiah" : "Scores get forced into money",
      desc: id
        ? "Tingkat kesiapan teknologi atau skor rubrik kerap dikalikan menjadi angka uang tanpa dasar. Metode ini sulit dipertanggungjawabkan dan tidak sejalan dengan panduan WIPO."
        : "Readiness levels or rubric scores are often multiplied into currency figures without basis. That is hard to defend and does not follow WIPO guidance.",
    },
    {
      title: id ? "Klaim AI tanpa bukti" : "AI claims without evidence",
      desc: id
        ? "Model bahasa yang berdiri sendiri dapat menulis klaim yang tidak ada di dokumen. Penilaian teknologi membutuhkan kutipan yang bisa ditelusuri sampai halaman dan paragraf."
        : "A standalone language model can state claims that are not in the document. Technology assessment needs quotes traceable to the page and paragraph.",
    },
  ];

  return (
    <section id="latar-belakang" className="scroll-mt-20 py-20 sm:py-28">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal>
          <SectionHeading
            eyebrow={id ? "Latar belakang" : "Background"}
            title={
              id
                ? "Inovasi riset sulit sampai ke industri karena nilainya tidak jelas."
                : "Research innovation struggles to reach industry because its value is unclear."
            }
          />
        </Reveal>
        <div className="mt-12 grid gap-10 md:grid-cols-3">
          {points.map((p, i) => (
            <Reveal key={p.title} delay={i * 90}>
              <div className="border-t border-slate-200 pt-5">
                <div className="text-sm tabular-nums text-slate-400">0{i + 1}</div>
                <h3 className="mt-2 text-lg font-semibold text-slate-900">{p.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{p.desc}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

export function SolutionSection({ id }: { id: boolean }) {
  const outputs = [
    {
      title: id ? "Penilaian teknologi" : "Technology assessment",
      desc: id
        ? "Skor 0–100% dari rubrik 1–5, ditampilkan bersama TRL NASA 1–9 pada skala aslinya."
        : "A 0–100% score from 1–5 rubrics, shown beside the native NASA TRL 1–9 scale.",
    },
    {
      title: id ? "Kesiapan komersialisasi" : "Commercialization readiness",
      desc: id
        ? "Permintaan pasar, posisi kompetitif, regulasi, rantai pasok, dan kesiapan lisensi."
        : "Market demand, competitive position, regulation, supply chain, and licensing readiness.",
    },
    {
      title: id ? "Valuasi ekonomi (Rupiah)" : "Economic valuation (IDR)",
      desc: id
        ? "Perhitungan keuangan murni berbasis WIPO: DCF, relief-from-royalty, biaya, dan pembanding pasar."
        : "Pure WIPO-based financial calculation: DCF, relief-from-royalty, cost, and market comparables.",
    },
    {
      title: id ? "Kelengkapan bukti" : "Evidence completeness",
      desc: id
        ? "Menunjukkan indikator yang terbukti, yang belum ada, dan yang tidak berlaku, tanpa mengisi nilai nol."
        : "Shows which indicators are evidenced, missing, or not applicable, without filling in zeros.",
    },
  ];

  return (
    <section id="solusi" className="scroll-mt-20 bg-slate-50 py-20 sm:py-28">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <Reveal>
            <SectionHeading
              eyebrow={id ? "Solusi" : "Solution"}
              title={id ? "Empat hasil yang dipisahkan dengan tegas." : "Four results, kept strictly separate."}
            >
              {id
                ? "TechVal AI membaca dokumen paten, mengutip bukti, lalu memberi empat keluaran yang tidak pernah saling dikonversi."
                : "TechVal AI reads patent documents, cites evidence, and returns four outputs that are never converted into one another."}
            </SectionHeading>
          </Reveal>
          <Link
            href="/methodology"
            className="group inline-flex items-center gap-1.5 text-sm font-medium text-blue-700 hover:text-blue-800"
          >
            {id ? "Baca metodologi" : "Read the methodology"}
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </div>
        <div className="mt-12 grid gap-4 sm:grid-cols-2">
          {outputs.map((o, i) => (
            <Reveal key={o.title} delay={i * 80}>
              <div className="h-full rounded-2xl border border-slate-200 bg-white p-6 transition duration-200 hover:border-slate-300 hover:shadow-sm">
                <h3 className="text-lg font-semibold text-slate-900">{o.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{o.desc}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
