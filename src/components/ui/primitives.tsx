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
        "rounded-lg border border-slate-200 bg-white p-5 shadow-sm",
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
        "inline-flex items-center gap-1 rounded-md border px-2.5 py-0.5 text-xs font-semibold",
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
    sm: "px-2.5 py-1.5 text-xs",
    md: "px-3.5 py-2 text-sm",
    lg: "px-5 py-2.5 text-base",
  };
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-md font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500",
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
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-blue-200 bg-blue-50/70 px-3.5 py-2 text-xs text-blue-900">
        <div className="flex items-center gap-2 font-semibold">
          <ShieldAlert className="h-4 w-4 text-blue-700" />
          <span>{t.fourOutputs.bannerTitle}</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {isDemo && (
            <Badge variant="warning">
              <Sparkles className="h-3 w-3" /> {t.fourOutputs.demoBadge}
            </Badge>
          )}
          {outputs.technology_assessment.is_provisional && (
            <Badge variant="warning">
              <AlertTriangle className="h-3 w-3" /> {t.fourOutputs.provisionalBadge}
            </Badge>
          )}
          {expertStatus === "approved" ? (
            <Badge variant="success">
              <CheckCircle2 className="h-3 w-3" /> {t.common.approvedStatus}
            </Badge>
          ) : expertStatus === "stale" ? (
            <Badge variant="danger">{t.common.staleStatus}</Badge>
          ) : (
            <Badge variant="outline">{t.common.draftWatermark}</Badge>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
        <Card className="border-l-4 border-l-blue-600 p-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            {t.fourOutputs.techAssessment}
          </div>
          <div className="mt-1.5 text-xl font-bold text-slate-900">
            {formatNormalizedScore(outputs.technology_assessment.normalized_score)}
          </div>
          <div className="mt-1 text-xs text-slate-600">
            NASA TRL (1–9 Native):{" "}
            <span className="font-semibold text-blue-700">
              {outputs.technology_assessment.trl_native_1_to_9
                ? `TRL ${outputs.technology_assessment.trl_native_1_to_9} / 9`
                : "Unavailable"}
            </span>
          </div>
        </Card>

        <Card className="border-l-4 border-l-indigo-600 p-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            {t.fourOutputs.commReadiness}
          </div>
          <div className="mt-1.5 text-xl font-bold text-slate-900">
            {formatNormalizedScore(outputs.commercialization_readiness.normalized_score)}
          </div>
          <div className="mt-1 text-xs text-slate-600">
            Market, Regulatory, Supply Chain & IP Readiness
          </div>
        </Card>

        <Card className="border-l-4 border-l-emerald-600 p-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            {t.fourOutputs.econValuation}
          </div>
          <div className="mt-1.5 text-lg font-bold text-emerald-800">
            {outputs.economic_valuation.dcf_base_formatted}
          </div>
          <div className="mt-1 text-[11px] text-slate-600">
            WIPO Base DCF (IDR) • Independent of Scores
          </div>
        </Card>

        <Card className="border-l-4 border-l-amber-600 p-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            {t.fourOutputs.evidenceCompleteness}
          </div>
          <div className="mt-1.5 text-xl font-bold text-slate-900">
            {(outputs.evidence_completeness.weighted_completeness_score * 100).toFixed(1)}%
          </div>
          <div className="mt-1 text-xs text-slate-600">
            Obs: {outputs.evidence_completeness.observed_count} | Miss:{" "}
            {outputs.evidence_completeness.missing_count} | N/A:{" "}
            {outputs.evidence_completeness.not_applicable_count}
          </div>
        </Card>
      </div>
    </div>
  );
}
