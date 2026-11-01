export interface MuseAgentSpec {
  index: number;
  node: string;
  model: string;
  endpoint: "/v1/chat/completions" | "/v1/images/generations" | "/v1/asr/transcribe";
  chatCompatible: boolean;
  name_id: string;
  name_en: string;
  role_id: string;
  role_en: string;
  advisor_prompt_id?: string;
  advisor_prompt_en?: string;
}

export const MUSE_AGENTS: MuseAgentSpec[] = [
  {
    index: 1,
    node: "intake_validation",
    model: "muse-spark-1.1",
    endpoint: "/v1/chat/completions",
    chatCompatible: true,
    name_id: "Pemeriksa Berkas Masuk",
    name_en: "Intake Validator",
    role_id: "Memeriksa kelengkapan dokumen paten, klaim, dan bagian teks sebelum dinilai.",
    role_en: "Checks that patent files, claims, and text sections are complete before scoring.",
    advisor_prompt_id: "Fokus pada kelengkapan dokumen, bagian yang tersedia, dan cakupan bukti.",
    advisor_prompt_en: "Focus on document completeness, available sections, and evidence coverage.",
  },
  {
    index: 2,
    node: "evidence_extraction",
    model: "muse-spark-1.3",
    endpoint: "/v1/chat/completions",
    chatCompatible: true,
    name_id: "Penarik Bukti & Kutipan",
    name_en: "Evidence & Quote Extractor",
    role_id: "Menarik kutipan langsung beserta penanda lokasi [page:N] atau [para:N] dari dokumen.",
    role_en: "Pulls verbatim quotes with [page:N] or [para:N] locators from the source documents.",
    advisor_prompt_id: "Jawab dengan mengutamakan kutipan langsung dan penanda lokasi [page:N] atau [para:N].",
    advisor_prompt_en: "Answer by foregrounding verbatim quotes and [page:N] or [para:N] locators.",
  },
  {
    index: 3,
    node: "ip_patent_analysis",
    model: "muse-spark-1.2",
    endpoint: "/v1/chat/completions",
    chatCompatible: true,
    name_id: "Pemeriksa Klaim Paten",
    name_en: "Patent Claim Analyst",
    role_id: "Menelaah kebaruan teknis, cakupan klaim, dan posisi perlindungan kekayaan intelektual.",
    role_en: "Reviews technical novelty, claim scope, and intellectual property protection.",
    advisor_prompt_id: "Fokus pada status paten, kebaruan teknis, dan kekuatan perlindungan klaim.",
    advisor_prompt_en: "Focus on patent status, technical novelty, and claim protection strength.",
  },
  {
    index: 4,
    node: "market_intelligence",
    model: "muse-spark-1.3-contributor",
    endpoint: "/v1/chat/completions",
    chatCompatible: true,
    name_id: "Penelaah Pasar & Adopsi",
    name_en: "Market & Adoption Analyst",
    role_id: "Memetakan kebutuhan industri sasaran, kesiapan mitra manufaktur, dan daya serap pasar.",
    role_en: "Maps target industry demand, manufacturing partner readiness, and market adoption.",
    advisor_prompt_id: "Fokus pada pasar sasaran, mitra industri, dan kesiapan adopsi komersial.",
    advisor_prompt_en: "Focus on target market, industrial partners, and commercial adoption readiness.",
  },
  {
    index: 5,
    node: "technical_trl_assessment",
    model: "muse-wonder-1.0",
    endpoint: "/v1/chat/completions",
    chatCompatible: true,
    name_id: "Penilai TRL Ilmiah",
    name_en: "Scientific TRL Assessor",
    role_id: "Memverifikasi pemenuhan kriteria keluar NASA TRL 1–9 berdasarkan bukti uji yang sah.",
    role_en: "Verifies NASA TRL 1–9 exit criteria against resolved test evidence.",
    advisor_prompt_id: "Fokus pada bukti pemenuhan kriteria keluar NASA TRL dan batas kematangan teknis.",
    advisor_prompt_en: "Focus on NASA TRL exit criteria evidence and technical maturity limits.",
  },
  {
    index: 6,
    node: "commercialization_pathway",
    model: "muse-spark-1.2-contributor",
    endpoint: "/v1/chat/completions",
    chatCompatible: true,
    name_id: "Perancang Jalur Lisensi",
    name_en: "Licensing Pathway Planner",
    role_id: "Menyusun jalur lisensi WIPO dan memisahkan kesiapan komersial dari nilai Rupiah.",
    role_en: "Plans the WIPO licensing pathway and keeps readiness separate from Rupiah value.",
    advisor_prompt_id: "Fokus pada jalur lisensi WIPO, struktur royalti, dan pemisahan skor dari nilai uang.",
    advisor_prompt_en: "Focus on WIPO licensing pathways, royalty structure, and keeping scores separate from money.",
  },
  {
    index: 7,
    node: "risk_synthesis",
    model: "muse-image-1.0",
    endpoint: "/v1/images/generations",
    chatCompatible: false,
    name_id: "Pembuat Ilustrasi Teknis",
    name_en: "Technical Figure Generator",
    role_id: "Menghasilkan ilustrasi skema reaktor dan diagram alir proses.",
    role_en: "Generates reactor schematics and process flow illustrations.",
  },
  {
    index: 8,
    node: "report_compilation",
    model: "muse-voice-transcribe-1.0",
    endpoint: "/v1/asr/transcribe",
    chatCompatible: false,
    name_id: "Perekam Catatan Suara Penguji",
    name_en: "Reviewer Voice Transcriber",
    role_id: "Mengubah rekaman suara penguji atau inventor menjadi catatan teks laporan.",
    role_en: "Transcribes reviewer or inventor voice notes into text for the report.",
  },
];

export const NODE_MODEL_MAP: Record<string, string> = Object.fromEntries(
  MUSE_AGENTS.map((a) => [a.node, a.model])
);
