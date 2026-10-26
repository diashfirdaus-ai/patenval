import fs from "fs";
import os from "os";
import path from "path";
import crypto from "crypto";

function resolveRuntimeDir(): string {
  if (process.env.TECHVAL_DATA_DIR) {
    return path.resolve(process.env.TECHVAL_DATA_DIR);
  }
  const localCandidate = path.resolve(process.cwd(), "..", ".runtime");
  try {
    fs.mkdirSync(localCandidate, { recursive: true });
    return localCandidate;
  } catch {
    // Fallback for read-only serverless environments (e.g. Vercel / AWS Lambda)
    const tmpCandidate = path.join(os.tmpdir(), "techval-runtime");
    fs.mkdirSync(tmpCandidate, { recursive: true });
    return tmpCandidate;
  }
}

const RUNTIME_DIR = resolveRuntimeDir();
const VAULT_DIR = path.join(RUNTIME_DIR, "vault");
const STATE_FILE = path.join(RUNTIME_DIR, "nextjs_web_state.json");

export function getVaultDir(): string {
  ensureDirs();
  return VAULT_DIR;
}

function ensureDirs() {
  if (!fs.existsSync(RUNTIME_DIR)) fs.mkdirSync(RUNTIME_DIR, { recursive: true });
  if (!fs.existsSync(VAULT_DIR)) fs.mkdirSync(VAULT_DIR, { recursive: true });
}

export function sha256Hex(data: Buffer | string): string {
  return crypto.createHash("sha256").update(data).digest("hex");
}

const VAULT_KEY = crypto
  .createHash("sha256")
  .update(process.env.VAULT_ENCRYPTION_KEY || "techval-local-vault-secret-key-2026")
  .digest();

export function encryptVaultBuffer(plain: Buffer): Buffer {
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv("aes-256-gcm", VAULT_KEY, iv);
  const enc = Buffer.concat([cipher.update(plain), cipher.final()]);
  const tag = cipher.getAuthTag();
  return Buffer.concat([iv, tag, enc]);
}

export function decryptVaultBuffer(packed: Buffer): Buffer {
  const iv = packed.subarray(0, 12);
  const tag = packed.subarray(12, 28);
  const enc = packed.subarray(28);
  const decipher = crypto.createDecipheriv("aes-256-gcm", VAULT_KEY, iv);
  decipher.setAuthTag(tag);
  return Buffer.concat([decipher.update(enc), decipher.final()]);
}

