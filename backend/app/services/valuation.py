from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional
import numpy as np


WIPO_LOCATORS = {
    "dcf": "WIPO IP Valuation Basics Guide, Section 3.3 (Income Method — Discounted Cash Flow), pp. 26-34",
    "relief_from_royalty": "WIPO IP Valuation Basics Guide, Section 3.3.2 (Relief-from-Royalty Method), pp. 31-34",
    "cost": "WIPO IP Valuation Basics Guide, Section 3.1 (Cost Method — Reproduction & Replacement Cost), pp. 18-21",
    "market_comparables": "WIPO IP Valuation Basics Guide, Section 3.2 (Market Method — Comparable Transactions), pp. 22-25",
}


def format_idr(value: Optional[float]) -> str:
    """Formats a float value for presentation in Indonesian Rupiah (IDR), rounded only at presentation."""
    if value is None:
        return "Unavailable"
    dec = Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    sign = "-" if dec < 0 else ""
    formatted = f"{abs(int(dec)):,}".replace(",", ".")
    return f"{sign}Rp {formatted}"


def _guard_no_score_inference(inputs: Dict[str, Any]) -> None:
    """
    Enforces the scientific rule:
    Never convert assessment scores into monetary values, and never infer tax rates,
    discount rates, or economic life from assessment/readiness/TRL scores.
    """
    forbidden_keys = {
        "infer_from_assessment_score",
        "score_to_monetary_multiplier",
        "trl_discount_rate_lookup",
        "assessment_score_input",
    }
    present = forbidden_keys.intersection(set(inputs.keys()))
    if present:
        raise ValueError(
            f"Forbidden score-to-valuation inference parameter(s) detected: {sorted(present)}. "
            "Assessment scores and TRL must never be converted into monetary values or financial parameters."
        )


