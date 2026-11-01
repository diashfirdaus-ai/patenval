import { NextRequest, NextResponse } from "next/server";
import { loadWebStateAsync } from "@/server/engine";
import { MUSE_AGENTS } from "@/lib/muse-agents";

export const maxDuration = 60;

type ChatTurn = { role: "user" | "assistant"; content: string };

function buildContext(state: any, techId: string | undefined, lang: string) {
  const tech = state.technologies.find((t: any) => t.id === techId) || state.technologies[0];
  if (!tech) return { tech: null, text: "" };
  const rev =
    [...state.revisions].reverse().find((r: any) => r.technology_id === tech.id) ||
    state.revisions[0];
  const fo = tech.four_separate_outputs || {};
  const id = lang === "id";

  const lines: string[] = [];
  lines.push(`TECHNOLOGY: ${tech.code} - ${id ? tech.title_id || tech.title_en : tech.title_en}`);
  lines.push(`Patent status: ${tech.patent_status}; claimed TRL: ${tech.claimed_trl}`);
  if (tech.is_synthetic_demo) lines.push("NOTE: this is a synthetic demonstration case.");
  lines.push("");
  lines.push("FOUR SEPARATE OUTPUTS (never convert one into another):");
  lines.push(`1. Technology score (normalized 0-1): ${fo.technology_assessment?.normalized_score}; native TRL ${fo.technology_assessment?.trl_native_1_to_9}`);
  lines.push(`2. Commercialization readiness (0-1): ${fo.commercialization_readiness?.normalized_score}`);
  lines.push(`3. Economic valuation base DCF: ${fo.economic_valuation?.dcf_base_formatted}`);
  lines.push(`4. Evidence completeness (0-1): ${fo.evidence_completeness?.weighted_completeness_score}`);

  lines.push("");
  lines.push("INDICATOR SCORES:");
  for (const s of rev?.indicator_scores || []) {
    lines.push(`- ${s.indicator_code}: raw=${s.raw_score} norm=${s.normalized_score} status=${s.status} :: ${id ? s.rationale_id : s.rationale_en}`);
  }

  lines.push("");
  lines.push("EVIDENCE (verbatim quotes with locators):");
  for (const e of rev?.evidence_items || []) {
    lines.push(`- [${e.location_ref}] (${e.indicator_code}, ${e.resolution_status}) "${e.quoted_text}"`);
  }

  lines.push("");
  lines.push("VALUATION SCENARIOS (IDR):");
  for (const v of state.valuationScenarios || []) {
    if (v.technology_id !== tech.id) continue;
    lines.push(
      `- ${v.scenario_name}: ${v.indicative_value_formatted}` +
        (v.range_min_idr ? ` (P10 ${Math.round(v.range_min_idr)}, P90 ${Math.round(v.range_max_idr)})` : "")
    );
  }
  return { tech, text: lines.join("\n") };
}

function systemPrompt(lang: string, context: string, agentFocus?: string) {
  const language = lang === "id" ? "Bahasa Indonesia" : "English";
  return [
    "You are the TechVal AI Advisor, powered by Meta Muse models.",
    "You help technology transfer officers, examiners and investors understand one technology assessment.",
    agentFocus ? `SPECIALTY FOCUS: ${agentFocus}` : "",
    "RULES:",
    "1. Answer ONLY from the CONTEXT below. If the context does not contain the answer, say so plainly. Never invent numbers, quotes or sources.",
    "2. Cite evidence with its locator exactly as written, for example [page:2] or [para:4].",
    "3. Technology score, TRL and commercialization readiness are never converted into Rupiah. If asked to do so, explain that WIPO methods value money from cash flows, not from scores.",
    "4. Money values come only from the VALUATION SCENARIOS list. Do not compute new ones.",
    "5. If the case is a synthetic demonstration, say that it is not a real-world claim when relevant.",
    `6. Reply in ${language}, in short paragraphs or a short list. At most 180 words.`,
    "",
    "CONTEXT:",
    context,
  ].join("\n");
}

export async function POST(req: NextRequest) {
  let body: any;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body." }, { status: 400 });
  }

  const question = String(body.question || "").trim().slice(0, 1000);
  if (!question) {
    return NextResponse.json({ detail: "Question is required." }, { status: 400 });
  }
  const lang = body.lang === "en" ? "en" : "id";
  const history: ChatTurn[] = Array.isArray(body.history)
    ? body.history
        .filter((h: any) => (h?.role === "user" || h?.role === "assistant") && typeof h.content === "string")
        .slice(-6)
        .map((h: any) => ({ role: h.role, content: h.content.slice(0, 1500) }))
    : [];

  const apiKey = (body.api_key_override || process.env.META_AI_API_KEY || "").trim();
  if (!apiKey) {
    return NextResponse.json(
      { detail: "META_AI_API_KEY is not configured in .env.local." },
      { status: 400 }
    );
  }
  const baseUrl = process.env.META_AI_BASE_URL || "https://api.meta.ai/v1";
  const agentSpec =
    MUSE_AGENTS.find((a) => a.node === body.agent_node && a.chatCompatible) ||
    MUSE_AGENTS.find((a) => a.model === body.model && a.chatCompatible);
  const model =
    agentSpec?.model || body.model || process.env.META_AI_DEFAULT_MODEL || "muse-spark-1.3";
  const focus = agentSpec
    ? lang === "id"
      ? agentSpec.advisor_prompt_id
      : agentSpec.advisor_prompt_en
    : undefined;

  const state = await loadWebStateAsync();
  const { tech, text } = buildContext(state, body.technology_id, lang);
  if (!tech) {
    return NextResponse.json({ detail: "No technology available." }, { status: 404 });
  }

  const started = Date.now();
  let upstream: Response;
  try {
    upstream = await fetch(`${baseUrl}/chat/completions`, {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        messages: [
          { role: "system", content: systemPrompt(lang, text, focus) },
          ...history,
          { role: "user", content: question },
        ],
        max_tokens: 4000,
        temperature: 0.2,
      }),
      signal: AbortSignal.timeout(55000),
    });
  } catch (err: any) {
    return NextResponse.json(
      { detail: `Could not reach Muse Spark: ${err?.message || "network error"}` },
      { status: 502 }
    );
  }

  if (!upstream.ok) {
    const errText = (await upstream.text()).slice(0, 400);
    return NextResponse.json(
      { detail: `Muse Spark returned HTTP ${upstream.status}: ${errText}` },
      { status: 502 }
    );
  }

  const json = await upstream.json();
  const answer: string = json.choices?.[0]?.message?.content?.trim() || "";
  if (!answer) {
    const reason = json.choices?.[0]?.finish_reason;
    return NextResponse.json(
      { detail: `Muse Spark returned an empty answer (finish_reason: ${reason || "unknown"}).` },
      { status: 502 }
    );
  }

  const allowed = new Set<string>(
    (state.revisions.flatMap((r: any) => r.evidence_items || []) as any[]).map((e) => e.location_ref)
  );
  const cited = Array.from(new Set(Array.from(answer.matchAll(/\[((?:page|para|table):\d+)\]/g)).map((m) => m[1])));
  const unverified = cited.filter((c) => !allowed.has(c));

  return NextResponse.json({
    answer,
    model: json.model || model,
    latency_ms: Date.now() - started,
    total_tokens: json.usage?.total_tokens ?? null,
    technology_code: tech.code,
    citations_verified: cited.filter((c) => allowed.has(c)),
    citations_unverified: unverified,
  });
}
