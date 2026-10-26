# TechVal AI — Scientific Literature Registry & Indicator Source Mapping Matrix

## 1. Scientific Reference Verification Policy

TechVal AI distinguishes strictly between:
- **`methodology_verified`**: Primary sources whose specific sections, pages, definitions, or mathematical formulas have been directly verified and implemented.
- **`bibliographically_verified_only`**: Sources whose bibliographic existence is verified, but whose internal content is not used to justify any specific formula, rubric threshold, or weight in the system.

### 1.1 Registered Scientific References (`scientific_references` table)

| Code | Citation | DOI / Official URL | Bibliographic Status | Methodology Verification Status | Verified Sections / Pages | Cross-Domain / Implementation Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`WIPO-2024`** | World Intellectual Property Organization (2024). *Intellectual Property Valuation Basics for Technology Transfer Professionals*. Geneva: WIPO. | `https://www.wipo.int/web-publications/intellectual-property-valuation-basics-for-technology-transfer-professionals/en/index.html` | `verified` | **`methodology_verified`** | Sections 2, 3, 4, and 5 (Cost, Market Comparables, DCF, Relief-from-Royalty, Risk & Attribution) | Grounds all deterministic IDR valuation approaches and prohibits converting qualitative scores into monetary values. |
| **`NASA-TRL-2020`** | NASA Earth Science Technology Office (ESTO) / Mankins, J. C. (2020). *Technology Readiness Levels (TRL) — NASA 1–9 Scale & ISO 16290:2013 Alignment*. Washington, DC: NASA. | `https://esto.nasa.gov/trl/` | `verified` | **`methodology_verified`** | TRL Definitions Level 1 through Level 9 & Exit Criteria Checklist | Adapted from aerospace systems engineering to general industrial, chemical, and hardware/software prototypes; native 1–9 scale preserved. |
| **`HARHOFF-2003`** | Harhoff, D., Scherer, F. M., & Vopel, K. (2003). Citations, family size, opposition and the value of patent rights. *Research Policy*, 32(8), 1343–1363. | `https://www.sciencedirect.com/science/article/abs/pii/S0048733302001245` | `verified` | **`methodology_verified`** | Section 2 (Indicators of Patent Value, pp. 1345–1348) & Section 4 (Empirical Results, pp. 1353–1359) | Establishes that forward citations, family size, and claim scope correlate with skewed economic value and must be treated as contextual signals, never deterministic currency multipliers. |
| **`SAATY-1980`** | Saaty, T. L. (1980). *The Analytic Hierarchy Process: Planning, Priority Setting, Resource Allocation*. New York: McGraw-Hill. | `https://doi.org/10.21236/ada214804` | `verified` | **`methodology_verified`** | Chapter 1 (1–9 Fundamental Scale, pp. 17–24) & Chapter 3 (Eigenvalue Consistency Ratio $CR \le 0.10$, pp. 49–62) | Grounds reciprocal pairwise comparison matrices, principal eigenvector weights, and $CR = CI/RI \le 0.10$ validation. |
| **`OECD-OSLO-2018`** | OECD / Eurostat (2018). *Oslo Manual 2018: Guidelines for Collecting, Reporting and Using Data on Innovation* (4th ed.). Paris: OECD Publishing. | `https://doi.org/10.1787/9789264304604-en` | `verified` | **`bibliographically_verified_only`** | None (`null`) — Bibliographic taxonomy context only | Used solely for high-level innovation taxonomy framing; never cited for any scoring formula or weight. |

---

## 2. Indicator Origin Classification & Source Mapping Matrix (`indicator_definitions` table)

Every indicator is explicitly classified into one of four origin categories:
- `directly_sourced`: Directly defined in a `methodology_verified` reference with an explicit section/page locator.
- `adapted`: Adapted from a `methodology_verified` reference to fit university/R&D technology transfer disclosures, with documented cross-domain adaptation notes.
- `proposed`: Proposed operational rubric indicator requiring local expert calibration (marked provisional until expert-validated).
- `expert_validated`: Calibrated and signed off by an authorized `expert_reviewer` via AHP ($CR \le 0.10$) and revision-bound review.

| Indicator Code | Dimension | Scale | Patent-Specific? | Origin Classification | Primary Reference | Source Section / Page Locator | Cross-Domain / Operational Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TECH_TRL_NATIVE` | `technology_assessment` | `1-9_trl` (Native) | No | **`directly_sourced`** | `NASA-TRL-2020` | NASA ESTO TRL 1–9 Scale Definitions, Levels 1–9 | Preserved on native 1–9 integer scale; never compressed to 1–5. |
| `TECH_NOVELTY` | `technology_assessment` | `1-5` | No | **`adapted`** | `HARHOFF-2003` | Section 2, pp. 1345–1348 (Technical differentiation & prior art distance) | Adapted from patent prior-art differentiation to cover both patented and unpatented R&D disclosures. |
| `TECH_VALIDATION` | `technology_assessment` | `1-5` | No | **`adapted`** | `NASA-TRL-2020` | NASA ESTO TRL Exit Criteria, Levels 4–7 (Lab vs. Relevant Operational Environment) | Evaluates empirical repeatability, test duration, and mass/energy balance verification. |
| `TECH_SCALABILITY` | `technology_assessment` | `1-5` | No | **`proposed`** | *Proposed Rubric* | Proposed Indicator — Provisional until Expert Calibration | Assesses engineering manufacturability, modular scaling, and domestic content (TKDN) readiness. |
| `TECH_PATENT_STRENGTH` | `technology_assessment` | `1-5` | **Yes** | **`adapted`** | `HARHOFF-2003` | Section 2 & Section 4, pp. 1345–1359 (Family size, citation signals, claim scope) | Marked `not_applicable` automatically for non-patent technologies without completeness penalty. |
| `TECH_SYSTEM_INTEGRATION` | `technology_assessment` | `1-5` | No | **`adapted`** | `NASA-TRL-2020` | NASA ESTO TRL Levels 5–7 (Subsystem & System Integration Readiness) | Adapted from aerospace subsystem interface verification to industrial skid/software integration. |
| `COMM_MARKET_DEMAND` | `commercialization_readiness` | `1-5` | No | **`adapted`** | `WIPO-2024` | Section 2 (Qualitative Commercial Assessment & Market Need Identification) | Evaluates documented addressable industrial demand and customer pain-point evidence. |
| `COMM_COMPETITIVE_POSITION` | `commercialization_readiness` | `1-5` | No | **`adapted`** | `WIPO-2024` | Section 2 (Competitive Advantage & Substitutes Analysis) | Evaluates quantified cost/performance advantage over incumbent solutions. |
| `COMM_REGULATORY` | `commercialization_readiness` | `1-5` | No | **`proposed`** | *Proposed Rubric* | Proposed Indicator — Provisional until Expert Calibration | Evaluates environmental, safety, or sector-specific regulatory compliance (e.g., PermenLHK, SNI). |
| `COMM_SUPPLY_CHAIN` | `commercialization_readiness` | `1-5` | No | **`proposed`** | *Proposed Rubric* | Proposed Indicator — Provisional until Expert Calibration | Evaluates domestic component availability, supplier qualification, and fabrication readiness. |
| `COMM_IP_LICENSING_READINESS` | `commercialization_readiness` | `1-5` | No | **`adapted`** | `WIPO-2024` | Section 2 & Section 5 (IP Ownership Clarity, Freedom-to-Operate & Licensing Readiness) | Evaluates clarity of institutional ownership, inventor agreements, and partner LOIs. |
