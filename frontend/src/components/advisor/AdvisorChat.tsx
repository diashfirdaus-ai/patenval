"use client";

import React, { useEffect, useRef, useState } from "react";
import { Send, ShieldCheck, AlertTriangle, Loader2 } from "lucide-react";
import { useAppState } from "@/lib/i18n";
import { apiClient } from "@/lib/api-client";
import { MUSE_AGENTS } from "@/lib/muse-agents";

interface Message {
  role: "user" | "assistant";
  content: string;
  meta?: {
    model: string;
    latency_ms: number;
    verified: string[];
    unverified: string[];
  };
  error?: boolean;
}

export function AdvisorChat() {
  const { lang, selectedTechId } = useAppState();
  const id = lang === "id";
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [agentNode, setAgentNode] = useState<string>("evidence_extraction");
  const chatAgents = MUSE_AGENTS.filter((a) => a.chatCompatible);
  const activeAgent = chatAgents.find((a) => a.node === agentNode) || chatAgents[0];
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  const suggestions = id
    ? [
        "Mengapa teknologi ini dinilai TRL 6?",
        "Apa bukti terkuat untuk kesiapan pasar?",
        "Bisakah skor teknologi diubah menjadi Rupiah?",
        "Apa risiko terbesar sebelum lisensi?",
      ]
    : [
        "Why is this technology rated TRL 6?",
        "What is the strongest evidence for market readiness?",
        "Can the technology score be converted into Rupiah?",
        "What is the biggest risk before licensing?",
      ];

  const send = async (text: string) => {
    const question = text.trim();
    if (!question || busy) return;
    const history = messages
      .filter((m) => !m.error)
      .map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setBusy(true);
    try {
      const res = await apiClient.askAdvisor({
        question,
        lang,
        technology_id: selectedTechId,
        agent_node: agentNode,
        history,
      });
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer,
          meta: {
            model: res.model,
            latency_ms: res.latency_ms,
            verified: res.citations_verified,
            unverified: res.citations_unverified,
          },
        },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: err?.message || "Request failed.", error: true },
      ]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-[34rem] flex-col rounded-2xl border border-slate-200 bg-white">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-5 py-3 text-xs">
        <label className="font-medium text-slate-600">
          {id ? "Pilih agen:" : "Select agent:"}
        </label>
        <select
          value={agentNode}
          onChange={(e) => setAgentNode(e.target.value)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-800"
        >
          {chatAgents.map((a) => (
            <option key={a.node} value={a.node}>
              #{a.index} {id ? a.name_id : a.name_en} — {a.model}
            </option>
          ))}
        </select>
      </div>
      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        {messages.length === 0 && (
          <div>
            <p className="text-sm text-slate-600">
              {id
                ? "Tanyakan apa saja tentang kasus yang sedang dipilih. Jawaban hanya berdasarkan skor, bukti, dan valuasi yang tersimpan."
                : "Ask anything about the selected case. Answers use only the stored scores, evidence, and valuation."}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {suggestions.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => send(s)}
                  className="rounded-full border border-slate-200 px-3.5 py-1.5 text-sm text-slate-700 transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-800"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                m.role === "user"
                  ? "bg-blue-600 text-white"
                  : m.error
                  ? "border border-rose-200 bg-rose-50 text-rose-800"
                  : "bg-slate-100 text-slate-800"
              }`}
            >
              <div className="whitespace-pre-wrap">{m.content}</div>
              {m.meta && (
                <div className="mt-3 space-y-1 border-t border-slate-200 pt-2 text-xs text-slate-500">
                  {m.meta.verified.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 text-emerald-700">
                      <ShieldCheck className="h-3.5 w-3.5" />
                      {id ? "Sitasi cocok dengan bukti:" : "Citations match evidence:"}
                      {m.meta.verified.map((c) => (
                        <span key={c} className="rounded bg-emerald-50 px-1.5 py-0.5">[{c}]</span>
                      ))}
                    </div>
                  )}
                  {m.meta.unverified.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 text-amber-700">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      {id ? "Sitasi tidak ditemukan:" : "Citations not found:"}
                      {m.meta.unverified.map((c) => (
                        <span key={c} className="rounded bg-amber-50 px-1.5 py-0.5">[{c}]</span>
                      ))}
                    </div>
                  )}
                  <div>
                    {m.meta.model} · {(m.meta.latency_ms / 1000).toFixed(1)}s
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {busy && (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            {id
              ? `${activeAgent.model} sedang menjawab…`
              : `${activeAgent.model} is answering…`}
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex items-center gap-2 border-t border-slate-200 p-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          maxLength={1000}
          placeholder={id ? "Tulis pertanyaan…" : "Write a question…"}
          className="flex-1 rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-200"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
        >
          <Send className="h-4 w-4" />
          {id ? "Kirim" : "Send"}
        </button>
      </form>
    </div>
  );
}
