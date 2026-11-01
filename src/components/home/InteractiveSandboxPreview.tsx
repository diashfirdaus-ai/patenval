"use client";

import React, { useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { computeDcf, formatRupiah } from "@/lib/dcf-demo";

function Slider({
  label,
  value,
  display,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  display: string;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="block">
      <div className="flex items-baseline justify-between text-sm">
        <span className="text-slate-700">{label}</span>
        <span className="font-semibold tabular-nums text-slate-900">{display}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-2 w-full cursor-pointer accent-blue-600"
      />
    </label>
  );
}

export function InteractiveSandboxPreview({ id }: { id: boolean }) {
  const [rate, setRate] = useState(15);
  const [attribution, setAttribution] = useState(75);
  const [revenue, setRevenue] = useState(100);

  const { npv, rows } = computeDcf(rate / 100, attribution / 100, revenue / 100);
  const maxPv = Math.max(...rows.map((r) => Math.abs(r.pv)), 1);

  return (
    <div className="grid gap-8 rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 lg:grid-cols-5">
      <div className="space-y-6 lg:col-span-2">
        <Slider
          label={id ? "Tingkat diskonto" : "Discount rate"}
          value={rate}
          display={`${rate.toFixed(1)}%`}
          min={8}
          max={25}
          step={0.5}
          onChange={setRate}
        />
        <Slider
          label={id ? "Faktor atribusi teknologi" : "Technology attribution"}
          value={attribution}
          display={`${attribution}%`}
          min={25}
          max={100}
          step={5}
          onChange={setAttribution}
        />
        <Slider
          label={id ? "Proyeksi pendapatan" : "Revenue projection"}
          value={revenue}
          display={`${revenue}%`}
          min={75}
          max={130}
          step={5}
          onChange={setRevenue}
        />
        <p className="text-xs leading-relaxed text-slate-500">
          {id
            ? "Dihitung dari arus kas proyek demo ITENAS-PAT-2026-001. Skor teknis dan TRL tidak pernah dipakai sebagai pengali uang."
            : "Computed from the ITENAS-PAT-2026-001 demo cash flows. Technical scores and TRL are never used as money multipliers."}
        </p>
      </div>

      <div className="lg:col-span-3">
        <div className="text-sm text-slate-500">
          {id ? "Nilai kini bersih (DCF)" : "Net present value (DCF)"}
        </div>
        <div className="mt-1 text-3xl font-semibold tabular-nums tracking-tight text-slate-900 sm:text-4xl">
          {formatRupiah(npv)}
        </div>

        <div className="mt-6 space-y-3">
          {rows.map((r) => (
            <div key={r.year} className="flex items-center gap-3 text-sm">
              <span className="w-14 shrink-0 text-slate-500">
                {id ? "Tahun" : "Year"} {r.year}
              </span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-blue-600 transition-[width] duration-300 ease-out"
                  style={{ width: `${Math.max(2, (Math.abs(r.pv) / maxPv) * 100)}%` }}
                />
              </div>
              <span className="w-36 shrink-0 text-right tabular-nums text-slate-700">
                {formatRupiah(r.pv)}
              </span>
            </div>
          ))}
        </div>

        <Link
          href="/valuation"
          className="group mt-6 inline-flex items-center gap-1.5 text-sm font-medium text-blue-700 hover:text-blue-800"
        >
          {id ? "Buka studio valuasi lengkap" : "Open the full valuation studio"}
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </Link>
      </div>
    </div>
  );
}
