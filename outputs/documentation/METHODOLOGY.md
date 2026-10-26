# TechVal AI — Scientific & Mathematical Methodology Specification

## 1. Strict Four-Output Separation Architecture

TechVal AI enforces a strict methodological separation across four distinct output domains. At no point in the backend, database, multi-agent workflow, or frontend are qualitative/ordinal assessment scores or TRL levels converted into monetary values, discount rates, or royalty rates.

| Output # | Domain Key | Mathematical Representation | Scale / Unit | Primary Grounding |
| :--- | :--- | :--- | :--- | :--- |
| **1** | `technology_assessment` | Composite normalized score $S_{\text{tech}} \in [0, 1]$ + Native NASA TRL $\in \{1,\dots,9\}$ | $[0, 1]$ & TRL $1\text{--}9$ | NASA ESTO TRL / ISO 16290:2013; Harhoff et al. (2003) |
| **2** | `commercialization_readiness` | Composite normalized score $S_{\text{comm}} \in [0, 1]$ | $[0, 1]$ | WIPO IP Valuation Basics (Sec. 2); Expert Rubric |
| **3** | `economic_valuation` | Deterministic financial models in Indonesian Rupiah ($\text{IDR}$) | $\text{Rp}$ (IDR) | WIPO IP Valuation Basics (Sec. 3–5) |
| **4** | `evidence_completeness` | Weighted coverage ratio $C \in [0, 1]$ across applicable indicators | $[0, 1]$ ($0\%\text{--}100\%$) | Explicit Missing-Data Accounting |

---

## 2. Indicator Normalization & Native TRL Preservation

### 2.1 Ordinal 1–5 Rubric Indicators
All non-TRL assessment and commercialization indicators use a 5-level ordinal rubric $s_i \in [1, 5]$. To aggregate across observed indicators without scale distortion, raw scores are linearly normalized onto $[0, 1]$:

$$s_i^{\text{norm}} = \frac{s_i - 1}{4} \in [0, 1]$$

### 2.2 NASA Technology Readiness Level (TRL 1–9)
Per NASA ESTO (`NASA-TRL-2020`, ISO 16290:2013), Technology Readiness Level (`TECH_TRL_NATIVE`) is evaluated and reported on its **native integer scale $\{1, 2, \dots, 9\}$** with explicit exit criteria verification. It is never compressed onto a 1–5 scale or averaged with 1–5 rubric scores.

---

## 3. Missing vs. Not-Applicable Handling & Weight Renormalization

Every indicator $i$ in dimension $d \in \{\text{tech}, \text{comm}\}$ is assigned one of three mutually exclusive statuses:
- `observed` ($i \in O_d$): Supported by a verified source locator (`page:N`, `para:N`, or `table:N`) and verbatim quote.
- `missing` ($i \in M_d$): Applicable to the technology domain, but sufficient documentary evidence is not yet available.
- `not_applicable` ($i \in NA_d$): Structurally inapplicable to the IP type (e.g., `TECH_PATENT_STRENGTH` for non-patent software or trade-secret disclosures).

Let $A_d = O_d \cup M_d$ denote the set of **applicable** indicators in dimension $d$, and let $w_i > 0$ denote the baseline or AHP-derived weight of indicator $i$.
- Indicators in $M_d$ and $NA_d$ are **never imputed as zero** (which would conflate missing evidence with technical failure).
- Instead, weights are renormalized strictly over the observed set $O_d$:

$$w'_i = \begin{cases} \dfrac{w_i}{\sum_{j \in O_d} w_j} & \text{if } i \in O_d \text{ and } \sum_{j \in O_d} w_j > 0 \\[10pt] 0 & \text{otherwise} \end{cases}$$

The composite dimension score is:

$$S_d = \sum_{i \in O_d} w'_i \, s_i^{\text{norm}}$$

### 3.1 Weighted Evidence Completeness
To prevent high scores on sparse evidence from appearing definitive, **Evidence Completeness** is computed over all applicable indicators $A_d = O_d \cup M_d$ (excluding $NA_d$ so non-patent technologies are never penalized):

$$C_d = \frac{\sum_{i \in O_d} w_i}{\sum_{k \in A_d} w_k} \in [0, 1]$$

Whenever $C_d < 0.70$, or when any uncalibrated (`provisional`) weight set is active, or when contradictory claims are detected across document sections, the assessment revision is automatically flagged `is_provisional = True`.

---

## 4. Analytic Hierarchy Process (AHP) Weight Calibration

Expert weight sets are calibrated using Saaty's Analytic Hierarchy Process (`SAATY-1980`, Chapters 1–3):
1. For $n$ indicators in a dimension, the expert constructs a pairwise comparison matrix $\mathbf{A} = [a_{ij}]_{n \times n}$ satisfying positivity ($a_{ij} > 0$), unit diagonal ($a_{ii} = 1$), and exact reciprocity ($a_{ji} = 1 / a_{ij}$).
2. The principal right eigenvector $\mathbf{w}$ corresponding to the maximum real eigenvalue $\lambda_{\max}$ is computed:
   $$\mathbf{A}\mathbf{w} = \lambda_{\max}\mathbf{w}, \quad \sum_{i=1}^n w_i = 1$$
