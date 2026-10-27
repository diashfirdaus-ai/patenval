"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import type { LanguageCode } from "./api-types";

export const translations = {
  en: {
    appName: "TechVal AI",
    appSubtitle: "Assess and value your technology",
    nav: {
      portfolio: "Home",
      submission: "Upload Documents",
      pipeline: "AI Analysis",
      assessment: "Technology Score",
      commercialization: "Market Readiness",
      valuation: "Value Estimate",
      governance: "Expert Review",
      reports: "Reports",
      methodology: "How It Works",
      evaluation: "Quality Check",
      groupMain: "Get started",
      groupResults: "Results",
      groupMore: "More",
    },
    fourOutputs: {
      bannerTitle: "Four separate results. Scores are never converted into money.",
      techAssessment: "Technology Score",
      commReadiness: "Market Readiness",
      econValuation: "Estimated Value",
      evidenceCompleteness: "Documents Completeness",
      techHint: "How mature the technology is",
      commHint: "How ready it is for the market",
      econHint: "Estimated worth in Rupiah",
      evidenceHint: "How much supporting evidence we found",
      provisionalBadge: "Preliminary",
      verifiedBadge: "Methodology Verified",
      demoBadge: "Demo Data",
      scoreConversionNotice:
        "Scores and TRL levels are never converted into monetary values, royalty rates, or discount rates.",
    },
    common: {
      activeTechnology: "Technology",
      role: "Role",
      language: "Language",
      save: "Save Changes",
      cancel: "Cancel",
      loading: "Loading...",
      errorPrefix: "Something went wrong:",
      observed: "Found",
      missing: "Missing",
      notApplicable: "Not Applicable",
      draftWatermark: "Draft",
      approvedStatus: "Approved by expert",
      staleStatus: "Needs re-review",
      advanced: "Advanced options",
      showMore: "Show more",
      showLess: "Show less",
    },
  },
  id: {
    appName: "TechVal AI",
    appSubtitle: "Nilai dan taksir teknologi Anda",
    nav: {
      portfolio: "Beranda",
      submission: "Unggah Dokumen",
      pipeline: "Analisis AI",
      assessment: "Skor Teknologi",
      commercialization: "Kesiapan Pasar",
      valuation: "Perkiraan Nilai",
      governance: "Tinjauan Pakar",
      reports: "Laporan",
      methodology: "Cara Kerja",
      evaluation: "Cek Kualitas",
      groupMain: "Mulai",
      groupResults: "Hasil",
      groupMore: "Lainnya",
    },
    fourOutputs: {
      bannerTitle: "Empat hasil terpisah. Skor tidak pernah dikonversi menjadi uang.",
      techAssessment: "Skor Teknologi",
      commReadiness: "Kesiapan Pasar",
      econValuation: "Perkiraan Nilai",
      evidenceCompleteness: "Kelengkapan Dokumen",
      techHint: "Seberapa matang teknologinya",
      commHint: "Seberapa siap masuk ke pasar",
      econHint: "Perkiraan nilai dalam Rupiah",
      evidenceHint: "Seberapa banyak bukti pendukung ditemukan",
      provisionalBadge: "Sementara",
      verifiedBadge: "Metodologi Terverifikasi",
      demoBadge: "Data Demo",
      scoreConversionNotice:
        "Skor penilaian dan tingkat TKT/TRL tidak pernah dikonversi menjadi nilai moneter, tarif royalti, atau tingkat diskonto.",
    },
    common: {
      activeTechnology: "Teknologi",
      role: "Peran",
      language: "Bahasa",
      save: "Simpan Perubahan",
      cancel: "Batal",
      loading: "Memuat...",
      errorPrefix: "Terjadi kesalahan:",
      observed: "Ditemukan",
      missing: "Belum Ada",
      notApplicable: "Tidak Berlaku",
      draftWatermark: "Draf",
      approvedStatus: "Disetujui pakar",
      staleStatus: "Perlu ditinjau ulang",
      advanced: "Opsi lanjutan",
      showMore: "Tampilkan lebih banyak",
      showLess: "Tampilkan lebih sedikit",
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