def calculate_dcf_valuation(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic Discounted Cash Flow (DCF) calculation in IDR.
    Preserves full internal floating-point precision and rounds only for presentation.

    Required inputs:
    - `economic_life_years` (int >= 1)
    - `discount_rate` (float >= 0.0, e.g., 0.14 for 14%)
    - `tax_rate` (float in [0.0, 1.0), e.g., 0.22 for 22% Indonesian corporate tax)
    - `year_zero_investment_idr` (float >= 0.0, treated separately at t=0 without discounting)
    - `annual_projections` (list of dicts for years 1..N with `ebitda_or_operating_cf_idr`, `depreciation_idr` (optional),
       `capex_idr`, `working_capital_change_idr`)
    - `attribution_mode`: "direct_cash_flows" | "documented_attribution_factor"
    - `attribution_factor`: float in (0, 1] if mode == "documented_attribution_factor"
    - `attribution_documentation`: required non-empty string if mode == "documented_attribution_factor"
    - `terminal_value_enabled`: bool (defaults to False)
    - `risk_treatment_mode`: "in_cash_flows" | "in_discount_rate" | "both"
    """
    _guard_no_score_inference(inputs)

    economic_life = int(inputs.get("economic_life_years", 0))
    if economic_life < 1 or economic_life > 40:
        raise ValueError(f"economic_life_years must be between 1 and 40, got {economic_life}.")

    discount_rate = float(inputs.get("discount_rate", -1.0))
    if discount_rate < 0.0 or discount_rate > 2.0:
        raise ValueError(f"discount_rate must be non-negative (0.0 <= r <= 2.0), got {discount_rate}.")

    tax_rate = float(inputs.get("tax_rate", -1.0))
    if tax_rate < 0.0 or tax_rate >= 1.0:
        raise ValueError(f"tax_rate must be in [0.0, 1.0), got {tax_rate}.")

    year_zero_investment = float(inputs.get("year_zero_investment_idr", 0.0))
    if year_zero_investment < 0.0:
        raise ValueError("year_zero_investment_idr cannot be negative; enter positive outlay amount.")

    attribution_mode = str(inputs.get("attribution_mode", "direct_cash_flows"))
    raw_attr_factor = inputs.get("attribution_factor")
    attr_doc = str(inputs.get("attribution_documentation") or "").strip()

    if attribution_mode == "direct_cash_flows":
        if raw_attr_factor is not None and abs(float(raw_attr_factor) - 1.0) > 1e-9:
            raise ValueError(
                "Duplicate attribution prevented: when attribution_mode is 'direct_cash_flows', "
                "cash flows are already strictly technology-attributable and cannot also apply a fractional attribution_factor."
            )
        effective_attr_factor = 1.0
    elif attribution_mode == "documented_attribution_factor":
        if raw_attr_factor is None:
            raise ValueError("attribution_factor is required when attribution_mode is 'documented_attribution_factor'.")
        effective_attr_factor = float(raw_attr_factor)
        if not (0.0 < effective_attr_factor <= 1.0):
            raise ValueError(f"attribution_factor must be in (0.0, 1.0], got {effective_attr_factor}.")
        if len(attr_doc) < 10:
            raise ValueError(
                "Documented attribution rationale (at least 10 characters) is required when using an attribution_factor."
            )
    else:
        raise ValueError(f"Unsupported attribution_mode: {attribution_mode}")

    # Check risk treatment and flag potential double counting
    risk_treatment_mode = str(inputs.get("risk_treatment_mode", "in_discount_rate"))
    cf_haircut = float(inputs.get("cash_flow_probability_haircut", 0.0))
    dr_risk_premium = float(inputs.get("discount_rate_technology_premium", 0.0))
    double_counting_flagged = False
    double_counting_warning: Optional[str] = None
    if risk_treatment_mode == "both" or (cf_haircut > 0.0 and dr_risk_premium > 0.0):
        double_counting_flagged = True
        double_counting_warning = (
            "POTENTIAL RISK DOUBLE COUNTING DETECTED: Risk adjustments are present in both cash-flow haircuts "
            "and a technology risk premium in the discount rate. WIPO valuation guidelines recommend accounting "
            "for technology commercialization risk in either scenario-weighted cash flows OR the discount rate, not both."
        )

    projections: List[Dict[str, Any]] = list(inputs.get("annual_projections", []))
    if len(projections) != economic_life:
        raise ValueError(
            f"Length of annual_projections ({len(projections)}) must match economic_life_years ({economic_life})."
        )

    schedule: List[Dict[str, Any]] = []
    pv_operating_fcf_sum = 0.0

    for idx, yr_input in enumerate(projections):
        year_num = idx + 1
        gross_ebitda = float(yr_input.get("ebitda_idr", yr_input.get("operating_cf_idr", 0.0)))
        depreciation = float(yr_input.get("depreciation_idr", 0.0))
        capex = float(yr_input.get("capex_idr", 0.0))
        delta_nwc = float(yr_input.get("working_capital_change_idr", 0.0))

        # Apply attribution factor to operating inflows before tax
        attributable_ebitda = gross_ebitda * effective_attr_factor
        attributable_depreciation = depreciation * effective_attr_factor
        ebit = attributable_ebitda - attributable_depreciation

        # Explicit corporate income taxes on positive EBIT
        taxes = max(0.0, ebit * tax_rate)
        nopat = ebit - taxes

        # Free Cash Flow to Technology = NOPAT + Depreciation - CapEx - Delta_NWC
        # Note: if cash_flow_probability_haircut is specified in 'in_cash_flows' mode, apply it
        raw_fcf = nopat + attributable_depreciation - capex - delta_nwc
        if cf_haircut > 0.0:
            fcf = raw_fcf * (1.0 - cf_haircut)
        else:
            fcf = raw_fcf

        discount_factor = (1.0 + discount_rate) ** year_num
        pv_fcf = fcf / discount_factor
        pv_operating_fcf_sum += pv_fcf

        schedule.append(
            {
                "year": year_num,
                "gross_ebitda_idr": gross_ebitda,
                "attributable_ebitda_idr": attributable_ebitda,
                "depreciation_idr": attributable_depreciation,
                "ebit_idr": ebit,
                "taxes_idr": taxes,
                "nopat_idr": nopat,
                "capex_idr": capex,
                "working_capital_change_idr": delta_nwc,
                "free_cash_flow_idr": fcf,
                "discount_factor": discount_factor,
                "present_value_fcf_idr": pv_fcf,
                "present_value_fcf_formatted": format_idr(pv_fcf),
            }
        )

    terminal_value_enabled = bool(inputs.get("terminal_value_enabled", False))
    pv_terminal_value = 0.0
    terminal_value_undiscounted = 0.0
    if terminal_value_enabled:
        tv_growth = float(inputs.get("terminal_growth_rate", 0.0))
        if discount_rate <= tv_growth:
            raise ValueError(
                "Terminal value calculation requires discount_rate > terminal_growth_rate."
            )
        final_fcf = schedule[-1]["free_cash_flow_idr"]
        terminal_value_undiscounted = (final_fcf * (1.0 + tv_growth)) / (discount_rate - tv_growth)
        pv_terminal_value = terminal_value_undiscounted / ((1.0 + discount_rate) ** economic_life)

    # Net Present Value (NPV) treats Year-0 investment separately at t=0
    npv_idr = pv_operating_fcf_sum + pv_terminal_value - year_zero_investment

    return {
        "approach": "dcf",
        "currency": "IDR",
        "indicative_value_idr": npv_idr,
        "indicative_value_formatted": format_idr(npv_idr),
        "pv_operating_cash_flows_idr": pv_operating_fcf_sum,
        "year_zero_investment_idr": year_zero_investment,
        "terminal_value_enabled": terminal_value_enabled,
        "terminal_value_undiscounted_idr": terminal_value_undiscounted,
        "pv_terminal_value_idr": pv_terminal_value,
        "attribution_mode": attribution_mode,
        "effective_attribution_factor": effective_attr_factor,
        "attribution_documentation": attr_doc,
        "discount_rate": discount_rate,
        "tax_rate": tax_rate,
        "economic_life_years": economic_life,
        "risk_treatment_mode": risk_treatment_mode,
        "double_counting_flagged": double_counting_flagged,
        "double_counting_warning": double_counting_warning,
        "annual_schedule": schedule,
        "wipo_reference_locator": WIPO_LOCATORS["dcf"],
    }


def calculate_cost_valuation(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic Cost Approach calculation (Reproduction / Replacement Cost Less Obsolescence) in IDR.
    """
    _guard_no_score_inference(inputs)

    rd_labor = float(inputs.get("rd_labor_cost_idr", 0.0))
    materials_prototyping = float(inputs.get("materials_prototyping_cost_idr", 0.0))
    testing_certification = float(inputs.get("testing_certification_cost_idr", 0.0))
    ip_legal_filing = float(inputs.get("ip_legal_filing_cost_idr", 0.0))
    overhead_engineering = float(inputs.get("engineering_overhead_cost_idr", 0.0))

    for name, val in [
        ("rd_labor_cost_idr", rd_labor),
        ("materials_prototyping_cost_idr", materials_prototyping),
        ("testing_certification_cost_idr", testing_certification),
        ("ip_legal_filing_cost_idr", ip_legal_filing),
        ("engineering_overhead_cost_idr", overhead_engineering),
    ]:
        if val < 0.0:
            raise ValueError(f"Cost component '{name}' cannot be negative, got {val}.")

    gross_replacement_cost = (
        rd_labor + materials_prototyping + testing_certification + ip_legal_filing + overhead_engineering
    )
    if gross_replacement_cost <= 0.0:
        raise ValueError("Total gross replacement cost must be greater than zero.")

    functional_obsolescence_rate = float(inputs.get("functional_obsolescence_rate", 0.0))
    economic_obsolescence_rate = float(inputs.get("economic_obsolescence_rate", 0.0))
    total_obsolescence_rate = functional_obsolescence_rate + economic_obsolescence_rate
    if not (0.0 <= total_obsolescence_rate < 1.0):
        raise ValueError(
            f"Combined obsolescence rate must be in [0.0, 1.0), got {total_obsolescence_rate}."
        )

    obsolescence_deduction = gross_replacement_cost * total_obsolescence_rate
    net_replacement_cost = gross_replacement_cost - obsolescence_deduction

    return {
        "approach": "cost",
        "currency": "IDR",
        "gross_replacement_cost_idr": gross_replacement_cost,
        "functional_obsolescence_rate": functional_obsolescence_rate,
        "economic_obsolescence_rate": economic_obsolescence_rate,
        "obsolescence_deduction_idr": obsolescence_deduction,
        "indicative_value_idr": net_replacement_cost,
        "indicative_value_formatted": format_idr(net_replacement_cost),
        "components": {
            "rd_labor_cost_idr": rd_labor,
            "materials_prototyping_cost_idr": materials_prototyping,
            "testing_certification_cost_idr": testing_certification,
            "ip_legal_filing_cost_idr": ip_legal_filing,
            "engineering_overhead_cost_idr": overhead_engineering,
        },
        "wipo_reference_locator": WIPO_LOCATORS["cost"],
    }


def calculate_market_comparables_valuation(comparables: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Deterministic Market Comparables Approach in IDR.
    Disables market valuation without credible, sufficiently documented comparables.
    Presents adjusted comparable indications and their range separately.
    """
    credible_items: List[Dict[str, Any]] = []
    for comp in comparables:
        is_verified = bool(comp.get("is_credible_verified", False))
        citation = str(comp.get("source_citation") or "").strip()
        unadj = comp.get("unadjusted_value_idr")
        adj_factor = float(comp.get("adjustment_factor", 1.0))
        adj_rationale = str(comp.get("adjustment_rationale") or "").strip()

        if (
            is_verified
            and len(citation) >= 10
            and unadj is not None
            and float(unadj) > 0
            and adj_factor > 0
            and len(adj_rationale) >= 5
        ):
            adjusted_val = float(unadj) * adj_factor
            credible_items.append(
                {
                    "id": comp.get("id"),
                    "title": comp.get("title"),
                    "source_citation": citation,
                    "jurisdiction": comp.get("jurisdiction", "ID"),
                    "transaction_year": comp.get("transaction_year", 2025),
                    "unadjusted_value_idr": float(unadj),
                    "adjustment_factor": adj_factor,
                    "adjustment_rationale": adj_rationale,
                    "adjusted_indication_idr": adjusted_val,
                    "adjusted_indication_formatted": format_idr(adjusted_val),
                }
            )

    if len(credible_items) == 0:
        raise ValueError(
            "Market valuation is disabled: no credible, sufficiently documented comparable transactions are available."
        )

    indications = sorted(item["adjusted_indication_idr"] for item in credible_items)
    min_val = indications[0]
    max_val = indications[-1]
    median_val = float(np.median(indications))

    return {
        "approach": "market_comparables",
        "currency": "IDR",
        "market_valuation_enabled": True,
        "comparable_count": len(credible_items),
        "adjusted_indications": credible_items,
        "range_min_idr": min_val,
        "range_max_idr": max_val,
        "median_indication_idr": median_val,
        "indicative_value_idr": median_val,
        "indicative_value_formatted": f"{format_idr(min_val)} — {format_idr(max_val)} (Median: {format_idr(median_val)})",
        "methodological_note": (
            "Each comparable transaction indication and the full observed range are presented separately; "
            "different valuation approaches are never averaged automatically."
        ),
        "wipo_reference_locator": WIPO_LOCATORS["market_comparables"],
    }


def calculate_relief_from_royalty_valuation(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic Relief-from-Royalty calculation in IDR.
    """
    _guard_no_score_inference(inputs)

    economic_life = int(inputs.get("economic_life_years", 0))
    if economic_life < 1 or economic_life > 40:
        raise ValueError(f"economic_life_years must be between 1 and 40, got {economic_life}.")

    discount_rate = float(inputs.get("discount_rate", -1.0))
    if discount_rate < 0.0 or discount_rate > 2.0:
        raise ValueError(f"discount_rate must be non-negative, got {discount_rate}.")

    tax_rate = float(inputs.get("tax_rate", -1.0))
    if tax_rate < 0.0 or tax_rate >= 1.0:
        raise ValueError(f"tax_rate must be in [0.0, 1.0), got {tax_rate}.")

    royalty_rate = float(inputs.get("royalty_rate", -1.0))
    if not (0.0 < royalty_rate < 1.0):
        raise ValueError(f"royalty_rate must be in (0.0, 1.0), got {royalty_rate}.")

    annual_revenues: List[float] = [float(x) for x in inputs.get("annual_revenues_idr", [])]
    if len(annual_revenues) != economic_life:
        raise ValueError("annual_revenues_idr length must match economic_life_years.")

    annual_ip_maintenance = float(inputs.get("annual_ip_maintenance_cost_idr", 0.0))
    year_zero_cost = float(inputs.get("year_zero_setup_cost_idr", 0.0))

    schedule: List[Dict[str, Any]] = []
    pv_sum = 0.0
    for idx, rev in enumerate(annual_revenues):
        yr = idx + 1
        gross_royalty_saved = rev * royalty_rate
        net_royalty_pre_tax = gross_royalty_saved - annual_ip_maintenance
        tax_charge = max(0.0, net_royalty_pre_tax * tax_rate)
        after_tax_royalty = net_royalty_pre_tax - tax_charge
        df = (1.0 + discount_rate) ** yr
        pv = after_tax_royalty / df
        pv_sum += pv
        schedule.append(
            {
                "year": yr,
                "projected_revenue_idr": rev,
                "gross_royalty_saved_idr": gross_royalty_saved,
                "ip_maintenance_cost_idr": annual_ip_maintenance,
                "taxes_idr": tax_charge,
                "after_tax_royalty_saving_idr": after_tax_royalty,
                "present_value_idr": pv,
            }
        )

    npv_idr = pv_sum - year_zero_cost
    return {
        "approach": "relief_from_royalty",
        "currency": "IDR",
        "royalty_rate": royalty_rate,
        "discount_rate": discount_rate,
        "tax_rate": tax_rate,
        "economic_life_years": economic_life,
        "year_zero_setup_cost_idr": year_zero_cost,
        "indicative_value_idr": npv_idr,
        "indicative_value_formatted": format_idr(npv_idr),
        "annual_schedule": schedule,
        "wipo_reference_locator": WIPO_LOCATORS["relief_from_royalty"],
    }


def run_dcf_sensitivity_analysis(base_inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Computes tornado sensitivity analysis around a base DCF scenario.
    """
    base_res = calculate_dcf_valuation(base_inputs)
    base_npv = base_res["indicative_value_idr"]

    results: List[Dict[str, Any]] = []

    # 1. Discount Rate +/- 200 bps (2%)
    dr_base = float(base_inputs["discount_rate"])
    low_dr_inputs = {**base_inputs, "discount_rate": max(0.0, dr_base - 0.02)}
    high_dr_inputs = {**base_inputs, "discount_rate": dr_base + 0.02}
    results.append(
        {
            "parameter": "Discount Rate (±2.0%)",
            "parameter_id": "discount_rate",
            "base_npv_idr": base_npv,
            "downside_case_label": f"{(dr_base + 0.02)*100:.1f}%",
            "downside_npv_idr": calculate_dcf_valuation(high_dr_inputs)["indicative_value_idr"],
            "upside_case_label": f"{max(0.0, dr_base - 0.02)*100:.1f}%",
            "upside_npv_idr": calculate_dcf_valuation(low_dr_inputs)["indicative_value_idr"],
        }
    )

    # 2. Operating Cash Flows (EBITDA) +/- 20%
    def _scale_ebitda(factor: float) -> Dict[str, Any]:
        scaled_proj = []
        for p in base_inputs["annual_projections"]:
            eb = float(p.get("ebitda_idr", p.get("operating_cf_idr", 0.0))) * factor
            scaled_proj.append({**p, "ebitda_idr": eb})
        return {**base_inputs, "annual_projections": scaled_proj}

    results.append(
        {
            "parameter": "Attributable Cash Flows (±20%)",
            "parameter_id": "cash_flows",
            "base_npv_idr": base_npv,
            "downside_case_label": "-20% Cash Flows",
            "downside_npv_idr": calculate_dcf_valuation(_scale_ebitda(0.80))["indicative_value_idr"],
            "upside_case_label": "+20% Cash Flows",
            "upside_npv_idr": calculate_dcf_valuation(_scale_ebitda(1.20))["indicative_value_idr"],
        }
    )

    # 3. Year-0 Investment & CapEx +/- 25%
    y0_base = float(base_inputs.get("year_zero_investment_idr", 0.0))
    low_capex_inputs = {**base_inputs, "year_zero_investment_idr": y0_base * 0.75}
    high_capex_inputs = {**base_inputs, "year_zero_investment_idr": y0_base * 1.25}
    results.append(
        {
            "parameter": "Year-0 Investment (±25%)",
            "parameter_id": "year_zero_investment",
            "base_npv_idr": base_npv,
            "downside_case_label": "+25% Outlay",
            "downside_npv_idr": calculate_dcf_valuation(high_capex_inputs)["indicative_value_idr"],
            "upside_case_label": "-25% Outlay",
            "upside_npv_idr": calculate_dcf_valuation(low_capex_inputs)["indicative_value_idr"],
        }
    )

    for r in results:
        r["swing_idr"] = abs(float(r["upside_npv_idr"]) - float(r["downside_npv_idr"]))

    results.sort(key=lambda x: x["swing_idr"], reverse=True)
    return results


def run_seeded_monte_carlo_dcf(
    base_inputs: Dict[str, Any],
    seed: int = 42,
    iterations: int = 1000,
    distributions: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Runs a reproducible, seeded Monte Carlo simulation over DCF assumptions using user-defined distributions.
    Describes simulated intervals strictly as conditional on user-specified assumptions.
    """
    if iterations < 50 or iterations > 20000:
        raise ValueError("Monte Carlo iterations must be between 50 and 20,000.")

    rng = np.random.Generator(np.random.PCG64(int(seed)))
    dist_cfg = distributions or {
        "cash_flow_multiplier": {"type": "triangular", "min": 0.75, "mode": 1.0, "max": 1.25},
        "discount_rate": {
            "type": "normal",
            "mean": float(base_inputs.get("discount_rate", 0.14)),
            "std": 0.015,
            "min": 0.04,
            "max": 0.45,
        },
        "year_zero_multiplier": {"type": "uniform", "min": 0.90, "max": 1.15},
    }

    def _sample(spec: Dict[str, Any], size: int) -> np.ndarray:
        dtype = spec.get("type", "triangular")
        if dtype == "triangular":
            return rng.triangular(
                float(spec.get("min", 0.8)),
                float(spec.get("mode", 1.0)),
                float(spec.get("max", 1.2)),
                size=size,
            )
        if dtype == "normal":
            arr = rng.normal(
                float(spec.get("mean", 1.0)),
                float(spec.get("std", 0.1)),
                size=size,
            )
            lo = spec.get("min")
            hi = spec.get("max")
            if lo is not None:
                arr = np.maximum(arr, float(lo))
            if hi is not None:
                arr = np.minimum(arr, float(hi))
            return arr
        if dtype == "uniform":
            return rng.uniform(
                float(spec.get("min", 0.85)),
                float(spec.get("max", 1.15)),
                size=size,
            )
        raise ValueError(f"Unsupported distribution type: {dtype}")

    cf_mults = _sample(
        dist_cfg.get("cash_flow_multiplier", {"type": "triangular", "min": 0.75, "mode": 1.0, "max": 1.25}),
        iterations,
    )
    dr_samples = _sample(
        dist_cfg.get(
            "discount_rate",
            {
                "type": "normal",
                "mean": float(base_inputs.get("discount_rate", 0.14)),
                "std": 0.015,
                "min": 0.04,
                "max": 0.45,
            },
        ),
        iterations,
    )
    y0_mults = _sample(
        dist_cfg.get("year_zero_multiplier", {"type": "uniform", "min": 0.90, "max": 1.15}),
        iterations,
    )

    # Vectorized DCF evaluation across iterations
    economic_life = int(base_inputs["economic_life_years"])
    tax_rate = float(base_inputs["tax_rate"])
    y0_base = float(base_inputs.get("year_zero_investment_idr", 0.0))
    attr_mode = str(base_inputs.get("attribution_mode", "direct_cash_flows"))
    attr_factor = (
        float(base_inputs["attribution_factor"])
        if attr_mode == "documented_attribution_factor"
        else 1.0
    )
    cf_haircut = float(base_inputs.get("cash_flow_probability_haircut", 0.0))

    npvs = -y0_base * y0_mults
    for idx, p in enumerate(base_inputs["annual_projections"]):
        yr = idx + 1
        gross_ebitda = float(p.get("ebitda_idr", p.get("operating_cf_idr", 0.0)))
        dep = float(p.get("depreciation_idr", 0.0))
        capex = float(p.get("capex_idr", 0.0))
        dnwc = float(p.get("working_capital_change_idr", 0.0))

        sim_ebitda = gross_ebitda * cf_mults * attr_factor
        sim_dep = dep * attr_factor
        sim_ebit = sim_ebitda - sim_dep
        sim_tax = np.maximum(0.0, sim_ebit * tax_rate)
        sim_nopat = sim_ebit - sim_tax
        sim_fcf = (sim_nopat + sim_dep - capex - dnwc) * (1.0 - cf_haircut)
        npvs = npvs + (sim_fcf / ((1.0 + dr_samples) ** yr))

    p5, p10, p25, p50, p75, p90, p95 = [
        float(x) for x in np.percentile(npvs, [5, 10, 25, 50, 75, 90, 95])
    ]
    counts, bin_edges = np.histogram(npvs, bins=12)
    histogram = [
        {
            "bin_index": i + 1,
            "bin_min_idr": float(bin_edges[i]),
            "bin_max_idr": float(bin_edges[i + 1]),
            "bin_label": format_idr(float((bin_edges[i] + bin_edges[i + 1]) / 2.0)),
            "count": int(counts[i]),
        }
        for i in range(len(counts))
    ]

    return {
        "seed": int(seed),
        "iterations": int(iterations),
        "distributions_used": dist_cfg,
        "mean_idr": float(np.mean(npvs)),
        "std_idr": float(np.std(npvs)),
        "percentiles_idr": {
            "p5": p5,
            "p10": p10,
            "p25": p25,
            "p50": p50,
            "p75": p75,
            "p90": p90,
            "p95": p95,
        },
        "probability_positive_npv": round(float(np.mean(npvs > 0.0)), 4),
        "histogram": histogram,
        "conditional_interval_statement": (
            "Simulated valuation intervals (P10–P90 and P5–P95) are strictly conditional on the user-defined "
            "input probability distributions, cash-flow projections, and model structure; they do not represent "
            "empirical market price guarantees."
        ),
    }