3. Consistency Index ($CI$) and Consistency Ratio ($CR$) are computed using Saaty's Random Index table $RI_n$:
   $$CI = \frac{\lambda_{\max} - n}{n - 1}, \quad CR = \frac{CI}{RI_n}$$
4. **Consistency Gate**: Any matrix with $CR > 0.10$ is rejected by the backend (`422 Unprocessable Entity`) and cannot be activated as an approved weight set.

---

## 5. Deterministic WIPO Economic Valuation Engine (IDR)

Grounded in WIPO's *Intellectual Property Valuation Basics for Technology Transfer Professionals* (`WIPO-2024`, Sections 2–5), all financial calculations are executed deterministically in Python (`backend/app/services/valuation.py`) in **Indonesian Rupiah ($\text{IDR}$)**:

### 5.1 Income Approach — Discounted Cash Flow (DCF)
For projection horizon $t = 1, \dots, T$, annual technology-attributable free cash flow is:

$$\text{FCF}_t = \alpha \cdot \left[ (R_t - C_t)(1 - \tau) - \text{CAPEX}_t - \Delta \text{WC}_t \right]$$

where:
- $R_t, C_t, \text{CAPEX}_t, \Delta \text{WC}_t$ are revenue, operating cost, capital expenditure, and working capital change in IDR,
- $\tau \in [0, 1)$ is the corporate tax rate,
- $\alpha \in (0, 1]$ is the documented technology attribution factor when `attribution_mode = "documented_attribution_factor"`, or $\alpha = 1$ when `attribution_mode = "direct_cash_flows"` (cash flows are already isolated to the IP). Applying an attribution factor $< 1$ to already-direct IP cash flows is rejected to prevent double-discounting.

The Net Present Value in IDR at discount rate $r > -1$ is:

$$\text{NPV}_{\text{IDR}} = \sum_{t=1}^{T} \frac{\text{FCF}_t}{(1 + r)^t} + \frac{\text{TV}_T}{(1 + r)^T}$$

### 5.2 Income Approach — Relief-from-Royalty
$$\text{V}_{\text{RfR, IDR}} = \sum_{t=1}^{T} \frac{\left(R_t \cdot \rho - M_t\right)(1 - \tau)}{(1 + r)^t}$$
where $\rho \in (0, 1)$ is the market-benchmarked royalty rate and $M_t$ is annual IP maintenance cost in IDR.

### 5.3 Cost Approach (Reproduction / Replacement Cost)
$$\text{V}_{\text{Cost, IDR}} = \left(\sum_{k} C_{\text{hist}, k} + C_{\text{reprod}} + C_{\text{opp}}\right)(1 - \delta_{\text{func}})(1 - \delta_{\text{econ}})$$
where $\delta_{\text{func}}, \delta_{\text{econ}} \in [0, 1)$ are functional and economic obsolescence factors.

### 5.4 Market Comparables Approach
Given $m \ge 1$ verified comparable transactions with base values $V_j$ and documented adjustment multipliers $\gamma_j$, adjusted transaction values $V'_j = V_j \cdot \gamma_j$ yield the indicative range $[\min_j V'_j, \max_j V'_j]$ and median indication $\text{median}(V'_1, \dots, V'_m)$.

### 5.5 Risk Double-Counting Guard
Per WIPO Section 4.3, technology commercialization risk may be reflected either in probability-weighted cash flows (`in_cash_flows`) or in a risk-adjusted discount rate (`in_discount_rate`). Selecting `both` triggers an explicit `double_counting_flagged = True` warning in the valuation scenario and report.

---

## 6. Phase 4 Research Evaluation Metrics

1. **Information Extraction & Source Resolution**: Precision, Recall, Micro-F1, and Macro-F1 across indicator extraction and `page:N`/`para:N`/`table:N` locator resolution.
2. **Ordinal & Continuous Expert Agreement**:
   - **Quadratic Weighted Kappa (QWK)** on discretized ordinal ratings withquadratic penalty $w_{ij} = (i - j)^2 / (k - 1)^2$.
   - **Intraclass Correlation Coefficients** $\text{ICC}(2,1)$ (two-way random effects, absolute agreement) and $\text{ICC}(3,1)$ (two-way mixed effects, consistency), reported with **reproducible 95% percentile bootstrap confidence intervals** (fixed seed `20260417`, $B = 500$ resamples).
3. **Financial Engine Accuracy**: Mean Absolute Error ($\text{MAE}$), Root Mean Squared Error ($\text{RMSE}$), and Symmetric Mean Absolute Percentage Error ($\text{sMAPE}$) against independent hand-calculated DCF, Cost, Market Comparables, and Relief-from-Royalty benchmarks ($\text{MAE} = 0.0000\text{ IDR}$).
