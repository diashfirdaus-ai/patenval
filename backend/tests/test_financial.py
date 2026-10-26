import pytest
from app.services.valuation import (
    calculate_cost_valuation,
    calculate_dcf_valuation,
    calculate_market_comparables_valuation,
    calculate_relief_from_royalty_valuation,
    run_dcf_sensitivity_analysis,
    run_seeded_monte_carlo_dcf,
)


def test_dcf_independent_hand_calculated_fixture():
    """
    Independently hand-calculated 2-year DCF fixture:
    - Year 0 investment: Rp 100,000,000 (not discounted)
    - Attribution factor: 0.50 (documented)
    - Tax rate: 20% (0.20), Discount rate: 10% (0.10), Terminal value: False (default)
    - Year 1: Gross EBITDA = 200M -> Attr EBITDA = 100M, Gross Dep = 20M -> Attr Dep = 10M
      -> EBIT = 90M -> Tax (20%) = 18M -> NOPAT = 72M
      -> FCF1 = NOPAT (72M) + Attr Dep (10M) - CapEx (12M) - dNWC (4M) = 66,000,000
      -> PV(FCF1) = 66,000,000 / 1.10 = 60,000,000.0
    - Year 2: Gross EBITDA = 300M -> Attr EBITDA = 150M, Gross Dep = 20M -> Attr Dep = 10M
      -> EBIT = 140M -> Tax (20%) = 28M -> NOPAT = 112M
      -> FCF2 = 112M + 10M - CapEx (0) - dNWC (1.0M) = 121,000,000
      -> PV(FCF2) = 121,000,000 / (1.10^2) = 121,000,000 / 1.21 = 100,000,000.0
    - Total PV Operating Cash Flows = 60M + 100M = 160,000,000
    - Net Present Value (NPV) = 160,000,000 - Year_0 (100,000,000) = 60,000,000.0
    """
    inputs = {
        "economic_life_years": 2,
        "discount_rate": 0.10,
        "tax_rate": 0.20,
        "year_zero_investment_idr": 100_000_000.0,
        "attribution_mode": "documented_attribution_factor",
        "attribution_factor": 0.50,
        "attribution_documentation": "50% patent contribution to modular reactor unit margin.",
        "annual_projections": [
            {"year": 1, "ebitda_idr": 200_000_000.0, "depreciation_idr": 20_000_000.0, "capex_idr": 12_000_000.0, "working_capital_change_idr": 4_000_000.0},
            {"year": 2, "ebitda_idr": 300_000_000.0, "depreciation_idr": 20_000_000.0, "capex_idr": 0.0, "working_capital_change_idr": 1_000_000.0},
        ],
    }
    res = calculate_dcf_valuation(inputs)
    assert res["terminal_value_enabled"] is False
    assert res["pv_terminal_value_idr"] == 0.0
    assert abs(res["annual_schedule"][0]["present_value_fcf_idr"] - 60_000_000.0) < 1e-6
    assert abs(res["annual_schedule"][1]["present_value_fcf_idr"] - 100_000_000.0) < 1e-6
    assert abs(res["pv_operating_cash_flows_idr"] - 160_000_000.0) < 1e-6
    assert abs(res["indicative_value_idr"] - 60_000_000.0) < 1e-6
    assert res["indicative_value_formatted"] == "Rp 60.000.000"


def test_dcf_zero_discount_rate_and_negative_npv():
    """Tests zero discount rate (r = 0.0) and negative NPV when Year-0 outlay exceeds inflows."""
    inputs = {
        "economic_life_years": 2,
        "discount_rate": 0.0,
        "tax_rate": 0.0,
        "year_zero_investment_idr": 500_000_000.0,
        "attribution_mode": "direct_cash_flows",
        "annual_projections": [
            {"year": 1, "ebitda_idr": 100_000_000.0, "depreciation_idr": 0.0, "capex_idr": 0.0, "working_capital_change_idr": 0.0},
            {"year": 2, "ebitda_idr": 150_000_000.0, "depreciation_idr": 0.0, "capex_idr": 0.0, "working_capital_change_idr": 0.0},
        ],
    }
    res = calculate_dcf_valuation(inputs)
    assert abs(res["indicative_value_idr"] - (-250_000_000.0)) < 1e-6
    assert res["indicative_value_formatted"] == "-Rp 250.000.000"


def test_dcf_duplicate_attribution_and_invalid_inputs_rejected():
    """Prevents duplicate attribution, score-to-monetary conversion, and invalid rates."""
    base = {
        "economic_life_years": 1,
        "discount_rate": 0.12,
        "tax_rate": 0.22,
        "year_zero_investment_idr": 10_000_000.0,
        "attribution_mode": "direct_cash_flows",
        "attribution_factor": 0.40,  # Forbidden in direct_cash_flows mode!
        "annual_projections": [
            {"year": 1, "ebitda_idr": 50_000_000.0, "depreciation_idr": 0.0, "capex_idr": 0.0, "working_capital_change_idr": 0.0}
        ],
    }
    with pytest.raises(ValueError, match="Duplicate attribution prevented"):
        calculate_dcf_valuation(base)

    # Missing documentation when using documented_attribution_factor
    with pytest.raises(ValueError, match="Documented attribution rationale"):
        calculate_dcf_valuation(
            {
                **base,
                "attribution_mode": "documented_attribution_factor",
                "attribution_factor": 0.40,
                "attribution_documentation": "",
            }
        )

    # Forbidden score-to-valuation inference
    with pytest.raises(ValueError, match="Forbidden score-to-valuation inference"):
        calculate_dcf_valuation({**base, "attribution_factor": None, "infer_from_assessment_score": True})

    # Negative discount rate
    with pytest.raises(ValueError, match="discount_rate"):
        calculate_dcf_valuation({**base, "attribution_factor": None, "discount_rate": -0.05})


