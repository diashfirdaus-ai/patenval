"use client";

import React from "react";
import { useAppState } from "@/lib/i18n";
import { AdvisorChat } from "@/components/advisor/AdvisorChat";
import { AgentRoster } from "@/components/advisor/AgentRoster";

export default function AdvisorPage() {
  const { lang } = useAppState();
  const id = lang === "id";

  return (
    <div className="mx-auto max-w-4xl space-y-10">
      <div>
        <div className="text-sm font-medium text-blue-700">
          SINC LAB × ITENAS × Muse (Meta)
        </div>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
          {id ? "Penasihat AI & 8 Agen Muse" : "AI Advisor & 8 Muse Agents"}
        </h1>
        <p className="mt-2 text-base leading-relaxed text-slate-600">
          {id
            ? "Penelitian dan sistem hasil kerja sama SINC LAB, ITENAS, dan Muse (Meta). Pilih salah satu agen untuk menjawab pertanyaan Anda: setiap agen hanya memakai data kasus, wajib mengutip lokasi bukti, dan tidak mengubah skor menjadi Rupiah."
            : "A research and system collaboration between SINC LAB, ITENAS, and Muse (Meta). Pick an agent to answer your question: each agent uses only the case data, cites evidence locators, and never converts scores into Rupiah."}
        </p>
      </div>

      <AdvisorChat />

      <div className="space-y-4">
        <h2 className="text-2xl font-semibold text-slate-900 sm:text-3xl">
          {id ? "8 Agen Muse dan Tugasnya" : "The 8 Muse Agents and Their Roles"}
        </h2>
        <p className="text-base text-slate-600">
          {id
            ? "Delapan model Muse yang bekerja pada penilaian teknologi dan komersialisasi paten:"
            : "The eight Muse models working across technology assessment and patent commercialization:"}
        </p>
        <AgentRoster id={id} />
      </div>
    </div>
  );
}