export function formatIdrServer(val: number | null | undefined): string {
  if (val === null || val === undefined || Number.isNaN(val)) return "Unavailable";
  const rounded = Math.round(val);
  const sign = rounded < 0 ? "-" : "";
  const formatted = Math.abs(rounded)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${sign}Rp ${formatted}`;
}

export const SAATY_RI_TABLE: Record<number, number> = {
  1: 0.0,
  2: 0.0,
  3: 0.58,
  4: 0.9,
  5: 1.12,
  6: 1.24,
  7: 1.32,
  8: 1.41,
  9: 1.45,
  10: 1.49,
};

export function validateAndSolveAhp(codes: string[], matrix: number[][]) {
  const n = matrix.length;
  if (n === 0 || codes.length !== n) {
    throw new Error("Matrix dimension must match indicator_codes length.");
  }
  for (let i = 0; i < n; i++) {
    if (matrix[i].length !== n) throw new Error("AHP matrix must be square.");
    if (Math.abs(matrix[i][i] - 1.0) > 1e-3) {
      throw new Error(`Diagonal entry (${i},${i}) must equal 1.0.`);
    }
    for (let j = 0; j < n; j++) {
      const aij = Number(matrix[i][j]);
      const aji = Number(matrix[j][i]);
      if (!(aij > 0) || Number.isNaN(aij)) {
        throw new Error(`Entry (${i},${j}) must be strictly positive.`);
      }
      if (Math.abs(aij * aji - 1.0) > 0.05) {
        throw new Error(
          `Reciprocity violated at (${i},${j}): ${aij} * ${aji} != 1.0`
        );
      }
    }
  }

  // Power iteration for principal right eigenvector
  let v = Array(n).fill(1 / n);
  for (let iter = 0; iter < 200; iter++) {
    const next = Array(n).fill(0);
    for (let i = 0; i < n; i++) {
      let s = 0;
      for (let j = 0; j < n; j++) s += matrix[i][j] * v[j];
      next[i] = s;
    }
    const sum = next.reduce((a, b) => a + b, 0);
    v = next.map((x) => x / sum);
  }

  let lambdaMax = 0;
  for (let i = 0; i < n; i++) {
    let rowSum = 0;
    for (let j = 0; j < n; j++) rowSum += matrix[i][j] * v[j];
    lambdaMax += rowSum / v[i];
  }
  lambdaMax /= n;

  const ci = n > 1 ? (lambdaMax - n) / (n - 1) : 0.0;
  const ri = SAATY_RI_TABLE[n] ?? 1.49;
  const cr = ri > 0 ? ci / ri : 0.0;
  const weights: Record<string, number> = {};
  codes.forEach((c, idx) => {
    weights[c] = Number(v[idx].toFixed(6));
  });

  return {
    dimension_size: n,
    lambda_max: Number(lambdaMax.toFixed(6)),
    consistency_index: Number(ci.toFixed(6)),
    random_index: ri,
    consistency_ratio: Number(cr.toFixed(6)),
    is_consistent: cr <= 0.1,
    weights,
  };
}

export function calculateDcfServer(
  inputs: Record<string, any>,
  mcSeed = 20260417,
  mcIterations = 500
) {
  const revs: number[] = inputs.revenues_idr || [];
  const costs: number[] = inputs.operating_costs_idr || [];
  const capex: number[] = inputs.capex_idr || [];
  const wc: number[] = inputs.working_capital_changes_idr || [];
  const taxRate = Number(inputs.tax_rate ?? 0.22);
  const r = Number(inputs.discount_rate ?? 0.15);
  const attrMode = inputs.attribution_mode || "documented_attribution_factor";
  const alpha =
    attrMode === "direct_cash_flows"
      ? 1.0
      : Number(inputs.attribution_factor ?? 0.75);
  const riskMode = inputs.risk_treatment_mode || "in_discount_rate";

  const annualBreakdown: any[] = [];
  let npv = 0;
  for (let t = 0; t < revs.length; t++) {
    const ebit = revs[t] - (costs[t] || 0);
    const nopat = ebit >= 0 ? ebit * (1 - taxRate) : ebit;
    const rawFcf = nopat - (capex[t] || 0) - (wc[t] || 0);
    const attrFcf = rawFcf * alpha;
    const pv = attrFcf / Math.pow(1 + r, t + 1);
    npv += pv;
    annualBreakdown.push({
      year: t + 1,
      revenue_idr: revs[t],
      operating_cost_idr: costs[t] || 0,
      ebit_idr: ebit,
      nopat_idr: Math.round(nopat),
      unattributed_fcf_idr: Math.round(rawFcf),
      attributed_fcf_idr: Math.round(attrFcf),
      present_value_idr: Math.round(pv),
    });
  }

  // Sensitivity
  const calcWith = (revMult: number, rDelta: number, alphaMult: number) => {
    let sum = 0;
    const rAdj = Math.max(-0.9, r + rDelta);
    const aAdj = Math.min(1.0, Math.max(0.01, alpha * alphaMult));
    for (let t = 0; t < revs.length; t++) {
      const ebit = revs[t] * revMult - (costs[t] || 0);
      const nopat = ebit >= 0 ? ebit * (1 - taxRate) : ebit;
      const fcf = (nopat - (capex[t] || 0) - (wc[t] || 0)) * aAdj;
      sum += fcf / Math.pow(1 + rAdj, t + 1);
    }
    return Math.round(sum);
  };

  const sensitivity = [
    {
      parameter: "revenue_trajectory",
      label: "Annual Revenue Trajectory (-15% / +15%)",
      downside_npv_idr: calcWith(0.85, 0, 1.0),
      base_npv_idr: Math.round(npv),
      upside_npv_idr: calcWith(1.15, 0, 1.0),
    },
    {
      parameter: "discount_rate",
      label: "Discount Rate r (+300 bps / -300 bps)",
      downside_npv_idr: calcWith(1.0, 0.03, 1.0),
      base_npv_idr: Math.round(npv),
      upside_npv_idr: calcWith(1.0, -0.03, 1.0),
    },
    {
      parameter: "attribution_factor",
      label: "IP Attribution Factor (-10% / +10%)",
      downside_npv_idr: calcWith(1.0, 0, 0.9),
      base_npv_idr: Math.round(npv),
      upside_npv_idr: calcWith(1.0, 0, 1.1),
    },
  ];

  // Seeded Mulberry32 PRNG for reproducible Monte Carlo
  let seed = mcSeed >>> 0;
  const rand = () => {
    seed = (seed + 0x6d2b79f5) >>> 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const samples: number[] = [];
  for (let i = 0; i < mcIterations; i++) {
    const revMult = 0.85 + rand() * 0.3;
    const rDelta = (rand() - 0.5) * 0.04;
    samples.push(calcWith(revMult, rDelta, 1.0));
  }
  samples.sort((a, b) => a - b);
  const p10 = samples[Math.floor(mcIterations * 0.1)];
  const p50 = samples[Math.floor(mcIterations * 0.5)];
  const p90 = samples[Math.floor(mcIterations * 0.9)];
  const mean = samples.reduce((a, b) => a + b, 0) / mcIterations;
  const variance =
    samples.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / mcIterations;

  const doubleCount = riskMode === "both";
  return {
    npv_idr: Math.round(npv),
    annual_breakdown: annualBreakdown,
    sensitivity,
    monte_carlo: {
      seed: mcSeed,
      iterations: mcIterations,
      p10_idr: p10,
      p50_idr: p50,
      p90_idr: p90,
      mean_idr: Math.round(mean),
      std_idr: Math.round(Math.sqrt(variance)),
    },
    double_counting_flagged: doubleCount,
    double_counting_warning: doubleCount
      ? "WIPO Section 4.3 Warning: Risk is applied in both cash flows and discount rate (potential double counting)."
      : null,
  };
}

function buildInitialState() {
  const now = new Date().toISOString();
  const techId = "tech-itenas-2026-001";
  const revId = "rev-itenas-2026-001";
  const runId = "run-itenas-2026-001";
  const doc1Id = "doc-itenas-spec-001";
  const doc2Id = "doc-itenas-mkt-002";

  const indicators = [
    {
      id: "ind-1",
      code: "TECH_TRL_NATIVE",
      dimension: "technology_assessment",
      name_en: "NASA Technology Readiness Level (Native 1-9)",
      name_id: "Tingkat Kesiapterapan Teknologi NASA (Skala Asli 1-9)",
      description_en:
        "Evaluated on the native 1-9 NASA ESTO / ISO 16290:2013 integer scale based on verified subsystem/system test evidence.",
      description_id:
        "Dievaluasi pada skala bulat asli 1-9 NASA ESTO / ISO 16290:2013 berdasarkan bukti pengujian subsistem/sistem.",
      scale_type: "1-9_trl",
      min_score: 1,
      max_score: 9,
      is_patent_specific: false,
      origin_classification: "directly_sourced",
      reference_id: "ref-nasa",
      source_locator: "NASA ESTO TRL 1-9 Definitions, Levels 1-9",
      cross_domain_note:
        "Adapted from aerospace systems engineering to chemical/membrane reactor prototypes.",
      rubric_levels: { "6": "Subsystem/system prototype demonstrated in a relevant environment." },
      default_provisional_weight: 0.2,
    },
    {
      id: "ind-2",
      code: "TECH_NOVELTY",
      dimension: "technology_assessment",
      name_en: "Technical Novelty & Prior-Art Differentiation",
      name_id: "Kebaruan Teknis & Diferensiasi Prior-Art",
      description_en:
        "Degree of verifiable technical differentiation over existing state-of-the-art processes.",
      description_id:
        "Tingkat diferensiasi teknis yang terverifikasi terhadap proses state-of-the-art yang ada.",
      scale_type: "1-5",
      min_score: 1,
      max_score: 5,
      is_patent_specific: false,
      origin_classification: "adapted",
      reference_id: "ref-harhoff",
      source_locator: "Harhoff et al. (2003), Section 2, pp. 1345-1348",
      cross_domain_note: "Adapted to cover both patented and unpatented R&D disclosures.",
      rubric_levels: {},
      default_provisional_weight: 0.2,
    },
    {
      id: "ind-3",
      code: "TECH_VALIDATION",
      dimension: "technology_assessment",
      name_en: "Empirical Validation & Repeatability",
      name_id: "Validasi Empiris & Keterulangan Pengujian",
      description_en: "Completeness and duration of quantitative performance testing.",
      description_id: "Kelengkapan dan durasi pengujian kinerja kuantitatif.",
      scale_type: "1-5",
      min_score: 1,
      max_score: 5,
      is_patent_specific: false,
      origin_classification: "adapted",
      reference_id: "ref-nasa",
      source_locator: "NASA ESTO TRL Exit Criteria, Levels 4-7",
      cross_domain_note: null,
      rubric_levels: {},
      default_provisional_weight: 0.2,
    },
    {
      id: "ind-4",
      code: "TECH_SCALABILITY",
      dimension: "technology_assessment",
      name_en: "Manufacturing & Engineering Scalability",
      name_id: "Skalabilitas Manufaktur & Rekayasa",
      description_en: "Readiness for modular scale-up and domestic fabrication (TKDN).",
      description_id: "Kesiapan untuk peningkatan skala modular dan fabrikasi dalam negeri (TKDN).",
      scale_type: "1-5",
      min_score: 1,
      max_score: 5,
      is_patent_specific: false,
      origin_classification: "proposed",
      reference_id: null,
      source_locator: "Proposed Rubric Indicator — Provisional until Expert Calibration",
      cross_domain_note: null,
      rubric_levels: {},
      default_provisional_weight: 0.15,
    },
    {
      id: "ind-5",
      code: "TECH_PATENT_STRENGTH",
      dimension: "technology_assessment",
      name_en: "Contextual Patent Scope & Citation Signal",
      name_id: "Cakupan Klaim & Sinyal Sitasi Paten Kontekstual",
      description_en:
        "Contextual breadth of independent claims and family/citation indicators (marked N/A for non-patent IP).",
      description_id:
        "Keluasan kontekstual klaim independen dan indikator keluarga/sitasi paten (N/A untuk non-paten).",
      scale_type: "1-5",
      min_score: 1,
      max_score: 5,
      is_patent_specific: true,
      origin_classification: "adapted",
      reference_id: "ref-harhoff",
      source_locator: "Harhoff et al. (2003), Sections 2 & 4, pp. 1345-1359",
      cross_domain_note: "Treated strictly as a contextual signal, never a monetary multiplier.",
      rubric_levels: {},
      default_provisional_weight: 0.15,
    },
    {
      id: "ind-6",
      code: "TECH_SYSTEM_INTEGRATION",
      dimension: "technology_assessment",
      name_en: "Subsystem & Plant Integration Compatibility",
      name_id: "Kompatibilitas Integrasi Subsistem & Pabrik",
      description_en: "Ease of retrofitting into existing industrial infrastructure.",
      description_id: "Kemudahan integrasi ke dalam infrastruktur industri yang ada.",
      scale_type: "1-5",
      min_score: 1,
      max_score: 5,
      is_patent_specific: false,
      origin_classification: "adapted",
      reference_id: "ref-nasa",
      source_locator: "NASA ESTO TRL Levels 5-7 Integration Definitions",
      cross_domain_note: null,
      rubric_levels: {},
      default_provisional_weight: 0.1,
    },
    {
      id: "ind-7",
      code: "COMM_MARKET_DEMAND",
      dimension: "commercialization_readiness",
      name_en: "Verified Industrial Market Demand",
      name_id: "Permintaan Pasar Industri Terverifikasi",
      description_en: "Documented addressable market and customer pain-point evidence.",
      description_id: "Bukti pasar sasaran terdokumentasi dan kebutuhan pelanggan industri.",
      scale_type: "1-5",
      min_score: 1,
      max_score: 5,
      is_patent_specific: false,
      origin_classification: "adapted",
      reference_id: "ref-wipo",
      source_locator: "WIPO IP Valuation Basics (2024), Section 2",
      cross_domain_note: null,
      rubric_levels: {},
      default_provisional_weight: 0.25,
    },
    {
      id: "ind-8",
      code: "COMM_COMPETITIVE_POSITION",
      dimension: "commercialization_readiness",
      name_en: "Cost & Performance Competitive Advantage",
      name_id: "Keunggulan Kompetitif Biaya & Kinerja",
      description_en: "Quantified operating/capital advantage over incumbent substitutes.",
      description_id: "Keunggulan biaya operasi/modal terukur dibandingkan solusi eksisting.",
      scale_type: "1-5",
      min_score: 1,
      max_score: 5,
      is_patent_specific: false,
      origin_classification: "adapted",
      reference_id: "ref-wipo",
      source_locator: "WIPO IP Valuation Basics (2024), Section 2",
      cross_domain_note: null,
      rubric_levels: {},
      default_provisional_weight: 0.2,
    },
    {
      id: "ind-9",
      code: "COMM_REGULATORY",
      dimension: "commercialization_readiness",
      name_en: "Regulatory & Environmental Compliance Readiness",
      name_id: "Kesiapan Kepatuhan Regulasi & Lingkungan",
      description_en: "Alignment with national discharge and safety standards (e.g., PermenLHK).",
      description_id: "Kesesuaian dengan baku mutu nasional dan standar keselamatan (PermenLHK).",
      scale_type: "1-5",
      min_score: 1,
      max_score: 5,
      is_patent_specific: false,
      origin_classification: "proposed",
      reference_id: null,
      source_locator: "Proposed Rubric Indicator — Provisional until Expert Calibration",
      cross_domain_note: null,
      rubric_levels: {},
      default_provisional_weight: 0.2,
    },
    {
      id: "ind-10",
      code: "COMM_SUPPLY_CHAIN",
      dimension: "commercialization_readiness",
      name_en: "Supply Chain & Local Manufacturing Readiness",
      name_id: "Kesiapan Rantai Pasok & Manufaktur Lokal",
      description_en: "Availability of raw materials and qualified domestic fabricators.",
      description_id: "Ketersediaan bahan baku dan fabrikator dalam negeri yang terkualifikasi.",
      scale_type: "1-5",
      min_score: 1,
      max_score: 5,
      is_patent_specific: false,
      origin_classification: "proposed",
      reference_id: null,
      source_locator: "Proposed Rubric Indicator — Provisional until Expert Calibration",
      cross_domain_note: null,
      rubric_levels: {},
      default_provisional_weight: 0.15,
    },
    {
      id: "ind-11",
      code: "COMM_IP_LICENSING_READINESS",
      dimension: "commercialization_readiness",
      name_en: "IP Ownership Clarity & Licensing Readiness",
      name_id: "Kejelasan Kepemilikan KI & Kesiapan Lisensi",
      description_en: "Clarity of institutional title, FTO, and commercial partner LOIs.",
      description_id: "Kejelasan kepemilikan institusi, FTO, dan LOI mitra komersial.",
      scale_type: "1-5",
      min_score: 1,
      max_score: 5,
      is_patent_specific: false,
      origin_classification: "adapted",
      reference_id: "ref-wipo",
      source_locator: "WIPO IP Valuation Basics (2024), Sections 2 & 5",
      cross_domain_note: null,
      rubric_levels: {},
      default_provisional_weight: 0.2,
    },
  ];

  const scores = [
    {
      id: "sc-1",
      indicator_code: "TECH_TRL_NATIVE",
      dimension: "technology_assessment",
      status: "observed",
      scale_type: "1-9_trl",
      raw_score: 6,
      normalized_score: null,
      base_weight: 0.2,
      renormalized_weight: 0.0,
      rationale_en:
        "TRL 6 verified by 450-hour pilot-scale membrane reactor test in industrial dye effluent [page:2].",
      rationale_id:
        "TKT/TRL 6 terverifikasi melalui uji reaktor membran skala pilot 450 jam pada limbah tekstil [page:2].",
      expert_review_status: "approved",
      expert_review_reason: "Verified against pilot logbook on page:2.",
    },
    {
      id: "sc-2",
      indicator_code: "TECH_NOVELTY",
      dimension: "technology_assessment",
      status: "observed",
      scale_type: "1-5",
      raw_score: 4.5,
      normalized_score: 0.875,
      base_weight: 0.25,
      renormalized_weight: 0.25,
      rationale_en:
        "Sol-gel TiO2-clinoptilolite nanocomposite coating achieves 94.2% COD removal without secondary sludge [page:1].",
      rationale_id:
        "Pelapisan nanokomposit sol-gel TiO2-klinoptilolit mencapai penyisihan COD 94,2% tanpa lumpur sekunder [page:1].",
      expert_review_status: "approved",
      expert_review_reason: null,
    },
    {
      id: "sc-3",
      indicator_code: "TECH_VALIDATION",
      dimension: "technology_assessment",
      status: "observed",
      scale_type: "1-5",
      raw_score: 4.0,
      normalized_score: 0.75,
      base_weight: 0.25,
      renormalized_weight: 0.25,
      rationale_en:
        "Validated across 450 cumulative operating hours at 15 m3/day pilot throughput with 1.45 kWh/m3 energy use [page:2].",
      rationale_id:
        "Tervalidasi selama 450 jam operasi kumulatif pada kapasitas pilot 15 m3/hari dengan konsumsi 1,45 kWh/m3 [page:2].",
      expert_review_status: "approved",
      expert_review_reason: null,
    },
    {
      id: "sc-4",
      indicator_code: "TECH_SCALABILITY",
      dimension: "technology_assessment",
      status: "observed",
      scale_type: "1-5",
      raw_score: 4.0,
      normalized_score: 0.75,
      base_weight: 0.15,
      renormalized_weight: 0.15,
      rationale_en:
        "Modular 15 m3/day skid architecture with 82% domestic content (TKDN) and 3 ISO-9001 fabricators [page:3].",
      rationale_id:
        "Arsitektur skid modular 15 m3/hari dengan 82% TKDN dan 3 fabrikator ISO-9001 lokal [page:3].",
      expert_review_status: "approved",
      expert_review_reason: null,
    },
    {
      id: "sc-5",
      indicator_code: "TECH_PATENT_STRENGTH",
      dimension: "technology_assessment",
      status: "observed",
      scale_type: "1-5",
      raw_score: 4.0,
      normalized_score: 0.75,
      base_weight: 0.2,
      renormalized_weight: 0.2,
      rationale_en:
        "3 independent claims covering sol-gel synthesis, tubular module geometry, and UV-A regeneration cycle [page:1].",
      rationale_id:
        "3 klaim independen mencakup sintesis sol-gel, geometri modul tubular, dan siklus regenerasi UV-A [page:1].",
      expert_review_status: "approved",
      expert_review_reason: null,
    },
    {
      id: "sc-6",
      indicator_code: "TECH_SYSTEM_INTEGRATION",
      dimension: "technology_assessment",
      status: "observed",
      scale_type: "1-5",
      raw_score: 4.0,
      normalized_score: 0.75,
      base_weight: 0.15,
      renormalized_weight: 0.15,
      rationale_en:
        "Closed-loop PLC transmembrane pressure control integrates directly into existing equalization tanks [page:2].",
      rationale_id:
        "Kontrol tekanan transmembran PLC loop tertutup terintegrasi langsung ke tangki ekualisasi eksisting [page:2].",
      expert_review_status: "approved",
      expert_review_reason: null,
    },
    {
      id: "sc-7",
      indicator_code: "COMM_MARKET_DEMAND",
      dimension: "commercialization_readiness",
      status: "observed",
      scale_type: "1-5",
      raw_score: 4.0,
      normalized_score: 0.75,
      base_weight: 0.25,
      renormalized_weight: 0.25,
      rationale_en:
        "Addresses 420+ medium-to-large textile dyeing facilities in the Citarum River basin [para:1].",
      rationale_id:
        "Menjawab kebutuhan 420+ fasilitas pencelupan tekstil menengah-besar di DAS Citarum [para:1].",
      expert_review_status: "approved",
      expert_review_reason: null,
    },
    {
      id: "sc-8",
      indicator_code: "COMM_COMPETITIVE_POSITION",
      dimension: "commercialization_readiness",
      status: "observed",
      scale_type: "1-5",
      raw_score: 4.0,
      normalized_score: 0.75,
      base_weight: 0.2,
      renormalized_weight: 0.2,
      rationale_en:
        "Eliminates Fenton chemical sludge disposal cost and lowers energy consumption to 1.45 kWh/m3 [para:2].",
      rationale_id:
        "Menghilangkan biaya pembuangan lumpur kimia Fenton dan menekan energi menjadi 1,45 kWh/m3 [para:2].",
      expert_review_status: "approved",
      expert_review_reason: null,
    },
    {
      id: "sc-9",
      indicator_code: "COMM_REGULATORY",
      dimension: "commercialization_readiness",
      status: "observed",
      scale_type: "1-5",
      raw_score: 4.5,
      normalized_score: 0.875,
      base_weight: 0.2,
      renormalized_weight: 0.2,
      rationale_en:
        "Effluent COD < 45 mg/L complies with PermenLHK No. P.16/MENLHK/SETJEN/KUM.1/4/2019 [page:3].",
      rationale_id:
        "Efluen COD < 45 mg/L memenuhi baku mutu PermenLHK No. P.16/MENLHK/SETJEN/KUM.1/4/2019 [page:3].",
      expert_review_status: "approved",
      expert_review_reason: null,
    },
    {
      id: "sc-10",
      indicator_code: "COMM_SUPPLY_CHAIN",
      dimension: "commercialization_readiness",
      status: "observed",
      scale_type: "1-5",
      raw_score: 4.0,
      normalized_score: 0.75,
      base_weight: 0.15,
      renormalized_weight: 0.15,
      rationale_en:
        "Natural clinoptilolite zeolite sourced from Tasikmalaya with 82% domestic component content [page:3].",
      rationale_id:
        "Zeolit klinoptilolit alam dipasok dari Tasikmalaya dengan tingkat komponen dalam negeri 82% [page:3].",
      expert_review_status: "approved",
      expert_review_reason: null,
    },
    {
      id: "sc-11",
      indicator_code: "COMM_IP_LICENSING_READINESS",
      dimension: "commercialization_readiness",
      status: "observed",
      scale_type: "1-5",
      raw_score: 4.0,
      normalized_score: 0.75,
      base_weight: 0.2,
      renormalized_weight: 0.2,
      rationale_en:
        "2 industrial Letters of Intent (LOI) signed for non-exclusive licensing in West Java [para:4].",
      rationale_id:
        "2 Letter of Intent (LOI) industri telah ditandatangani untuk lisensi non-eksklusif di Jawa Barat [para:4].",
      expert_review_status: "approved",
      expert_review_reason: null,
    },
  ];

  const evidenceItems = [
    {
      id: "ev-1",
      indicator_score_id: "sc-1",
      document_id: doc1Id,
      indicator_code: "TECH_TRL_NATIVE",
      location_ref: "page:2",
      quoted_text:
        "Pilot Validation (TRL 6): The 15 m3/day subsystem prototype was operated continuously for 450 cumulative hours in an industrial textile wastewater environment.",
      claim_summary: "Verified TRL 6 pilot operation for 450 hours at 15 m3/day.",
      resolution_status: "resolved",
      rejection_reason: null,
    },
    {
      id: "ev-2",
      indicator_score_id: "sc-2",
      document_id: doc1Id,
      indicator_code: "TECH_NOVELTY",
      location_ref: "page:1",
      quoted_text:
        "The hybrid TiO2-zeolite nanocomposite membrane achieves 94.2% COD degradation and 97.8% reactive azo dye decolorization.",
      claim_summary: "94.2% COD degradation and 97.8% azo dye decolorization.",
      resolution_status: "resolved",
      rejection_reason: null,
    },
    {
      id: "ev-3",
      indicator_score_id: "sc-4",
      document_id: doc1Id,
      indicator_code: "TECH_SCALABILITY",
      location_ref: "page:3",
      quoted_text:
        "Supply Chain & Regulatory Compliance: Achieving 82% local component content (TKDN) with 3 qualified ISO-9001 pressure vessel fabricators in Bandung.",
      claim_summary: "82% local content (TKDN) with 3 qualified ISO-9001 fabricators.",
      resolution_status: "resolved",
      rejection_reason: null,
    },
    {
      id: "ev-4",
      indicator_score_id: "sc-7",
      document_id: doc2Id,
      indicator_code: "COMM_MARKET_DEMAND",
      location_ref: "para:1",
      quoted_text:
        "Target Market Segment: Over 420 medium-to-large textile dyeing facilities operating in the Citarum River basin require compact tertiary wastewater retrofits.",
      claim_summary: "420+ textile facilities in Citarum basin require retrofits.",
      resolution_status: "resolved",
      rejection_reason: null,
    },
    {
      id: "ev-5",
      indicator_score_id: "sc-11",
      document_id: doc2Id,
      indicator_code: "COMM_IP_LICENSING_READINESS",
      location_ref: "para:4",
      quoted_text:
        "Two regional environmental engineering EPC firms have signed Letters of Intent (LOI) for non-exclusive manufacturing and integration licensing.",
      claim_summary: "Two EPC firms signed LOIs for non-exclusive licensing.",
      resolution_status: "resolved",
      rejection_reason: null,
    },
  ];

  const dcfInputs = {
    revenues_idr: [1200000000, 2500000000, 4200000000, 5800000000, 7000000000],
    operating_costs_idr: [750000000, 1400000000, 2150000000, 2850000000, 3400000000],
    capex_idr: [350000000, 150000000, 100000000, 100000000, 100000000],
    working_capital_changes_idr: [50000000, 75000000, 90000000, 80000000, 60000000],
    tax_rate: 0.22,
    discount_rate: 0.15,
    attribution_mode: "documented_attribution_factor",
    attribution_factor: 0.75,
    attribution_documentation:
      "75% technology attribution factor based on membrane module share of turnkey skid BOM.",
    risk_treatment_mode: "in_discount_rate",
  };
  const dcfCalc = calculateDcfServer(dcfInputs, 20260417, 500);

  const valuationScenarios = [
    {
      id: "val-dcf-base",
      technology_id: techId,
      assessment_revision_id: revId,
      scenario_name: "WIPO Base DCF Valuation (IDR)",
      scenario_case: "base",
      approach: "dcf",
      currency: "IDR",
      attribution_mode: "documented_attribution_factor",
      attribution_factor: 0.75,
      attribution_documentation: dcfInputs.attribution_documentation,
      risk_treatment_mode: "in_discount_rate",
      double_counting_flagged: false,
      double_counting_warning: null,
      inputs_json: dcfInputs,
      calculation_breakdown_json: { annual_breakdown: dcfCalc.annual_breakdown },
      indicative_value_idr: dcfCalc.npv_idr,
      indicative_value_formatted: formatIdrServer(dcfCalc.npv_idr),
      range_min_idr: dcfCalc.monte_carlo.p10_idr,
      range_max_idr: dcfCalc.monte_carlo.p90_idr,
      sensitivity_json: dcfCalc.sensitivity,
      monte_carlo_seed: 20260417,
      monte_carlo_json: dcfCalc.monte_carlo,
      wipo_reference_locator:
        "WIPO IP Valuation Basics (2024), Section 4.1 — Income Approach (DCF)",
      created_at: now,
    },
    {
      id: "val-rfr-base",
      technology_id: techId,
      assessment_revision_id: revId,
      scenario_name: "WIPO Relief-from-Royalty (5.0% Gross Royalty)",
      scenario_case: "base",
      approach: "relief_from_royalty",
      currency: "IDR",
      attribution_mode: "direct_cash_flows",
      attribution_factor: 1.0,
      attribution_documentation: "Direct licensing royalty stream (5.0% of licensed skid revenue).",
      risk_treatment_mode: "in_discount_rate",
      double_counting_flagged: false,
      double_counting_warning: null,
      inputs_json: { royalty_rate: 0.05, discount_rate: 0.15, tax_rate: 0.22 },
      calculation_breakdown_json: { annual_breakdown: [] },
      indicative_value_idr: 486250000,
      indicative_value_formatted: formatIdrServer(486250000),
      range_min_idr: 410000000,
      range_max_idr: 560000000,
      sensitivity_json: [],
      monte_carlo_seed: null,
      monte_carlo_json: null,
      wipo_reference_locator:
        "WIPO IP Valuation Basics (2024), Section 4.2 — Relief-from-Royalty Method",
      created_at: now,
    },
    {
      id: "val-cost-base",
      technology_id: techId,
      assessment_revision_id: revId,
      scenario_name: "WIPO Reproduction Cost Approach (IDR)",
      scenario_case: "low",
      approach: "cost",
      currency: "IDR",
      attribution_mode: "direct_cash_flows",
      attribution_factor: 1.0,
      attribution_documentation: "Historical R&D + pilot reproduction cost less obsolescence.",
      risk_treatment_mode: "in_discount_rate",
      double_counting_flagged: false,
      double_counting_warning: null,
      inputs_json: { historical_rd_idr: 680000000, reproduction_pilot_idr: 420000000 },
      calculation_breakdown_json: { annual_breakdown: [] },
      indicative_value_idr: 992750000,
      indicative_value_formatted: formatIdrServer(992750000),
      range_min_idr: 900000000,
      range_max_idr: 1100000000,
      sensitivity_json: [],
      monte_carlo_seed: null,
      monte_carlo_json: null,
      wipo_reference_locator: "WIPO IP Valuation Basics (2024), Section 3 — Cost Approach",
      created_at: now,
    },
    {
      id: "val-mkt-base",
      technology_id: techId,
      assessment_revision_id: revId,
      scenario_name: "WIPO Market Comparables Indication (IDR)",
      scenario_case: "high",
      approach: "market_comparables",
      currency: "IDR",
      attribution_mode: "direct_cash_flows",
      attribution_factor: 1.0,
      attribution_documentation: "Adjusted comparable industrial water membrane licensing deals.",
      risk_treatment_mode: "in_discount_rate",
      double_counting_flagged: false,
      double_counting_warning: null,
      inputs_json: {},
      calculation_breakdown_json: { annual_breakdown: [] },
      indicative_value_idr: 1850000000,
      indicative_value_formatted: formatIdrServer(1850000000),
      range_min_idr: 1550000000,
      range_max_idr: 2150000000,
      sensitivity_json: [],
      monte_carlo_seed: null,
      monte_carlo_json: null,
      wipo_reference_locator:
        "WIPO IP Valuation Basics (2024), Section 3.2 — Market Approach",
      created_at: now,
    },
  ];

  return {
    technologies: [
      {
        id: techId,
        code: "ITENAS-PAT-2026-001",
        title_en:
          "Photocatalytic TiO2-Zeolite Nanocomposite Membrane Reactor for Industrial Textile Wastewater",
        title_id:
          "Reaktor Membran Nanokomposit Fotokatalitik TiO2-Zeolit untuk Limbah Cair Industri Tekstil",
        domain: "Environmental & Chemical Engineering",
        inventor_organization: "ITENAS Bandung — Chemical & Environmental Engineering Lab",
        description_en:
          "Modular photocatalytic tubular membrane reactor combining sol-gel TiO2 nanoparticles immobilized on natural clinoptilolite zeolite with low-energy UV-A LED regeneration.",
        description_id:
          "Reaktor membran tubular fotokatalitik modular yang menggabungkan nanopartikel TiO2 sol-gel terimobilisasi pada zeolit klinoptilolit alam dengan regenerasi LED UV-A hemat energi.",
        claimed_trl: 6,
        patent_status: "patent_pending",
        patent_application_number: "IDP000089421",
        patent_jurisdiction: "ID",
        status: "assessed",
        is_synthetic_demo: true,
        active_document_count: 2,
        created_at: now,
        updated_at: now,
        latest_revision_id: revId,
        latest_revision_number: 1,
        expert_review_status: "unreviewed_draft",
        four_separate_outputs: {
          technology_assessment: {
            normalized_score: 0.7813,
            trl_native_1_to_9: 6,
            is_provisional: true,
          },
          commercialization_readiness: {
            normalized_score: 0.775,
            is_provisional: true,
          },
          economic_valuation: {
            currency: "IDR",
            dcf_base_indicative_idr: dcfCalc.npv_idr,
            dcf_base_formatted: formatIdrServer(dcfCalc.npv_idr),
            score_conversion_prohibited: true,
          },
          evidence_completeness: {
            weighted_completeness_score: 1.0,
            observed_count: 11,
            missing_count: 0,
            not_applicable_count: 0,
          },
        },
      },
    ],
    documents: [
      {
        id: doc1Id,
        technology_id: techId,
        opaque_storage_id: "vault_demo_spec_001.enc",
        original_filename: "ITENAS_PAT_2026_001_Patent_And_Pilot_Specification.pdf",
        document_type: "patent_specification",
        mime_type: "application/pdf",
        file_extension: ".pdf",
        file_size_bytes: 18420,
        sha256_hash:
          "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
        signature_valid: true,
        encrypted_at_rest: true,
        ocr_required: false,
        ocr_warning_message: null,
        page_or_section_count: 3,
        extracted_char_count: 1420,
        is_deleted: false,
        deleted_at: null,
        created_at: now,
      },
      {
        id: doc2Id,
        technology_id: techId,
        opaque_storage_id: "vault_demo_mkt_002.enc",
        original_filename: "ITENAS_PAT_2026_001_Market_And_Commercialization_Dossier.docx",
        document_type: "market_study",
        mime_type:
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        file_extension: ".docx",
        file_size_bytes: 14280,
        sha256_hash:
          "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae",
        signature_valid: true,
        encrypted_at_rest: true,
        ocr_required: false,
        ocr_warning_message: null,
        page_or_section_count: 4,
        extracted_char_count: 1180,
        is_deleted: false,
        deleted_at: null,
        created_at: now,
      },
    ],
    documentSections: {
      [doc1Id]: [
        {
          id: "sec-1",
          section_index: 1,
          location_type: "page",
          location_ref: "page:1",
          heading: "Page 1 — Patent Claims & Technical Novelty",
          content_text:
            "Independent Claim 1: A photocatalytic nanocomposite membrane comprising sol-gel synthesized TiO2 anatase nanoparticles immobilized on thermally activated clinoptilolite zeolite. The hybrid TiO2-zeolite nanocomposite membrane achieves 94.2% COD degradation and 97.8% reactive azo dye decolorization without generating secondary chemical Fentonsludge.",
          char_count: 332,
        },
        {
          id: "sec-2",
          section_index: 2,
          location_type: "page",
          location_ref: "page:2",
          heading: "Page 2 — Pilot Validation (NASA TRL 6) & System Integration",
          content_text:
            "Pilot Validation (TRL 6): The 15 m3/day subsystem prototype was operated continuously for 450 cumulative hours in an industrial textile wastewater environment at Majalaya, Bandung. Specific electrical energy consumption averaged 1.45 kWh/m3 with closed-loop PLC transmembrane pressure control.",
          char_count: 298,
        },
        {
          id: "sec-3",
          section_index: 3,
          location_type: "page",
          location_ref: "page:3",
          heading: "Page 3 — Supply Chain (TKDN) & Regulatory Compliance",
          content_text:
            "Supply Chain & Regulatory Compliance: Achieving 82% local component content (TKDN) with 3 qualified ISO-9001 pressure vessel fabricators in Bandung. Treated effluent COD < 45 mg/L complies with PermenLHK No. P.16/MENLHK/SETJEN/KUM.1/4/2019.",
          char_count: 249,
        },
      ],
      [doc2Id]: [
        {
          id: "sec-4",
          section_index: 1,
          location_type: "paragraph",
          location_ref: "para:1",
          heading: "Market Demand Analysis",
          content_text:
            "Target Market Segment: Over 420 medium-to-large textile dyeing facilities operating in the Citarum River basin require compact tertiary wastewater retrofits.",
          char_count: 162,
        },
        {
          id: "sec-5",
          section_index: 2,
          location_type: "paragraph",
          location_ref: "para:2",
          heading: "Competitive Cost Position",
          content_text:
            "Eliminates Fenton chemical sludge disposal cost and lowers energy consumption to 1.45 kWh/m3, yielding a 28% lifecycle OPEX reduction.",
          char_count: 138,
        },
        {
          id: "sec-6",
          section_index: 3,
          location_type: "paragraph",
          location_ref: "para:3",
          heading: "Financial Projection Basis (IDR)",
          content_text:
            "Five-year projected licensing and turnkey module revenues grow from Rp 1.200.000.000 in Year 1 to Rp 7.000.000.000 in Year 5 at a 15% WACC discount rate.",
          char_count: 154,
        },
        {
          id: "sec-7",
          section_index: 4,
          location_type: "paragraph",
          location_ref: "para:4",
          heading: "IP Licensing Readiness",
          content_text:
            "Two regional environmental engineering EPC firms have signed Letters of Intent (LOI) for non-exclusive manufacturing and integration licensing.",
          char_count: 144,
        },
      ],
    },
    revisions: [
      {
        id: revId,
        technology_id: techId,
        analysis_run_id: runId,
        parent_revision_id: null,
        weight_set_id: "ws-provisional-v1",
        revision_number: 1,
        actor_id: "usr-analyst",
        change_reason:
          "Initial 8-agent LangGraph assessment and WIPO IDR valuation compilation.",
        previous_values_json: null,
        technology_assessment_score: 0.7813,
        trl_score: 6,
        trl_exit_criteria_met_json: [
          "Subsystem/system prototype demonstrated in relevant industrial wastewater environment (450 cumulative hours at 15 m3/day).",
          "Mass and electrical energy balance verified (1.45 kWh/m3).",
          "PLC closed-loop transmembrane pressure control verified under fouling cycles.",
        ],
        commercialization_readiness_score: 0.775,
        evidence_completeness_score: 1.0,
        tech_completeness_score: 1.0,
        comm_completeness_score: 1.0,
        is_provisional: true,
        provisional_reasons_json: [
          "Active weight set is provisional_equal_v1 (requires expert AHP sign-off).",
        ],
        applicable_indicator_count: 11,
        observed_indicator_count: 11,
        missing_indicator_count: 0,
        not_applicable_indicator_count: 0,
        ip_patent_signals_json: {
          source: "manual_or_disclosed",
          patent_number: "IDP000089421",
          jurisdiction: "ID",
          family_size: 2,
          forward_citations_5yr: 3,
          independent_claims_count: 3,
          harhoff_contextual_note:
            "Per Harhoff et al. (2003), patent family and citation indicators are contextual signals and are never converted into IDR monetary values.",
        },
        market_intelligence_json: {
          target_segment: "Citarum Basin Industrial Textile Dyeing Facilities (420+ plants)",
        },
        commercialization_pathway_json: {
          recommended_pathway: "Non-Exclusive EPC Licensing + Core Membrane Cartridge Supply",
          rationale:
            "Enables rapid industrial deployment through existing ISO-9001 fabricators while retaining high-margin sol-gel membrane coating IP.",
        },
        risk_matrix_json: {},
        created_at: now,
        indicator_scores: scores,
        evidence_items: evidenceItems,
      },
    ],
    analysisRuns: [
      {
        id: runId,
        technology_id: techId,
        consent_record_id: "consent-init-001",
        status: "completed",
        current_node: "report_compilation",
        progress_percent: 100,
        requested_provider: "fixture",
        requested_model: "fixture-deterministic-v1",
        actual_provider_returned: "fixture",
        actual_model_returned: "fixture-deterministic-v1",
        prompt_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        run_config_hash:
          "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        config_snapshot_json: { strict_evidence_verification: true },
        rubric_version_tag: "methodology_v1.0",
        document_hashes_json: {
          [doc1Id]:
            "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
          [doc2Id]:
            "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae",
        },
        app_version: "1.0.0",
        retry_count: 0,
        max_retries: 3,
        cancel_requested: false,
        error_message: null,
        partial_results_json: {
          extraction: { contradictions_detected: [] },
        },
        rejected_claims_json: [],
        started_at: now,
        completed_at: now,
        created_at: now,
        agent_executions: [
          "intake_validation",
          "evidence_extraction",
          "ip_patent_analysis",
          "market_intelligence",
          "technical_trl_assessment",
          "commercialization_pathway",
          "risk_synthesis",
          "report_compilation",
        ].map((name, idx) => ({
          id: `ag-${idx + 1}`,
          agent_name: name,
          status: "completed",
          provider_used: "fixture",
          model_used: "fixture-deterministic-v1",
          prompt_hash: "e3b0c44298fc1c149afbf4c8",
          latency_ms: 42 + idx * 11,
          output_summary: { verified: true },
        })),
        checkpoints: [],
      },
    ],
    valuationScenarios,
    reviews: [] as any[],
    reports: [] as any[],
    indicators,
    references: [
      {
        id: "ref-wipo",
        code: "WIPO-2024",
        authors: "World Intellectual Property Organization (WIPO)",
        publication_year: 2024,
        title:
          "Intellectual Property Valuation Basics for Technology Transfer Professionals",
        venue_or_publisher: "WIPO Official Publication, Geneva",
        doi_or_url:
          "https://www.wipo.int/web-publications/intellectual-property-valuation-basics-for-technology-transfer-professionals/en/index.html",
        bibliographic_status: "verified",
        methodology_verification_status: "methodology_verified",
        verified_sections_pages:
          "Sections 2, 3, 4, and 5 (Cost, Market Comparables, DCF, Relief-from-Royalty, Attribution & Risk)",
        domain_scope: "Technology Transfer & IP Valuation",
        cross_domain_adaptation_notes:
          "Implemented in Indonesian Rupiah (IDR) with strict separation from qualitative assessment scores.",
        summary_quote:
          "Valuation approaches (Cost, Market, Income/DCF, Relief-from-Royalty) require financial inputs and must not be conflated with qualitative scoring.",
      },
      {
        id: "ref-nasa",
        code: "NASA-TRL-2020",
        authors: "NASA Earth Science Technology Office (ESTO) / Mankins, J. C.",
        publication_year: 2020,
        title: "Technology Readiness Levels (TRL) — NASA 1-9 Scale & ISO 16290:2013",
        venue_or_publisher: "NASA ESTO Official Guidelines",
        doi_or_url: "https://esto.nasa.gov/trl/",
        bibliographic_status: "verified",
        methodology_verification_status: "methodology_verified",
        verified_sections_pages: "TRL Definitions Level 1 through Level 9 & Exit Criteria",
        domain_scope: "Engineering & Technology Maturity",
        cross_domain_adaptation_notes:
          "Adapted from aerospace systems to industrial chemical/hardware/software prototypes; native 1-9 integer scale preserved.",
        summary_quote:
          "TRL 6 requires a system/subsystem model or prototype demonstration in a relevant environment.",
      },
      {
        id: "ref-harhoff",
        code: "HARHOFF-2003",
        authors: "Harhoff, D., Scherer, F. M., & Vopel, K.",
        publication_year: 2003,
        title: "Citations, family size, opposition and the value of patent rights",
        venue_or_publisher: "Research Policy, 32(8), 1343-1363",
        doi_or_url:
          "https://www.sciencedirect.com/science/article/abs/pii/S0048733302001245",
        bibliographic_status: "verified",
        methodology_verification_status: "methodology_verified",
        verified_sections_pages:
          "Section 2 (pp. 1345-1348) & Section 4 (Empirical Results, pp. 1353-1359)",
        domain_scope: "Patent Econometrics",
        cross_domain_adaptation_notes:
          "Patent citations and family size are treated strictly as contextual signals, never direct monetary multipliers.",
        summary_quote:
          "Forward citations and family size correlate with highly skewed economic value but do not deterministically price individual patents.",
      },
      {
        id: "ref-saaty",
        code: "SAATY-1980",
        authors: "Saaty, T. L.",
        publication_year: 1980,
        title:
          "The Analytic Hierarchy Process: Planning, Priority Setting, Resource Allocation",
        venue_or_publisher: "McGraw-Hill, New York",
        doi_or_url: "https://doi.org/10.21236/ada214804",
        bibliographic_status: "verified",
        methodology_verification_status: "methodology_verified",
        verified_sections_pages:
          "Chapter 1 (1-9 Fundamental Scale, pp. 17-24) & Chapter 3 (Consistency Ratio CR <= 0.10, pp. 49-62)",
        domain_scope: "Multi-Criteria Decision Analysis",
        cross_domain_adaptation_notes: null,
        summary_quote:
          "Pairwise reciprocal judgments must satisfy Consistency Ratio CR = CI / RI <= 0.10.",
      },
      {
        id: "ref-oslo",
        code: "OECD-OSLO-2018",
        authors: "OECD / Eurostat",
        publication_year: 2018,
        title:
          "Oslo Manual 2018: Guidelines for Collecting, Reporting and Using Data on Innovation",
        venue_or_publisher: "OECD Publishing, Paris",
        doi_or_url: "https://doi.org/10.1787/9789264304604-en",
        bibliographic_status: "verified",
        methodology_verification_status: "bibliographically_verified_only",
        verified_sections_pages: null,
        domain_scope: "Innovation Taxonomy",
        cross_domain_adaptation_notes:
          "Bibliographically verified only; never cited to justify any scoring formula or weight.",
        summary_quote:
          "Provides general innovation taxonomy framing without specific patent valuation formulas.",
      },
    ],
    auditLogs: [
      {
        id: "aud-1",
        created_at: now,
        action: "system.seed",
        entity_type: "technology",
        entity_id: techId,
        reason:
          "Initialized baseline technology ITENAS-PAT-2026-001 with 4 strictly separated outputs.",
      },
    ],
  };
}

export function loadWebState(): Record<string, any> {
  ensureDirs();
  if (!fs.existsSync(STATE_FILE)) {
    const init = buildInitialState();
    fs.writeFileSync(STATE_FILE, JSON.stringify(init, null, 2), "utf-8");
    return init;
  }
  try {
    return JSON.parse(fs.readFileSync(STATE_FILE, "utf-8"));
  } catch {
    const init = buildInitialState();
    fs.writeFileSync(STATE_FILE, JSON.stringify(init, null, 2), "utf-8");
    return init;
  }
}

export function saveWebState(state: any) {
  ensureDirs();
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), "utf-8");
}