def test_dcf_risk_double_counting_flagged():
    """Verifies risk double-counting detection when risk is applied to both cash flows and discount rate."""
    inputs = {
        "economic_life_years": 1,
        "discount_rate": 0.15,
        "tax_rate": 0.20,
        "year_zero_investment_idr": 10_000_000.0,
        "attribution_mode": "direct_cash_flows",
        "risk_treatment_mode": "both",
        "cash_flow_probability_haircut": 0.20,
        "discount_rate_technology_premium": 0.05,
        "annual_projections": [
            {"year": 1, "ebitda_idr": 100_000_000.0, "depreciation_idr": 0.0, "capex_idr": 0.0, "working_capital_change_idr": 0.0}
        ],
    }
    res = calculate_dcf_valuation(inputs)
    assert res["double_counting_flagged"] is True
    assert "DOUBLE COUNTING" in res["double_counting_warning"]


def test_cost_market_and_royalty_valuations():
    """Independently verifies Cost, Market Comparables, and Relief-from-Royalty calculations."""
    cost_res = calculate_cost_valuation(
        {
            "rd_labor_cost_idr": 400_000_000.0,
            "materials_prototyping_cost_idr": 300_000_000.0,
            "testing_certification_cost_idr": 100_000_000.0,
            "ip_legal_filing_cost_idr": 50_000_000.0,
            "engineering_overhead_cost_idr": 150_000_000.0,
            "functional_obsolescence_rate": 0.10,
            "economic_obsolescence_rate": 0.05,
        }
    )
    assert abs(cost_res["gross_replacement_cost_idr"] - 1_000_000_000.0) < 1e-6
    assert abs(cost_res["indicative_value_idr"] - 850_000_000.0) < 1e-6

    # Negative cost component rejected
    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_cost_valuation({"rd_labor_cost_idr": -100.0})

    # Market valuation disabled without credible comparables
    with pytest.raises(ValueError, match="Market valuation is disabled"):
        calculate_market_comparables_valuation([])

    comp_res = calculate_market_comparables_valuation(
        [
            {
                "id": "c1",
                "title": "License A",
                "source_citation": "Official Licensing Compendium 2025 #11",
                "unadjusted_value_idr": 800_000_000.0,
                "adjustment_factor": 1.10,
                "adjustment_rationale": "Higher throughput capacity",
                "is_credible_verified": True,
            },
            {
                "id": "c2",
                "title": "License B",
                "source_citation": "Official Licensing Compendium 2025 #12",
                "unadjusted_value_idr": 1_000_000_000.0,
                "adjustment_factor": 0.95,
                "adjustment_rationale": "Single territory adjustment",
                "is_credible_verified": True,
            },
        ]
    )
    assert abs(comp_res["range_min_idr"] - 880_000_000.0) < 1e-4
    assert abs(comp_res["range_max_idr"] - 950_000_000.0) < 1e-4
    assert abs(comp_res["median_indication_idr"] - 915_000_000.0) < 1e-4

    # Relief-from-royalty
    roy_res = calculate_relief_from_royalty_valuation(
        {
            "economic_life_years": 1,
            "discount_rate": 0.10,
            "tax_rate": 0.20,
            "royalty_rate": 0.05,
            "annual_revenues_idr": [2_000_000_000.0],
            "annual_ip_maintenance_cost_idr": 12_000_000.0,
            "year_zero_setup_cost_idr": 10_000_000.0,
        }
    )
    # Gross royalty = 100M, net pre-tax = 88M, after 20% tax = 70.4M, PV at 10% = 64M, minus 10M setup = 54M
    assert abs(roy_res["indicative_value_idr"] - 54_000_000.0) < 1e-6


def test_reproducible_seeded_monte_carlo_and_sensitivity():
    """Verifies that seeded Monte Carlo simulations are strictly reproducible."""
    inputs = {
        "economic_life_years": 3,
        "discount_rate": 0.14,
        "tax_rate": 0.22,
        "year_zero_investment_idr": 200_000_000.0,
        "attribution_mode": "direct_cash_flows",
        "annual_projections": [
            {"year": 1, "ebitda_idr": 180_000_000.0, "depreciation_idr": 20_000_000.0, "capex_idr": 10_000_000.0, "working_capital_change_idr": 5_000_000.0},
            {"year": 2, "ebitda_idr": 250_000_000.0, "depreciation_idr": 20_000_000.0, "capex_idr": 10_000_000.0, "working_capital_change_idr": 5_000_000.0},
            {"year": 3, "ebitda_idr": 320_000_000.0, "depreciation_idr": 20_000_000.0, "capex_idr": 10_000_000.0, "working_capital_change_idr": 5_000_000.0},
        ],
    }
    mc1 = run_seeded_monte_carlo_dcf(inputs, seed=12345, iterations=500)
    mc2 = run_seeded_monte_carlo_dcf(inputs, seed=12345, iterations=500)
    mc3 = run_seeded_monte_carlo_dcf(inputs, seed=99999, iterations=500)

    assert mc1["percentiles_idr"] == mc2["percentiles_idr"]
    assert mc1["mean_idr"] == mc2["mean_idr"]
    assert mc1["mean_idr"] != mc3["mean_idr"]
    assert "conditional on the user-defined" in mc1["conditional_interval_statement"]

    sens = run_dcf_sensitivity_analysis(inputs)
    assert len(sens) == 3
    assert sens[0]["swing_idr"] >= sens[1]["swing_idr"]
