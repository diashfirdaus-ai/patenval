"use client";

import React from "react";
import { MUSE_AGENTS } from "@/lib/muse-agents";

export function AgentRoster({ id }: { id: boolean }) {
  return (
    <div className="grid gap-5 sm:grid-cols-2">
      {MUSE_AGENTS.map((a) => (
        <div
          key={a.node}
          className="rounded-2xl border border-slate-200 bg-white p-6 transition duration-200 hover:border-slate-300 hover:shadow-sm"
        >
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="text-xl font-semibold text-slate-900 sm:text-2xl">
              {a.index}. {id ? a.name_id : a.name_en}
            </h3>
            <span className="rounded-lg bg-blue-50 px-3 py-1 font-mono text-sm font-semibold text-blue-700">
              {a.model}
            </span>
          </div>
          <p className="mt-3 text-base leading-relaxed text-slate-600 sm:text-lg">
            {id ? a.role_id : a.role_en}
          </p>
        </div>
      ))}
    </div>
  );
}
