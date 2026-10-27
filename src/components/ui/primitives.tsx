"use client";

import React from "react";
import { cn, formatNormalizedScore } from "@/lib/utils";
import type { FourSeparateOutputsSummary } from "@/lib/api-types";
import { useAppState } from "@/lib/i18n";
import { ShieldAlert, CheckCircle2, AlertTriangle, Sparkles } from "lucide-react";

export function Card({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-slate-200 bg-white p-5 sm:p-6 shadow-sm",
        className
      )}
    >
      {children}
    </div>
  );
}

export function Badge({
  variant = "default",
  className,
  children,
}: {
  variant?: "default" | "success" | "warning" | "danger" | "info" | "outline";
  className?: string;
  children: React.ReactNode;
}) {
  const styles: Record<string, string> = {
    default: "bg-slate-100 text-slate-800 border-slate-200",
    success: "bg-emerald-50 text-emerald-800 border-emerald-200",
    warning: "bg-amber-50 text-amber-800 border-amber-300",
    danger: "bg-rose-50 text-rose-800 border-rose-200",
    info: "bg-blue-50 text-blue-800 border-blue-200",
    outline: "bg-transparent text-slate-700 border-slate-300",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap",
        styles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}

export function Button({
  variant = "primary",
  size = "md",
  className,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "outline" | "danger";
  size?: "sm" | "md" | "lg";
}) {
  const variants: Record<string, string> = {
    primary: "bg-blue-700 text-white hover:bg-blue-800 disabled:bg-blue-300",
    secondary: "bg-slate-800 text-white hover:bg-slate-900 disabled:bg-slate-400",
    outline:
      "border border-slate-300 bg-white text-slate-800 hover:bg-slate-50 disabled:opacity-50",
    danger: "bg-rose-600 text-white hover:bg-rose-700 disabled:bg-rose-300",
  };
  const sizes: Record<string, string> = {
    sm: "px-3 py-2 text-sm",
    md: "px-4 py-2.5 text-sm",
    lg: "px-6 py-3 text-base",
  };
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-xl font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function ProgressBar({ value, color = "bg-blue-600" }: { value: number; color?: string }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden" aria-hidden="true">
      <div className={cn("h-full rounded-full", color)} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
      <div className="text-lg font-semibold text-slate-900">{title}</div>
      {description && <p className="max-w-md text-sm text-slate-600">{description}</p>}
      {action}
    </div>
  );
}

export function Collapsible({
  title,
  children,
  defaultOpen = false,
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  return (
    <details open={defaultOpen} className="group rounded-2xl border border-slate-200 bg-white">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-5 py-3.5 text-sm font-semibold text-slate-800 hover:bg-slate-50 rounded-2xl">
        {title}
        <span className="text-slate-400 transition-transform group-open:rotate-180" aria-hidden="true">▾</span>
      </summary>
      <div className="border-t border-slate-100 p-5">{children}</div>
    </details>
  );
}

export function FourOutputsGrid({
  outputs,
  isDemo = false,
  expertStatus = "unreviewed_draft",
}: {
  outputs: FourSeparateOutputsSummary;
  isDemo?: boolean;
  expertStatus?: string;
}) {
  const { t } = useAppState();
  const techScore = (outputs.technology_assessment.normalized_score ?? 0) * 100;
  const commScore = (outputs.commercialization_readiness.normalized_score ?? 0) * 100;
  const evidence = outputs.evidence_completeness.weighted_completeness_score * 100;
  const trl = outputs.technology_assessment.trl_native_1_to_9;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        {isDemo && (
          <Badge variant="warning">
            <Sparkles className="h-3 w-3" aria-hidden="true" /> {t.fourOutputs.demoBadge}
          </Badge>
        )}
        {outputs.technology_assessment.is_provisional && (
          <Badge variant="warning">
            <AlertTriangle className="h-3 w-3" aria-hidden="true" /> {t.fourOutputs.provisionalBadge}
          </Badge>
        )}
        {expertStatus === "approved" ? (
          <Badge variant="success">
            <CheckCircle2 className="h-3 w-3" aria-hidden="true" /> {t.common.approvedStatus}
          </Badge>
        ) : expertStatus === "stale" ? (
          <Badge variant="danger">{t.common.staleStatus}</Badge>
        ) : (
          <Badge variant="outline">{t.common.draftWatermark}</Badge>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="space-y-3 p-5 sm:p-5">
          <div>
            <div className="text-sm font-semibold text-slate-900">{t.fourOutputs.techAssessment}</div>
            <div className="text-xs text-slate-500">{t.fourOutputs.techHint}</div>
          </div>
          <div className="text-3xl font-bold text-slate-900">{techScore.toFixed(0)}%</div>
          <ProgressBar value={techScore} color="bg-blue-600" />
          <div className="text-xs text-slate-600">
            NASA TRL: <span className="font-semibold text-blue-700">{trl ? `${trl} / 9` : "-"}</span>
          </div>
        </Card>

        <Card className="space-y-3 p-5 sm:p-5">
          <div>
            <div className="text-sm font-semibold text-slate-900">{t.fourOutputs.commReadiness}</div>
            <div className="text-xs text-slate-500">{t.fourOutputs.commHint}</div>
          </div>
          <div className="text-3xl font-bold text-slate-900">{commScore.toFixed(0)}%</div>
          <ProgressBar value={commScore} color="bg-indigo-600" />
        </Card>

        <Card className="space-y-3 p-5 sm:p-5">
          <div>
            <div className="text-sm font-semibold text-slate-900">{t.fourOutputs.econValuation}</div>
            <div className="text-xs text-slate-500">{t.fourOutputs.econHint}</div>
          </div>
          <div className="text-2xl font-bold text-emerald-700 break-words">
            {outputs.economic_valuation.dcf_base_formatted}
          </div>
        </Card>

        <Card className="space-y-3 p-5 sm:p-5">
          <div>
            <div className="text-sm font-semibold text-slate-900">{t.fourOutputs.evidenceCompleteness}</div>
            <div className="text-xs text-slate-500">{t.fourOutputs.evidenceHint}</div>
          </div>
          <div className="text-3xl font-bold text-slate-900">{evidence.toFixed(0)}%</div>
          <ProgressBar value={evidence} color="bg-amber-500" />
          <div className="text-xs text-slate-600">
            {outputs.evidence_completeness.observed_count} {t.common.observed.toLowerCase()} ·{" "}
            {outputs.evidence_completeness.missing_count} {t.common.missing.toLowerCase()}
          </div>
        </Card>
      </div>

      <p className="flex items-start gap-2 text-xs text-slate-500">
        <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        {t.fourOutputs.bannerTitle}
      </p>
    </div>
  );
}
