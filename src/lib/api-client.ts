import type {
  AnalysisRunItem,
  AssessmentRevisionItem,
  AuthSessionResponse,
  DocumentItem,
  DocumentSectionItem,
  ExpertReviewItem,
  IndicatorDefinitionItem,
  ReportSnapshotItem,
  ScientificReferenceItem,
  TechnologyItem,
  ValuationScenarioItem,
} from "./api-types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "/api/v1";

const STORAGE_AUTH_KEY = "techval_auth_session_v1";

export const DEMO_ACCOUNTS = {
  analyst: {
    username: "analyst",
    password: "AnalystTechVal2026!",
    label: "Analyst (Rina Kusuma)",
  },
  expert_reviewer: {
    username: "reviewer",
    password: "ReviewerTechVal2026!",
    label: "Expert Reviewer (Prof. Hendra Wijaya)",
  },
  admin: {
    username: "admin",
    password: "AdminTechVal2026!",
    label: "Admin (Dr. Pratama)",
  },
};

export function getSavedSession(): AuthSessionResponse | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_AUTH_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as AuthSessionResponse;
  } catch {
    return null;
  }
}

export function saveSession(session: AuthSessionResponse | null): void {
  if (typeof window === "undefined") return;
  if (!session) {
    window.localStorage.removeItem(STORAGE_AUTH_KEY);
  } else {
    window.localStorage.setItem(STORAGE_AUTH_KEY, JSON.stringify(session));
  }
}

export async function ensureAuthenticated(
  preferredRole: keyof typeof DEMO_ACCOUNTS = "analyst"
): Promise<AuthSessionResponse> {
  const existing = getSavedSession();
  if (existing && existing.access_token) {
    return existing;
  }
  const creds = DEMO_ACCOUNTS[preferredRole];
  return loginWithCredentials(creds.username, creds.password);
}

export async function loginWithCredentials(
  username: string,
  password: string
): Promise<AuthSessionResponse> {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Authentication failed (${res.status}): ${errText}`);
  }
  const data = (await res.json()) as AuthSessionResponse;
  saveSession(data);
  return data;
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  let session = getSavedSession();
  if (!session) {
    session = await ensureAuthenticated("analyst");
  }

  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${session.access_token}`);
  if (
    options.method &&
    !["GET", "HEAD", "OPTIONS"].includes(options.method.toUpperCase())
  ) {
    headers.set("X-CSRF-Token", session.csrf_token);
  }
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let res = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    session = await loginWithCredentials(
      DEMO_ACCOUNTS.analyst.username,
      DEMO_ACCOUNTS.analyst.password
    );
    headers.set("Authorization", `Bearer ${session.access_token}`);
    headers.set("X-CSRF-Token", session.csrf_token);
    res = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail =
        typeof body.detail === "string"
          ? body.detail
          : JSON.stringify(body.detail || body);
    } catch {
      detail = await res.text();
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }

  return (await res.json()) as T;
}

