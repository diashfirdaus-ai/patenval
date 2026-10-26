"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import type { LanguageCode } from "./api-types";

export const translations = {
  en: {
    appName: "TechVal AI",
    appSubtitle: "Scientific Technology Assessment & WIPO Economic Valuation Platform",
    nav: {
      portfolio: "1. Portfolio Overview",
      submission: "2. Submission & Vault",
      pipeline: "3. Multi-Agent Pipeline",
      assessment: "4. Tech Assessment & TRL",
      commercialization: "5. Commercialization & AHP",
      valuation: "6. Valuation Studio (IDR)",
      governance: "7. Expert Review & Audit",
      reports: "8. Bilingual PDF Reports",
      methodology: "9. Scientific Methodology",
      evaluation: "10. Research Evaluation",
    },
    fourOutputs: {
      bannerTitle: "Strict Four-Output Separation Architecture (Score-to-IDR Conversion Prohibited)",
      techAssessment: "1. Technology Assessment",
      commReadiness: "2. Commercialization Readiness",
      econValuation: "3. Economic Valuation (IDR)",
      evidenceCompleteness: "4. Evidence Completeness",
      provisionalBadge: "Provisional Assessment",
      verifiedBadge: "Methodology Verified",
      demoBadge: "Synthetic / Demo Data",
      scoreConversionNotice:
        "Scores and TRL levels are never converted into monetary values, royalty rates, or discount rates.",
    },
    common: {
      activeTechnology: "Active Technology",
      role: "Active Role",
      language: "Language",
      save: "Save & Create Revision",
      cancel: "Cancel",
      loading: "Loading scientific workspace...",
      errorPrefix: "Operation failed:",
      observed: "Observed",
      missing: "Missing",
      notApplicable: "Not Applicable",
      draftWatermark: "DRAFT — UNAPPROVED / PROVISIONAL",
      approvedStatus: "Expert Approved (Current Revision)",
      staleStatus: "STALE — Material Change After Approval",
    },
  },
  id: {
    appName: "TechVal AI",
    appSubtitle: "Platform Penilaian Teknologi Ilmiah & Valuasi Ekonomi WIPO",
    nav: {
      portfolio: "1. Ringkasan Portofolio",
      submission: "2. Pengajuan & Brankas Dokumen",
      pipeline: "3. Pipeline Multi-Agen",
      assessment: "4. Penilaian Teknologi & TKT",
      commercialization: "5. Komersialisasi & AHP",
      valuation: "6. Studio Valuasi (IDR)",
      governance: "7. Tinjauan Pakar & Audit",
      reports: "8. Laporan PDF Dwibahasa",
      methodology: "9. Metodologi Ilmiah",
      evaluation: "10. Evaluasi Riset (Fase 4)",
    },
    fourOutputs: {
      bannerTitle: "Arsitektur Pemisahan Empat Keluaran Ketat (Konversi Skor ke IDR Dilarang)",
      techAssessment: "1. Penilaian Teknologi",
      commReadiness: "2. Kesiapan Komersialisasi",
      econValuation: "3. Valuasi Ekonomi (IDR)",
      evidenceCompleteness: "4. Kelengkapan Bukti",
      provisionalBadge: "Penilaian Sementara",
      verifiedBadge: "Metodologi Terverifikasi",
      demoBadge: "Data Sintetis / Demo",
      scoreConversionNotice:
        "Skor penilaian dan tingkat TKT/TRL tidak pernah dikonversi menjadi nilai moneter, tarif royalti, atau tingkat diskonto.",
    },
    common: {
      activeTechnology: "Teknologi Aktif",
      role: "Peran Aktif",
      language: "Bahasa",
      save: "Simpan & Buat Revisi Baru",
      cancel: "Batal",
      loading: "Memuat ruang kerja ilmiah...",
      errorPrefix: "Operasi gagal:",
      observed: "Teramati",
      missing: "Belum Tersedia",
      notApplicable: "Tidak Berlaku",
      draftWatermark: "DRAF — BELUM DISETUJUI / SEMENTARA",
      approvedStatus: "Disetujui Pakar (Revisi Saat Ini)",
      staleStatus: "KEDALUWARSA (STALE) — Ada Perubahan Material",
    },
  },
};

interface AppContextState {
  lang: LanguageCode;
  setLang: (lang: LanguageCode) => void;
  t: (typeof translations)["en"];
  selectedTechId: string | null;
  setSelectedTechId: (id: string | null) => void;
}

const AppContext = createContext<AppContextState | null>(null);

export function AppStateProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<LanguageCode>("en");
  const [selectedTechId, setSelectedTechIdState] = useState<string | null>(null);

  useEffect(() => {
    const savedLang = window.localStorage.getItem("techval_lang") as LanguageCode | null;
    if (savedLang === "en" || savedLang === "id") {
      setLangState(savedLang);
    }
    const savedTech = window.localStorage.getItem("techval_selected_tech_id");
    if (savedTech) {
      setSelectedTechIdState(savedTech);
    }
  }, []);

  const setLang = (next: LanguageCode) => {
    setLangState(next);
    window.localStorage.setItem("techval_lang", next);
  };

  const setSelectedTechId = (id: string | null) => {
    setSelectedTechIdState(id);
    if (id) {
      window.localStorage.setItem("techval_selected_tech_id", id);
    } else {
      window.localStorage.removeItem("techval_selected_tech_id");
    }
  };

  return React.createElement(
    AppContext.Provider,
    {
      value: {
        lang,
        setLang,
        t: translations[lang],
        selectedTechId,
        setSelectedTechId,
      },
    },
    children
  );
}

export function useAppState() {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error("useAppState must be used within AppStateProvider");
  }
  return ctx;
}
