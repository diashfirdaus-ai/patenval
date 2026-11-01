"use client";

import React from "react";
import { MUSE_AGENTS } from "@/lib/muse-agents";

export function AgentRoster({ id }: { id: boolean }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {MUSE_AGENTS.map((a) => (
        <div
          key={a.node}
          className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-4 transition duration-200 hover:border-slate-300"
        >
          <div>
            <div className="flex items-center justify-between gap-2 text-xs">
              <span className="font-semibold text-blue-700">
                #{a.index} · {id ? a.name_id : a.name_en}
              </span>
              <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-[11px] text-slate-700">
                {a.model}
              </span>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              {id ? a.role_id : a.role_en}
            </p>
          </div>
          <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-2 text-[11px] text-slate-400">
            <span className="font-mono">{a.node}</span>
            <span className="font-mono">{a.endpoint}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
