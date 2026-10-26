"use client";

import React, { useEffect, useState } from "react";
import { useAppState } from "@/lib/i18n";
import { apiClient } from "@/lib/api-client";
import type { ValuationScenarioItem } from "@/lib/api-types";
import { Card, Badge, Button } from "@/components/ui/primitives";
import { formatIdr } from "@/lib/utils";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { Calculator, AlertTriangle, CheckCircle2, Play } from "lucide-react";

export default function ValuationStudioPage() {
  const { lang, t, selectedTechId } = useAppState();
  const [scenarios, setScenarios] = useState<ValuationScenarioItem[]>([]);
  const [activeScenario, setActiveScenario] = useState<ValuationScenarioItem | null>(
    null
  );
  const [discountRate, setDiscountRate] = useState<number>(0.15);
  const [attributionMode, setAttributionMode] = useState<string>(
    "documented_attribution_factor"
  );
  const [attributionFactor, setAttributionFactor] = useState<number>(0.75);
  const [riskMode, setRiskMode] = useState<string>("in_discount_rate");
  const [mcSeed, setMcSeed] = useState<number>(20260417);
  const [calculating, setCalculating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadValuations = async () => {
    if (!selectedTechId) return;
    setError(null);
    try {
      const list = await apiClient.listValuationScenarios(selectedTechId);
      setScenarios(list);
      const dcfBase =
        list.find((s) => s.approach === "dcf" && s.scenario_case === "base") ||
        list[0] ||
        null;
      setActiveScenario(dcfBase);
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    loadValuations();
  }, [selectedTechId]);

  const handleRunCustomDcf = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTechId) return;
    setCalculating(true);
    setError(null);
    try {
      const created = await apiClient.calculateDcf({
        technology_id: selectedTechId,
        scenario_name: `Interactive WIPO DCF (r=${(discountRate * 100).toFixed(1)}%)`,
        scenario_case: "base",
        revenues_idr: [
          1200000000, 2500000000, 4200000000, 5800000000, 7000000000,
        ],
        operating_costs_idr: [
          750000000, 1400000000, 2150000000, 2850000000, 3400000000,
        ],
        capex_idr: [350000000, 150000000, 100000000, 100000000, 100000000],
        working_capital_changes_idr: [50000000, 75000000, 90000000, 80000000, 60000000],
        tax_rate: 0.22,
        discount_rate: Number(discountRate),
        attribution_mode: attributionMode,
        attribution_factor:
          attributionMode === "documented_attribution_factor"
            ? Number(attributionFactor)
            : null,
        attribution_documentation:
          "Documented technology contribution factor per pilot bill-of-materials.",
        risk_treatment_mode: riskMode,
        run_sensitivity: true,
        monte_carlo_seed: Number(mcSeed),
        monte_carlo_iterations: 1000,
      });
      setActiveScenario(created);
      await loadValuations();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCalculating(false);
    }
  };

  const annualRows =
    activeScenario?.calculation_breakdown_json?.annual_breakdown || [];
  const mcStats = activeScenario?.monte_carlo_json || null;
  const sensRows = activeScenario?.sensitivity_json || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{t.nav.valuation}</h1>
        <p className="text-sm text-slate-600">
          {lang === "id"
            ? "Dimensi 3: Valuasi Ekonomi Deterministik dalam Rupiah (IDR) berdasarkan WIPO IP Valuation Basics (Bagian 2–5)."
            : "Dimension 3: Deterministic Economic Valuation in Indonesian Rupiah (IDR) grounded in WIPO IP Valuation Basics (Sections 2–5)."}
        </p>
      </div>

      <div className="rounded-md border border-emerald-300 bg-emerald-50/70 px-4 py-2.5 text-xs text-emerald-950 flex items-center justify-between">
        <span>
          <strong>Methodological Firewall:</strong> {t.fourOutputs.scoreConversionNotice}
        </span>
        <Badge variant="success">Pure Financial Engine (IDR)</Badge>
      </div>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 p-3 text-xs text-rose-800">
          {t.common.errorPrefix} {error}
        </div>
      )}

      {/* Scenario Selector Cards */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
        {scenarios.map((scen) => {
          const isSelected = activeScenario?.id === scen.id;
          return (
            <div
              key={scen.id}
              onClick={() => setActiveScenario(scen)}
              className={`cursor-pointer rounded-lg border p-4 transition ${
                isSelected
                  ? "border-blue-600 bg-blue-50/50 shadow-sm"
                  : "border-slate-200 bg-white hover:border-slate-300"
              }`}
            >
              <div className="flex items-center justify-between">
                <Badge variant="info">{scen.approach.toUpperCase()}</Badge>
                <span className="text-[11px] font-semibold uppercase text-slate-500">
                  {scen.scenario_case}
                </span>
              </div>
              <div className="mt-2 font-bold text-xs text-slate-800">
                {scen.scenario_name}
              </div>
              <div className="mt-1.5 text-base font-bold text-emerald-800">
                {scen.indicative_value_formatted}
              </div>
              <div className="mt-1 text-[10px] text-slate-500 truncate">
                {scen.wipo_reference_locator}
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Interactive DCF & Monte Carlo Controls */}
        <Card className="lg:col-span-1 space-y-4">
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <Calculator className="h-4 w-4 text-emerald-700" />
            <span>WIPO DCF & Attribution Simulator</span>
          </div>

          <form onSubmit={handleRunCustomDcf} className="space-y-3 text-xs">
            <div>
              <label className="block font-semibold text-slate-700">
                Discount Rate ($r$)
              </label>
              <input
                type="number"
                step="0.01"
                min="-0.5"
                max="1.0"
                value={discountRate}
                onChange={(e) => setDiscountRate(Number(e.target.value))}
                className="mt-1 w-full rounded border border-slate-300 px-2.5 py-1.5 font-mono"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700">
                IP Attribution Mode (No Double Counting)
              </label>
              <select
                value={attributionMode}
                onChange={(e) => setAttributionMode(e.target.value)}
                className="mt-1 w-full rounded border border-slate-300 px-2.5 py-1.5"
              >
                <option value="documented_attribution_factor">
                  Documented Attribution Factor (&alpha; &in; (0, 1])
                </option>
                <option value="direct_cash_flows">
                  Direct Technology-Specific Cash Flows (&alpha; = 1.0)
                </option>
              </select>
            </div>

            {attributionMode === "documented_attribution_factor" && (
              <div>
                <label className="block font-semibold text-slate-700">
                  Technology Attribution Factor (&alpha;)
                </label>
                <input
                  type="number"
                  step="0.05"
                  min="0.05"
                  max="1.0"
                  value={attributionFactor}
                  onChange={(e) => setAttributionFactor(Number(e.target.value))}
                  className="mt-1 w-full rounded border border-slate-300 px-2.5 py-1.5 font-mono"
                />
              </div>
            )}

            <div>
              <label className="block font-semibold text-slate-700">
                Risk Treatment Mode
              </label>
              <select
                value={riskMode}
                onChange={(e) => setRiskMode(e.target.value)}
                className="mt-1 w-full rounded border border-slate-300 px-2.5 py-1.5"
              >
                <option value="in_discount_rate">
                  Risk-Adjusted Discount Rate Only
                </option>
                <option value="in_cash_flows">
                  Probability-Weighted Cash Flows Only
                </option>
                <option value="both">
                  Both (Triggers WIPO Double-Counting Warning)
                </option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-700">
                Deterministic Monte Carlo Seed
              </label>
              <input
                type="number"
                value={mcSeed}
                onChange={(e) => setMcSeed(Number(e.target.value))}
                className="mt-1 w-full rounded border border-slate-300 px-2.5 py-1.5 font-mono"
              />
            </div>

            <Button type="submit" disabled={calculating} className="w-full">
              <Play className="h-3.5 w-3.5" />
              {calculating
                ? "Computing Deterministic NPV..."
                : "Run Deterministic DCF + Monte Carlo"}
            </Button>
          </form>
        </Card>

        {/* Active Scenario Breakdown & Charts */}
        <Card className="lg:col-span-2 space-y-4">
          {activeScenario ? (
            <>
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
                <div>
                  <h2 className="text-base font-bold text-slate-900">
                    {activeScenario.scenario_name}
                  </h2>
                  <p className="text-xs text-slate-500">
                    {activeScenario.wipo_reference_locator} • Attribution:{" "}
                    {activeScenario.attribution_mode} (
                    {activeScenario.attribution_factor ?? 1.0})
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-xl font-bold text-emerald-800">
                    {activeScenario.indicative_value_formatted}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Indicative Present Value (IDR)
                  </div>
                </div>
              </div>

              {activeScenario.double_counting_flagged && (
                <div className="rounded border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span>{activeScenario.double_counting_warning}</span>
                </div>
              )}

              {annualRows.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Annual Attributed & Discounted Cash Flows (IDR)
                  </h3>
                  <div className="h-56 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={annualRows}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="year" tickFormatter={(v) => `Year ${v}`} />
                        <YAxis
                          tickFormatter={(v) => `${(Number(v) / 1e9).toFixed(1)}B`}
                        />
                        <Tooltip formatter={(val: any) => formatIdr(Number(val))} />
                        <Bar
                          dataKey="attributed_fcf_idr"
                          name="Attributed FCF (IDR)"
                          fill="#3b82f6"
                        />
                        <Bar
                          dataKey="present_value_idr"
                          name="Present Value (IDR)"
                          fill="#059669"
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Monte Carlo & Sensitivity */}
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {mcStats && (
                  <div className="rounded border border-slate-200 bg-slate-50 p-3 text-xs space-y-1.5">
                    <div className="font-bold text-slate-900 flex items-center justify-between">
                      <span>Seeded Monte Carlo (N={mcStats.iterations})</span>
                      <Badge variant="outline">Seed: {mcStats.seed}</Badge>
                    </div>
                    <div>
                      P10 (Conservative):{" "}
                      <strong className="text-slate-900">
                        {formatIdr(mcStats.p10_idr)}
                      </strong>
                    </div>
                    <div>
                      P50 (Median):{" "}
                      <strong className="text-emerald-800">
                        {formatIdr(mcStats.p50_idr)}
                      </strong>
                    </div>
                    <div>
                      P90 (Upside):{" "}
                      <strong className="text-blue-800">
                        {formatIdr(mcStats.p90_idr)}
                      </strong>
                    </div>
                    <div className="text-[11px] text-slate-500">
                      Mean: {formatIdr(mcStats.mean_idr)} | Std:{" "}
                      {formatIdr(mcStats.std_idr)}
                    </div>
                  </div>
                )}

                {sensRows.length > 0 && (
                  <div className="rounded border border-slate-200 bg-slate-50 p-3 text-xs space-y-1.5">
                    <div className="font-bold text-slate-900">
                      One-at-a-Time Sensitivity Analysis
                    </div>
                    {sensRows.map((sr: any, i: number) => (
                      <div key={i} className="border-t border-slate-200 pt-1">
                        <div className="font-semibold text-slate-700">{sr.label}</div>
                        <div className="text-[11px] text-slate-600">
                          Low: {formatIdr(sr.downside_npv_idr)} | High:{" "}
                          {formatIdr(sr.upside_npv_idr)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="py-8 text-center text-sm text-slate-500">
              Select a valuation scenario above to inspect its breakdown.
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