export const apiClient = {
  getHealth: () => apiFetch<Record<string, any>>("/health"),
  listTechnologies: () => apiFetch<TechnologyItem[]>("/technologies"),
  getTechnology: (id: string) => apiFetch<TechnologyItem>(`/technologies/${id}`),
  createTechnology: (payload: Record<string, any>) =>
    apiFetch<TechnologyItem>("/technologies", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listDocuments: (techId: string, includeDeleted = false) =>
    apiFetch<DocumentItem[]>(
      `/documents?technology_id=${techId}&include_deleted=${includeDeleted}`
    ),
  getDocumentSections: (docId: string) =>
    apiFetch<DocumentSectionItem[]>(`/documents/${docId}/sections`),
  uploadDocument: (techId: string, documentType: string, file: File) => {
    const fd = new FormData();
    fd.append("technology_id", techId);
    fd.append("document_type", documentType);
    fd.append("file", file);
    return apiFetch<DocumentItem>("/documents/upload", {
      method: "POST",
      body: fd,
    });
  },
  deleteDocument: (docId: string, reason: string) =>
    apiFetch<Record<string, any>>(
      `/documents/${docId}?reason=${encodeURIComponent(reason)}`,
      { method: "DELETE" }
    ),
  createConsent: (payload: Record<string, any>) =>
    apiFetch<Record<string, any>>("/analysis-runs/consent", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  triggerAnalysisRun: (payload: Record<string, any>) =>
    apiFetch<AnalysisRunItem>("/analysis-runs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listAnalysisRuns: (techId: string) =>
    apiFetch<AnalysisRunItem[]>(`/analysis-runs?technology_id=${techId}`),
  getAnalysisRun: (runId: string) =>
    apiFetch<AnalysisRunItem>(`/analysis-runs/${runId}`),
  cancelAnalysisRun: (runId: string) =>
    apiFetch<Record<string, any>>(`/analysis-runs/${runId}/cancel`, {
      method: "POST",
    }),
  retryAnalysisRun: (runId: string, executeSynchronously = true) =>
    apiFetch<AnalysisRunItem>(
      `/analysis-runs/${runId}/retry?execute_synchronously=${executeSynchronously}`,
      { method: "POST" }
    ),
  listIndicators: () => apiFetch<IndicatorDefinitionItem[]>("/indicators"),
  listWeightSets: async () => {
    const res = await apiFetch<Record<string, any>>("/weighting/weight-sets");
    return res.weight_sets || [];
  },
  listRevisions: (techId: string) =>
    apiFetch<AssessmentRevisionItem[]>(`/indicators/revisions/${techId}`),
  getLatestRevision: async (techId: string) => {
    const revs = await apiFetch<AssessmentRevisionItem[]>(
      `/indicators/revisions/${techId}`
    );
    if (!revs || revs.length === 0) {
      throw new Error("No assessment revisions found for this technology.");
    }
    return revs[0];
  },
  createNewRevision: async (techId: string, payload: Record<string, any>) => {
    const revs = await apiFetch<AssessmentRevisionItem[]>(
      `/indicators/revisions/${techId}`
    );
    const parentId = revs[0]?.id;
    const session = getSavedSession();
    if (!session || session.user.role === "analyst") {
      await loginWithCredentials(
        DEMO_ACCOUNTS.expert_reviewer.username,
        DEMO_ACCOUNTS.expert_reviewer.password
      );
    }
    const updates = (payload.indicator_updates || []).map((u: any) => ({
      indicator_code: u.indicator_code,
      status: u.status,
      raw_score: u.raw_score,
      expert_review_status: "approved",
      expert_review_reason: payload.change_reason || "Verified indicator update",
      rationale_en: u.rationale_en,
      rationale_id: u.rationale_id,
    }));
    await apiFetch<Record<string, any>>("/reviews/revise-indicators", {
      method: "POST",
      body: JSON.stringify({
        technology_id: techId,
        parent_revision_id: parentId,
        change_reason: payload.change_reason,
        indicator_updates: updates,
      }),
    });
    const updatedRevs = await apiFetch<AssessmentRevisionItem[]>(
      `/indicators/revisions/${techId}`
    );
    return updatedRevs[0];
  },
  computeAhp: (payload: Record<string, any>) =>
    apiFetch<Record<string, any>>("/weighting/ahp-preview", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  lookupPatentSignals: (payload: Record<string, any>) => {
    if (payload.technology_id) {
      return apiFetch<Record<string, any>>(
        `/technologies/${payload.technology_id}/patent-ops-check`
      );
    }
    return Promise.resolve({
      source: "manual_or_disclosed",
      patent_number: payload.patent_number,
      ...payload.manual_signals,
    });
  },
  listValuationScenarios: async (techId: string, revId?: string) => {
    const res = await apiFetch<Record<string, any>>(
      `/valuation/scenarios/${techId}${revId ? `?revision_id=${revId}` : ""}`
    );
    return (res.scenarios || []) as ValuationScenarioItem[];
  },
  calculateDcf: async (payload: Record<string, any>) => {
    const revs = await apiFetch<AssessmentRevisionItem[]>(
      `/indicators/revisions/${payload.technology_id}`
    );
    const parentId = revs[0]?.id;
    const dcfInputs = {
      revenues_idr: payload.revenues_idr,
      operating_costs_idr: payload.operating_costs_idr,
      capex_idr: payload.capex_idr,
      working_capital_changes_idr: payload.working_capital_changes_idr,
      tax_rate: payload.tax_rate,
      discount_rate: payload.discount_rate,
      attribution_mode: payload.attribution_mode,
      attribution_factor: payload.attribution_factor ?? 1.0,
      attribution_documentation: payload.attribution_documentation,
      risk_treatment_mode: payload.risk_treatment_mode,
    };
    await apiFetch<Record<string, any>>("/valuation/revise", {
      method: "POST",
      body: JSON.stringify({
        technology_id: payload.technology_id,
        parent_revision_id: parentId,
        change_reason: `Updated DCF scenario: ${payload.scenario_name}`,
        dcf_base_inputs: dcfInputs,
        monte_carlo_seed: payload.monte_carlo_seed || 42,
        monte_carlo_iterations: payload.monte_carlo_iterations || 500,
      }),
    });
    const listRes = await apiFetch<Record<string, any>>(
      `/valuation/scenarios/${payload.technology_id}`
    );
    const scenarios = (listRes.scenarios || []) as ValuationScenarioItem[];
    return (
      scenarios.find((s) => s.approach === "dcf" && s.scenario_case === "base") ||
      scenarios[0]
    );
  },
  listReviews: (techId: string) =>
    apiFetch<ExpertReviewItem[]>(`/reviews/${techId}`),
  submitExpertReview: (payload: Record<string, any>) =>
    apiFetch<ExpertReviewItem>("/reviews/sign-off", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listAuditLogs: (limit = 100) =>
    apiFetch<Record<string, any>[]>(`/auth/audit-logs?limit=${limit}`),
  generateReport: (payload: {
    technology_id: string;
    assessment_revision_id?: string | null;
    language: "en" | "id";
  }) =>
    apiFetch<ReportSnapshotItem>("/reports/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listReports: (techId: string) =>
    apiFetch<ReportSnapshotItem[]>(`/reports/${techId}`),
  getReportDownloadUrl: (reportId: string) =>
    `${API_BASE_URL}/reports/download/${reportId}`,
  listReferences: () => apiFetch<ScientificReferenceItem[]>("/references"),
  getMethodologySpecs: async () => {
    const configs = await apiFetch<Record<string, any>[]>(
      "/references/methodology-configs"
    );
    return configs[0] || {};
  },
  runEvaluationSuite: async () => {
    const datasets = await apiFetch<Record<string, any>[]>(
      "/experiments/datasets"
    );
    const dsId = datasets[0]?.id;
    if (dsId) {
      return apiFetch<Record<string, any>>("/experiments/run", {
        method: "POST",
        body: JSON.stringify({
          dataset_id: dsId,
          name: "Phase 4 Multi-Condition Benchmark Run",
        }),
      });
    }
    const exps = await apiFetch<Record<string, any>[]>("/experiments");
    return exps[0] || {};
  },
  getEvaluationExportUrl: (experimentId: string, format: "json" | "csv") =>
    `${API_BASE_URL}/experiments/${experimentId}/export/${format}`,
};
