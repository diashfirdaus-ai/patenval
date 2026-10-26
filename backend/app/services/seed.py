import hashlib
import json
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config import settings
from app.models import (
    AnalysisRun,
    ConsentRecord,
    Document,
    DocumentChunk,
    DocumentSection,
    Experiment,
    ExperimentDataset,
    IndicatorDefinition,
    MarketComparable,
    MethodologyConfig,
    ScientificReference,
    Technology,
    User,
    WeightSet,
)
from app.security.auth import hash_password
from app.security.storage import store_encrypted_file
from app.services.evaluation import (
    EXTRACTION_MATCHING_POLICY,
    evaluate_four_conditions_dataset,
)
from app.services.parser import chunk_section_text, parse_docx_bytes, parse_pdf_bytes
from app.services.workflow import execute_analysis_run
from fixtures.demo_data import (
    build_demo_market_docx_bytes,
    build_demo_patent_pdf_bytes,
    build_synthetic_evaluation_dataset_items,
)


def validate_methodology_attribution(
    reference: Optional[ScientificReference],
    origin_type: str,
    attributed_section: Optional[str],
    attributed_page: Optional[str],
) -> None:
    """
    Enforces the scientific registry rule:
    - Distinguish `directly_sourced`, `adapted`, `proposed`, and `expert_validated` methods.
    - Require exact sections/pages (`attributed_section` and `attributed_page`) AND a reference with
      `bibliographic_status == 'verified'` and `methodology_verification_status == 'verified_with_locator'`
      before attributing an operational rule (`directly_sourced` or `adapted`) to a publication.
    """
    valid_origins = {"directly_sourced", "adapted", "proposed", "expert_validated"}
    if origin_type not in valid_origins:
        raise ValueError(f"Invalid origin_type '{origin_type}'. Must be one of {sorted(valid_origins)}.")

    if origin_type in ("directly_sourced", "adapted"):
        if not reference:
            raise ValueError(
                f"Operational rule with origin_type '{origin_type}' requires a linked ScientificReference."
            )
        if reference.bibliographic_status != "verified":
            raise ValueError(
                f"Cannot attribute operational rule to reference '{reference.code}' because its "
                f"bibliographic_status is '{reference.bibliographic_status}' (must be 'verified')."
            )
        if reference.methodology_verification_status != "verified_with_locator":
            raise ValueError(
                f"Cannot attribute operational rule to reference '{reference.code}' because its "
                f"methodology_verification_status is '{reference.methodology_verification_status}' "
                "(exact section/page verification required)."
            )
        if not (attributed_section or "").strip() or not (attributed_page or "").strip():
            raise ValueError(
                "Exact section (`attributed_section`) and page (`attributed_page`) locators are required "
                "before attributing an operational rule to a publication."
            )


SEED_SCIENTIFIC_REFERENCES: List[Dict[str, Any]] = [
    {
        "code": "WIPO-VAL-2024",
        "authors": "World Intellectual Property Organization (WIPO)",
        "publication_year": 2024,
        "title": "Intellectual Property Valuation Basics for Technology Transfer Professionals",
        "venue_or_publisher": "WIPO Web Publications, Geneva",
        "doi_or_url": "https://www.wipo.int/web-publications/intellectual-property-valuation-basics-for-technology-transfer-professionals/en/index.html",
        "bibliographic_status": "verified",
        "methodology_verification_status": "verified_with_locator",
        "verified_sections_pages": "Section 3.1 (Cost Method, pp. 18-21); Section 3.2 (Market Method, pp. 22-25); Section 3.3 (Income/DCF & Relief-from-Royalty, pp. 26-39)",
        "domain_scope": "Technology Transfer & Intellectual Property Financial Valuation",
        "cross_domain_adaptation_notes": (
            "Directly grounds deterministic Cost, Market Comparables, DCF, and Relief-from-Royalty structures. "
            "Adapted for Indonesian Rupiah (IDR) corporate tax and cash-flow attribution schedules."
        ),
        "summary_quote": "Valuation approaches comprise the Cost Method, Market Method, and Income Method (DCF and Relief-from-Royalty), each requiring explicit assumptions.",
    },
    {
        "code": "NASA-TRL-ESTO",
        "authors": "Mankins, J. C. / NASA Earth Science Technology Office (ESTO)",
        "publication_year": 1995,
        "title": "Technology Readiness Levels: A White Paper & NASA ESTO TRL Definitions and Exit Criteria",
        "venue_or_publisher": "NASA Office of Space Access and Technology / ESTO",
        "doi_or_url": "https://esto.nasa.gov/trl/",
        "bibliographic_status": "verified",
        "methodology_verification_status": "verified_with_locator",
        "verified_sections_pages": "NASA TRL Scale Definitions (Levels 1-9) & Exit Criteria Table, Sections 1-3, pp. 1-6",
        "domain_scope": "Aerospace & Space Systems Engineering Readiness",
        "cross_domain_adaptation_notes": (
            "CROSS-DOMAIN ADAPTATION: Originally formulated for aerospace flight hardware/software systems. "
            "Adapted here for industrial, chemical, manufacturing, and digital research technologies by mapping "
            "'flight/mission environment' to 'industrial operational environment' while preserving the native 1-9 scale."
        ),
        "summary_quote": "Technology Readiness Levels (TRLs) are a systematic metric/measurement system that supports assessments of the maturity of a particular technology on a scale from TRL 1 to TRL 9.",
    },
    {
        "code": "HARHOFF-2003",
        "authors": "Harhoff, D., Scherer, F. M., & Vopel, K.",
        "publication_year": 2003,
        "title": "Citations, family size, opposition and the value of patent rights",
        "venue_or_publisher": "Research Policy, 32(8), 1343-1363",
        "doi_or_url": "https://www.sciencedirect.com/science/article/abs/pii/S0048733302001245",
        "bibliographic_status": "verified",
        "methodology_verification_status": "contextual_only",
        "verified_sections_pages": "Sections 3-5, Tables 3-6, pp. 1348-1360",
        "domain_scope": "Empirical Economics of Patent Value Indicators",
        "cross_domain_adaptation_notes": (
            "Used strictly to ground forward citations, backward citations, and patent family size as contextual "
            "signals of technological significance. Never used as a deterministic monetary conversion multiplier."
        ),
        "summary_quote": "Backward and forward citations as well as family size and opposition outcomes are positively correlated with the skewed distribution of patent values, but exhibit high variance across individual patents.",
    },
    {
        "code": "SAATY-AHP-1980",
        "authors": "Saaty, T. L.",
        "publication_year": 1980,
        "title": "The Analytic Hierarchy Process: Planning, Priority Setting, Resource Allocation",
        "venue_or_publisher": "McGraw-Hill International Book Co., New York",
        "doi_or_url": "https://doi.org/10.1016/0377-2217(90)90057-I",
        "bibliographic_status": "verified",
        "methodology_verification_status": "verified_with_locator",
        "verified_sections_pages": "Chapter 1, Section 1.5 (Eigenvalue Priority Vector & Consistency Ratio), Table 1.5 (Random Index RI), pp. 17-24",
        "domain_scope": "Multi-Criteria Decision Analysis (MCDA)",
        "cross_domain_adaptation_notes": (
            "Directly grounds reciprocal pairwise judgment matrices, principal right eigenvector weights, "
            "and Random Index (RI) values for n=1..10. The CR <= 0.10 cutoff is documented and enforced as a "
            "methodological convention."
        ),
        "summary_quote": "A consistency ratio (CR = CI / RI) of 0.10 or less is considered acceptable as a methodological convention for pairwise comparison matrices.",
    },
    {
        "code": "SHROUT-FLEISS-1979",
        "authors": "Shrout, P. E., & Fleiss, J. L. (with Cohen, J., 1968)",
        "publication_year": 1979,
        "title": "Intraclass correlations: Uses in assessing rater reliability (and Weighted Kappa: Nominal scale agreement with provision for scaled disagreement)",
        "venue_or_publisher": "Psychological Bulletin, 86(2), 420-428 & 70(4), 213-220",
        "doi_or_url": "https://doi.org/10.1037/0033-2909.86.2.420",
        "bibliographic_status": "verified",
        "methodology_verification_status": "verified_with_locator",
        "verified_sections_pages": "Shrout & Fleiss (1979) Formulas for Case 2 ICC(2,1) and Case 3 ICC(3,1), Table 1, pp. 422-425; Cohen (1968) Eq. 6-8, pp. 215-217",
        "domain_scope": "Psychometrics & Inter-Rater Reliability Evaluation",
        "cross_domain_adaptation_notes": (
            "Directly grounds Phase 4 research evaluation metrics: Quadratic-Weighted Cohen's Kappa (QWK) "
            "and explicitly specified ICC(2,1) (two-way random absolute agreement) and ICC(3,1) (two-way mixed consistency)."
        ),
        "summary_quote": "Because different intraclass correlation equations give different results from the same data, researchers must specify the exact model (Case 1, 2, or 3) and form (single vs k raters).",
    },
]


SEED_INDICATORS: List[Dict[str, Any]] = [
    # Native 1-9 NASA TRL Indicator
    {
        "code": "TECH_TRL_NATIVE",
        "dimension": "technology_assessment",
        "name_en": "Technology Readiness Level (NASA Native 1–9 Scale)",
        "name_id": "Tingkat Kesiapterapan Teknologi / TKT (Skala Asli NASA 1–9)",
        "description_en": "Maturity of the core technology evaluated against NASA ESTO TRL 1–9 definitions and exit criteria (adapted for industrial/non-aerospace domains).",
        "description_id": "Kematangan teknologi inti yang dievaluasi terhadap definisi dan kriteria keluar TRL 1–9 NASA ESTO (diadaptasi untuk domain industri non-dirgantara).",
        "scale_type": "1-9_trl",
        "min_score": 1,
        "max_score": 9,
        "is_patent_specific": False,
        "origin_classification": "adapted",
        "ref_code": "NASA-TRL-ESTO",
        "source_locator": "NASA ESTO TRL Definitions & Exit Criteria Table, pp. 1-6",
        "cross_domain_note": "Adapted from aerospace flight hardware to general industrial/laboratory prototypes; kept strictly on its native 1-9 integer scale.",
        "default_provisional_weight": 0.0,
        "rubric_levels_json": {
            "1": "TRL 1: Basic principles observed and reported.",
            "2": "TRL 2: Technology concept and/or application formulated.",
            "3": "TRL 3: Analytical and experimental critical function and/or characteristic proof of concept.",
            "4": "TRL 4: Component and/or breadboard validation in laboratory environment.",
            "5": "TRL 5: Component and/or breadboard validation in relevant environment.",
            "6": "TRL 6: System/subsystem model or prototype demonstration in a relevant environment.",
            "7": "TRL 7: System prototype demonstration in an operational environment.",
            "8": "TRL 8: Actual system completed and qualified through test and demonstration.",
            "9": "TRL 9: Actual system proven through successful mission/industrial operations.",
        },
    },
    # 5 Technology Assessment 1-5 Rubrics
    {
        "code": "TECH_NOVELTY",
        "dimension": "technology_assessment",
        "name_en": "Technological Novelty & Differentiation",
        "name_id": "Kebaruan & Diferensiasi Teknologi",
        "description_en": "Degree of technical advancement and functional superiority over existing state-of-the-art solutions.",
        "description_id": "Tingkat kemajuan teknis dan keunggulan fungsional dibandingkan solusi yang sudah ada.",
        "scale_type": "1-5",
        "min_score": 1,
        "max_score": 5,
        "is_patent_specific": False,
        "origin_classification": "proposed",
        "ref_code": None,
        "source_locator": "Proposed TechVal Rubric v1.0 (Explicitly labeled as proposed)",
        "cross_domain_note": None,
        "default_provisional_weight": 0.20,
        "rubric_levels_json": {
            "1": "Level 1: Replicates conventional public-domain techniques with no measurable differentiation.",
            "2": "Level 2: Minor parameter tuning of known methods with unverified performance claims.",
            "3": "Level 3: Clear incremental engineering improvement over baseline alternatives with laboratory evidence.",
            "4": "Level 4: Distinct architectural or material innovation demonstrating superior quantitative performance metrics.",
            "5": "Level 5: Breakthrough paradigm verified across independent tests with transformative efficiency/performance gains.",
        },
    },
    {
        "code": "TECH_VALIDATION",
        "dimension": "technology_assessment",
        "name_en": "Experimental Verification & Reproducibility",
        "name_id": "Verifikasi Eksperimental & Reprodusibilitas",
        "description_en": "Completeness, rigor, and repeatability of laboratory or pilot test logs supporting technical claims.",
        "description_id": "Kelengkapan, ketelitian, dan keterulangan log pengujian laboratorium atau pilot yang mendukung klaim teknis.",
        "scale_type": "1-5",
        "min_score": 1,
        "max_score": 5,
        "is_patent_specific": False,
        "origin_classification": "adapted",
        "ref_code": "NASA-TRL-ESTO",
        "source_locator": "NASA ESTO Exit Criteria Verification Standards, Section 2, pp. 2-5",
        "cross_domain_note": "Adapted from NASA exit-criteria test rigor to general R&D documentation.",
        "default_provisional_weight": 0.20,
        "rubric_levels_json": {
            "1": "Level 1: Theoretical assertions only; no empirical test measurements provided.",
            "2": "Level 2: Single-run bench observation without control baseline or instrumentation logs.",
            "3": "Level 3: Controlled laboratory test series with documented operating conditions and baseline comparison.",
            "4": "Level 4: Multi-hour pilot or relevant-environment test logs with statistical repeatability metrics.",
            "5": "Level 5: Independently certified third-party or full operational field validation across extended cycles.",
        },
    },
    {
        "code": "TECH_SCALABILITY",
        "dimension": "technology_assessment",
        "name_en": "Engineering Scalability & Manufacturing Feasibility",
        "name_id": "Skalabilitas Rekayasa & Kelayakan Manufaktur",
        "description_en": "Feasibility of scaling production using accessible materials, equipment, and quality controls.",
        "description_id": "Kelayakan peningkatan skala produksi menggunakan material, peralatan, dan kendali mutu yang tersedia.",
        "scale_type": "1-5",
        "min_score": 1,
        "max_score": 5,
        "is_patent_specific": False,
        "origin_classification": "proposed",
        "ref_code": None,
        "source_locator": "Proposed TechVal Rubric v1.0",
        "cross_domain_note": None,
        "default_provisional_weight": 0.20,
        "rubric_levels_json": {
            "1": "Level 1: Relies on prohibitive exotic materials or non-scalable manual micro-fabrication.",
            "2": "Level 2: Scaling bottlenecks identified but no engineering process flow or bill of materials exists.",
            "3": "Level 3: Preliminary process flow diagram and bill of materials defined for batch fabrication.",
            "4": "Level 4: Pilot-scale unit operations demonstrated with qualified domestic/regional component suppliers.",
            "5": "Level 5: Full industrial manufacturing tolerances, QA/QC protocols, and supply chain audited.",
        },
    },
    {
        "code": "TECH_PATENT_STRENGTH",
        "dimension": "technology_assessment",
        "name_en": "Patent Claim Scope & Technical Defensibility (Patent-Specific)",
        "name_id": "Cakupan Klaim Paten & Ketahanan Teknis (Spesifik Paten)",
        "description_en": "Breadth of independent patent claims and resistance to trivial design-around (may be marked Not Applicable for non-patent IP).",
        "description_id": "Keluasan klaim paten independen dan ketahanan terhadap rekayasa balik (dapat ditandai Tidak Berlaku untuk KI non-paten).",
        "scale_type": "1-5",
        "min_score": 1,
        "max_score": 5,
        "is_patent_specific": True,
        "origin_classification": "adapted",
        "ref_code": "HARHOFF-2003",
        "source_locator": "Harhoff et al. (2003), Section 3 (Patent Value Determinants), pp. 1348-1352",
        "cross_domain_note": "Evaluates qualitative claim scope; patent citations/family size remain contextual signals only.",
        "default_provisional_weight": 0.20,
        "rubric_levels_json": {
            "1": "Level 1: Narrow picture claims easily bypassed by minor parameter substitution.",
            "2": "Level 2: Pending application with unresolved prior-art novelty objections.",
            "3": "Level 3: Granted national patent covering core process or apparatus configuration.",
            "4": "Level 4: Granted patent with broad independent claims covering both method and system architecture.",
            "5": "Level 5: Multi-jurisdictional patent family surviving examination/opposition with high barrier to design-around.",
        },
    },
    {
        "code": "TECH_SYSTEM_INTEGRATION",
        "dimension": "technology_assessment",
        "name_en": "System Integration & Operational Compatibility",
        "name_id": "Integrasi Sistem & Kompatibilitas Operasional",
        "description_en": "Ease of integrating the technology into existing industrial plants or user workflows.",
        "description_id": "Kemudahan mengintegrasikan teknologi ke dalam fasilitas industri atau alur kerja pengguna yang ada.",
        "scale_type": "1-5",
        "min_score": 1,
        "max_score": 5,
        "is_patent_specific": False,
        "origin_classification": "proposed",
        "ref_code": None,
        "source_locator": "Proposed TechVal Rubric v1.0",
        "cross_domain_note": None,
        "default_provisional_weight": 0.20,
        "rubric_levels_json": {
            "1": "Level 1: Requires complete replacement of host facility infrastructure with incompatible interfaces.",
            "2": "Level 2: Interface specifications undefined; major retrofit engineering required.",
            "3": "Level 3: Standard mechanical/electrical/software interfaces defined for retrofit integration.",
            "4": "Level 4: Drop-in modular skid or subsystem verified with standard industrial utility connections.",
            "5": "Level 5: Plug-and-play deployment proven across multiple operational host environments.",
        },
    },
    # 5 Commercialization Readiness 1-5 Rubrics
    {
        "code": "COMM_MARKET_DEMAND",
        "dimension": "commercialization_readiness",
        "name_en": "Documented Market Demand & Customer Pain Point",
        "name_id": "Permintaan Pasar Terdokumentasi & Kebutuhan Industri",
        "description_en": "Strength of cited evidence demonstrating addressable market need and customer willingness to adopt.",
        "description_id": "Kekuatan bukti terutip yang menunjukkan kebutuhan pasar sasaran dan kesiapan adopsi pelanggan.",
        "scale_type": "1-5",
        "min_score": 1,
        "max_score": 5,
        "is_patent_specific": False,
        "origin_classification": "proposed",
        "ref_code": None,
        "source_locator": "Proposed TechVal Rubric v1.0",
        "cross_domain_note": None,
        "default_provisional_weight": 0.20,
        "rubric_levels_json": {
            "1": "Level 1: Speculative market claim with no cited industry data or customer validation.",
            "2": "Level 2: General macroeconomic sector overview without technology-specific demand linkage.",
            "3": "Level 3: Cited industry/regulatory market study identifying target customer segment and pain point.",
            "4": "Level 4: Direct industrial partner letters of intent (LOI) or pilot trial agreements documented.",
            "5": "Level 5: Binding commercial off-take, licensing term sheet, or repeat purchase orders executed.",
        },
    },
    {
        "code": "COMM_COMPETITIVE_POSITION",
        "dimension": "commercialization_readiness",
        "name_en": "Competitive Cost-Performance Advantage",
        "name_id": "Keunggulan Biaya-Kinerja Kompetitif",
        "description_en": "Documented total cost of ownership (TCO) or operational value advantage relative to incumbent substitutes.",
        "description_id": "Keunggulan total biaya kepemilikan (TCO) atau nilai operasional dibandingkan produk substitusi.",
        "scale_type": "1-5",
        "min_score": 1,
        "max_score": 5,
        "is_patent_specific": False,
        "origin_classification": "adapted",
        "ref_code": "WIPO-VAL-2024",
        "source_locator": "WIPO IP Valuation Basics Guide, Section 2 (Qualitative Value Drivers), pp. 11-16",
        "cross_domain_note": "Qualitative commercial readiness indicator; never automatically converted into cash flows.",
        "default_provisional_weight": 0.20,
        "rubric_levels_json": {
            "1": "Level 1: Higher unit cost and lower performance than incumbent commercial products.",
            "2": "Level 2: Cost-performance parity unknown; no benchmark against commercial substitutes.",
            "3": "Level 3: Benchmarked against primary incumbents showing competitive operating cost or quality edge.",
            "4": "Level 4: Quantified lifecycle cost reduction or regulatory compliance advantage verified in pilot.",
            "5": "Level 5: Dominant cost-performance leadership with high switching barriers for customers.",
        },
    },
    {
        "code": "COMM_REGULATORY",
        "dimension": "commercialization_readiness",
        "name_en": "Regulatory, Standards & Environmental Compliance Readiness",
        "name_id": "Kesiapan Regulasi, Standar (SNI) & Kepatuhan Lingkungan",
        "description_en": "Alignment with applicable Indonesian (SNI, KLHK, BPOM, Kemenperin) and international standards.",
        "description_id": "Kesesuaian dengan standar regulasi Indonesia (SNI, KLHK, BPOM, Kemenperin) dan internasional.",
        "scale_type": "1-5",
        "min_score": 1,
        "max_score": 5,
        "is_patent_specific": False,
        "origin_classification": "proposed",
        "ref_code": None,
        "source_locator": "Proposed TechVal Rubric v1.0",
        "cross_domain_note": None,
        "default_provisional_weight": 0.20,
        "rubric_levels_json": {
            "1": "Level 1: Severe regulatory barriers or non-compliance with mandatory safety/environmental laws.",
            "2": "Level 2: Applicable regulatory standards not yet mapped or assessed.",
            "3": "Level 3: Applicable regulatory standards mapped; laboratory output meets threshold specifications.",
            "4": "Level 4: Formal certification testing underway or pilot effluent/product certified by accredited lab.",
            "5": "Level 5: All mandatory commercial certifications, permits, and SNI/ISO registrations granted.",
        },
    },
    {
        "code": "COMM_SUPPLY_CHAIN",
        "dimension": "commercialization_readiness",
        "name_en": "Supply Chain, TKDN & Delivery Readiness",
        "name_id": "Kesiapan Rantai Pasok, TKDN & Pengiriman",
        "description_en": "Availability of local/regional component suppliers, domestic content (TKDN), and maintenance support.",
        "description_id": "Ketersediaan pemasok komponen lokal/regional, Tingkat Komponen Dalam Negeri (TKDN), dan layanan purnajual.",
        "scale_type": "1-5",
        "min_score": 1,
        "max_score": 5,
        "is_patent_specific": False,
        "origin_classification": "proposed",
        "ref_code": None,
        "source_locator": "Proposed TechVal Rubric v1.0",
        "cross_domain_note": None,
        "default_provisional_weight": 0.20,
        "rubric_levels_json": {
            "1": "Level 1: Single-source foreign dependencies with high supply disruption risk.",
            "2": "Level 2: Component sourcing and maintenance logistics not yet identified.",
            "3": "Level 3: Key raw materials and fabrication vendors identified with preliminary quotes.",
            "4": "Level 4: High domestic component availability (TKDN readiness) with qualified local fabricators.",
            "5": "Level 5: Contracted multi-vendor supply chain and established field service/consumables network.",
        },
    },
    {
        "code": "COMM_IP_LICENSING_READINESS",
        "dimension": "commercialization_readiness",
        "name_en": "Patent Licensing & Technology Transfer Packaging (Patent-Specific)",
        "name_id": "Kesiapan Lisensi Paten & Paket Alih Teknologi (Spesifik Paten)",
        "description_en": "Clarity of ownership, encumbrance-free patent title, and technical transfer package (may be N/A for non-patent IP).",
        "description_id": "Kejelasan kepemilikan, status hukum paten bebas sengketa, dan kelengkapan paket alih teknologi (dapat N/A untuk non-paten).",
        "scale_type": "1-5",
        "min_score": 1,
        "max_score": 5,
        "is_patent_specific": True,
        "origin_classification": "adapted",
        "ref_code": "WIPO-VAL-2024",
        "source_locator": "WIPO IP Valuation Basics Guide, Section 2.2 (Legal & Institutional Readiness), pp. 13-16",
        "cross_domain_note": "Specific to patent/licensing transfer; may be marked not_applicable when IP is trade secret or unregistered.",
        "default_provisional_weight": 0.20,
        "rubric_levels_json": {
            "1": "Level 1: Disputed inventorship or lapsed patent maintenance fees blocking licensing.",
            "2": "Level 2: Co-ownership rights unassigned; no standard operating manual for licensees.",
            "3": "Level 3: Clear institutional IP assignment (TTO/University) with active patent registration.",
            "4": "Level 4: Complete engineering transfer dossier, SOPs, and draft licensing term sheet prepared.",
            "5": "Level 5: Turnkey technology transfer package validated with active commercial licensee(s).",
        },
    },
]


def seed_initial_data(db: Session) -> Dict[str, Any]:
    """
    Idempotently seeds users, the 5 supplied scientific references, versioned methodology config,
    indicator rubrics, provisional equal weight set, synthetic demo technology & documents,
    demo analysis run, and Phase 4 research evaluation dataset.
    """
    # 1. Seed Users
    users_spec = [
        ("admin@itenas.ac.id", "admin", "Dr. Admin TechVal (ITENAS)", "AdminTechVal2026!", "admin", "en"),
        ("analyst@itenas.ac.id", "analyst", "Rizky Pratama (Analyst)", "AnalystTechVal2026!", "analyst", "id"),
        ("reviewer@itenas.ac.id", "reviewer", "Prof. Hendra Wijaya (Expert Reviewer)", "ExpertTechVal2026!", "expert_reviewer", "en"),
    ]
    created_users: Dict[str, User] = {}
    for email, uname, fname, pwd, role, lang in users_spec:
        existing = db.execute(select(User).where(User.username == uname)).scalar_one_or_none()
        if not existing:
            existing = User(
                email=email,
                username=uname,
                full_name=fname,
                password_hash=hash_password(pwd),
                role=role,
                preferred_language=lang,
                is_active=True,
            )
            db.add(existing)
            db.flush()
        created_users[uname] = existing

    # 2. Seed the 5 Scientific References
    refs_by_code: Dict[str, ScientificReference] = {}
    for r_spec in SEED_SCIENTIFIC_REFERENCES:
        existing_ref = db.execute(
            select(ScientificReference).where(ScientificReference.code == r_spec["code"])
        ).scalar_one_or_none()
        if not existing_ref:
            existing_ref = ScientificReference(**r_spec)
            db.add(existing_ref)
            db.flush()
        refs_by_code[r_spec["code"]] = existing_ref

    # 3. Seed Versioned MethodologyConfig (validating attribution locators!)
    m_cfg = db.execute(
        select(MethodologyConfig).where(MethodologyConfig.version_tag == "methodology_v1.0")
    ).scalar_one_or_none()
    if not m_cfg:
        wipo_ref = refs_by_code["WIPO-VAL-2024"]
        validate_methodology_attribution(
            wipo_ref,
            origin_type="adapted",
            attributed_section="Section 3 (Valuation Methods)",
            attributed_page="pp. 18-39",
        )
        m_cfg = MethodologyConfig(
            version_tag="methodology_v1.0",
            name="TechVal AI Scientific Assessment & WIPO Valuation Methodology v1.0",
            reference_id=wipo_ref.id,
            origin_type="adapted",
            empirical_validation_status="not_empirically_validated",
            attributed_section="Section 3 (Valuation Methods)",
            attributed_page="pp. 18-39",
            normalization_formula="(score - 1) / 4",
            ahp_cr_threshold=0.10,
            rules_json={
                "four_separate_outputs": [
                    "technology_assessment",
                    "commercialization_readiness",
                    "economic_valuation",
                    "evidence_completeness",
                ],
                "score_to_monetary_conversion": "strictly_prohibited",
                "trl_scale": "native_1_to_9",
                "rubric_normalization": "(score - 1) / 4",
                "missing_vs_na_policy": "only_patent_specific_may_be_na_missing_stays_missing",
                "ahp_cr_convention": 0.10,
                "extraction_matching_policy": EXTRACTION_MATCHING_POLICY,
            },
            is_active=True,
        )
        db.add(m_cfg)
        db.flush()

    # 4. Seed Indicator Definitions
    for ind_spec in SEED_INDICATORS:
        existing_ind = db.execute(
            select(IndicatorDefinition).where(IndicatorDefinition.code == ind_spec["code"])
        ).scalar_one_or_none()
        if not existing_ind:
            ref_obj = refs_by_code.get(ind_spec["ref_code"]) if ind_spec.get("ref_code") else None
            existing_ind = IndicatorDefinition(
                code=ind_spec["code"],
                dimension=ind_spec["dimension"],
                name_en=ind_spec["name_en"],
                name_id=ind_spec["name_id"],
                description_en=ind_spec["description_en"],
                description_id=ind_spec["description_id"],
                scale_type=ind_spec["scale_type"],
                min_score=ind_spec["min_score"],
                max_score=ind_spec["max_score"],
                is_patent_specific=ind_spec["is_patent_specific"],
                origin_classification=ind_spec["origin_classification"],
                reference_id=ref_obj.id if ref_obj else None,
                source_locator=ind_spec["source_locator"],
                cross_domain_note=ind_spec["cross_domain_note"],
                rubric_levels_json=ind_spec["rubric_levels_json"],
                default_provisional_weight=ind_spec["default_provisional_weight"],
            )
            db.add(existing_ind)
            db.flush()

    # 5. Seed Provisional Equal WeightSet
    ws = db.execute(
        select(WeightSet).where(WeightSet.version_tag == "provisional_equal_v1")
    ).scalar_one_or_none()
    if not ws:
        equal_weights = {
            ind["code"]: ind["default_provisional_weight"]
            for ind in SEED_INDICATORS
            if ind["scale_type"] == "1-5"
        }
        ws = WeightSet(
            name="Provisional Equal Weights (Baseline v1.0)",
            version_tag="provisional_equal_v1",
            weighting_method="provisional_equal",
            is_provisional=True,
            is_active=True,
            tech_consistency_ratio=0.0,
            comm_consistency_ratio=0.0,
            weights_json=equal_weights,
            methodological_note=(
                "Explicitly provisional equal weights (0.20 per 1-5 indicator within each dimension) "
                "prior to domain-specific AHP pairwise elicitation."
            ),
            created_by=created_users["admin"].id,
        )
        db.add(ws)
        db.flush()

    # 6. Seed Demonstration Technology, Documents, Market Comparables, and Initial Analysis Run
    demo_tech = db.execute(
        select(Technology).where(Technology.code == "ITENAS-PAT-2026-001")
    ).scalar_one_or_none()
    if not demo_tech:
        demo_tech = Technology(
            code="ITENAS-PAT-2026-001",
            title_en="Modular Photocatalytic Membrane Reactor for Industrial Textile Wastewater Reclamation",
            title_id="Reaktor Membran Fotokatalitik Modular untuk Reklamasi Air Limbah Industri Tekstil",
            domain="Environmental & Chemical Process Engineering",
            inventor_organization="ITENAS Environmental & Membrane Research Group",
            description_en=(
                "[SYNTHETIC DEMONSTRATION FIXTURE] Closed-loop tubular ceramic ultrafiltration reactor "
                "coated with TiO2-graphene nanocomposite for continuous textile effluent reclamation."
            ),
            description_id=(
                "[DATA DEMONSTRASI SINTETIS] Reaktor ultrafiltrasi keramik tubular siklus tertutup berlapis "
                "nanokomposit TiO2-grafena untuk reklamasi efluen tekstil kontinu."
            ),
            claimed_trl=6,
            patent_status="granted",
            patent_Application_number="IDP000089421",
            patent_jurisdiction="ID",
            status="under_review",
            is_synthetic_demo=True,
            created_by=created_users["analyst"].id,
        )
        db.add(demo_tech)
        db.flush()

        # Upload & parse demo PDF and DOCX into encrypted vault
        pdf_bytes = build_demo_patent_pdf_bytes()
        opaque_pdf, sha_pdf, path_pdf = store_encrypted_file(pdf_bytes)
        pdf_sections, pdf_ocr, pdf_warn = parse_pdf_bytes(pdf_bytes)
        doc_pdf = Document(
            technology_id=demo_tech.id,
            opaque_storage_id=opaque_pdf,
            original_filename="IDP000089421_Patent_And_TRL6_Test_Report.pdf",
            document_type="patent_spec",
            mime_type="application/pdf",
            file_extension=".pdf",
            file_size_bytes=len(pdf_bytes),
            sha256_hash=sha_pdf,
            encrypted_vault_path=str(path_pdf),
            signature_valid=True,
            ocr_required=pdf_ocr,
            ocr_warning_message=pdf_warn or None,
            page_or_section_count=len(pdf_sections),
            extracted_char_count=sum(s["char_count"] for s in pdf_sections),
            uploaded_by=created_users["analyst"].id,
        )
        db.add(doc_pdf)
        db.flush()

        for s in pdf_sections:
            sec_row = DocumentSection(document_id=doc_pdf.id, **s)
            db.add(sec_row)
            db.flush()
            for ch in chunk_section_text(s["location_ref"], s["content_text"]):
                db.add(DocumentChunk(document_id=doc_pdf.id, section_id=sec_row.id, **ch))

        docx_bytes = build_demo_market_docx_bytes()
        opaque_dx, sha_dx, path_dx = store_encrypted_file(docx_bytes)
        dx_sections, dx_ocr, dx_warn = parse_docx_bytes(docx_bytes)
        doc_dx = Document(
            technology_id=demo_tech.id,
            opaque_storage_id=opaque_dx,
            original_filename="ITENAS_Textile_Wastewater_Market_Study_2026.docx",
            document_type="market_study",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_extension=".docx",
            file_size_bytes=len(docx_bytes),
            sha256_hash=sha_dx,
            encrypted_vault_path=str(path_dx),
            signature_valid=True,
            ocr_required=dx_ocr,
            ocr_warning_message=dx_warn or None,
            page_or_section_count=len(dx_sections),
            extracted_char_count=sum(s["char_count"] for s in dx_sections),
            uploaded_by=created_users["analyst"].id,
        )
        db.add(doc_dx)
        db.flush()

        for s in dx_sections:
            sec_row = DocumentSection(document_id=doc_dx.id, **s)
            db.add(sec_row)
            db.flush()
            for ch in chunk_section_text(s["location_ref"], s["content_text"]):
                db.add(DocumentChunk(document_id=doc_dx.id, section_id=sec_row.id, **ch))

        # Seed credible Market Comparables & manual patent family record
        db.add_all(
            [
                MarketComparable(
                    technology_id=demo_tech.id,
                    evidence_category="comparable_transaction",
                    title="Industrial Ceramic Membrane Skid Technology License (West Java Industrial Estate)",
                    source_citation="Indonesian Environmental Equipment Licensing Registry (2025), Entry #ID-ENV-2025-14",
                    source_url_or_doi="https://pdki-indonesia.dgip.go.id/",
                    jurisdiction="ID",
                    transaction_year=2025,
                    unadjusted_value_idr=920_000_000.0,
                    royalty_rate_percent=4.5,
                    adjustment_factor=1.05,
                    adjustment_rationale="+5% adjustment for integrated photocatalytic self-cleaning coating reducing fouling.",
                    is_credible_verified=True,
                    metadata_json={"capacity_m3_day": 15},
                    created_by=created_users["analyst"].id,
                ),
                MarketComparable(
                    technology_id=demo_tech.id,
                    evidence_category="comparable_transaction",
                    title="ASEAN Textile Effluent Ultrafiltration Module Patent Assignment",
                    source_citation="ASEAN WIPO Tech Transfer Compendium (2024), Case Study #SG-ID-09",
                    source_url_or_doi="https://www.wipo.int/patentscope/en/",
                    jurisdiction="ASEAN",
                    transaction_year=2024,
                    unadjusted_value_idr=1_080_000_000.0,
                    royalty_rate_percent=5.0,
                    adjustment_factor=0.92,
                    adjustment_rationale="-8% adjustment for single-jurisdiction granted status vs regional bundle.",
                    is_credible_verified=True,
                    metadata_json={"capacity_m3_day": 20},
                    created_by=created_users["analyst"].id,
                ),
                MarketComparable(
                    technology_id=demo_tech.id,
                    evidence_category="patent_family_record",
                    title="PDKI & PCT Patent Family Record IDP000089421 / WO2025041822",
                    source_citation="DGIP PDKI Indonesia & WIPO Patentscope Official Export (Verified Oct 2026)",
                    source_url_or_doi="https://pdki-indonesia.dgip.go.id/",
                    jurisdiction="ID",
                    transaction_year=2025,
                    unadjusted_value_idr=None,
                    royalty_rate_percent=None,
                    adjustment_factor=1.0,
                    adjustment_rationale="Contextual patent family and citation record per Harhoff et al. (2003).",
                    is_credible_verified=True,
                    metadata_json={
                        "family_size": 3,
                        "forward_citations": 6,
                        "backward_citations": 14,
                        "family_jurisdictions": ["ID", "WO", "SG"],
                    },
                    created_by=created_users["analyst"].id,
                ),
            ]
        )
        db.flush()

        # Create explicit ConsentRecord and execute initial fixture AnalysisRun
        doc_ids = [doc_pdf.id, doc_dx.id]
        doc_hashes = {doc_pdf.id: doc_pdf.sha256_hash, doc_dx.id: doc_dx.sha256_hash}
        config_snapshot = {"rubric_version": "methodology_v1.0", "weight_set": "provisional_equal_v1"}
        run_config_hash = hashlib.sha256(
            json.dumps(
                {
                    "provider": "fixture",
                    "model": "fixture-deterministic-v1",
                    "doc_hashes": doc_hashes,
                    "config": config_snapshot,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()

        consent = ConsentRecord(
            technology_id=demo_tech.id,
            user_id=created_users["analyst"].id,
            provider="fixture",
            model_name="fixture-deterministic-v1",
            transmission_scope="local_fixture_only",
            document_ids_json=doc_ids,
            document_hashes_json=doc_hashes,
            run_config_hash=run_config_hash,
            consent_granted=True,
            consent_statement=(
                "Explicit consent granted for local deterministic fixture analysis of selected documents."
            ),
        )
        db.add(consent)
        db.flush()

        demo_run = AnalysisRun(
            technology_id=demo_tech.id,
            consent_record_id=consent.id,
            methodology_config_id=m_cfg.id,
            weight_set_id=ws.id,
            status="queued",
            requested_provider="fixture",
            requested_model="fixture-deterministic-v1",
            prompt_hash="initial_seed_prompt_hash",
            run_config_hash=run_config_hash,
            config_snapshot_json=config_snapshot,
            rubric_version_tag="methodology_v1.0",
            document_hashes_json=doc_hashes,
            app_version=settings.APP_VERSION,
            created_by=created_users["analyst"].id,
        )
        db.add(demo_run)
        db.commit()

        execute_analysis_run(db, demo_run.id)

    # 7. Seed Phase 4 Research Evaluation Dataset & Experiment (Prominently labeled synthetic!)
    ds = db.execute(
        select(ExperimentDataset).where(ExperimentDataset.code == "SYNTH-BENCHMARK-2026-V1")
    ).scalar_one_or_none()
    if not ds:
        items = build_synthetic_evaluation_dataset_items()
        manifest_hash = hashlib.sha256(json.dumps(items, sort_keys=True).encode("utf-8")).hexdigest()
        ds = ExperimentDataset(
            code="SYNTH-BENCHMARK-2026-V1",
            name="[SYNTHETIC DEMO] 4-Condition Technology Assessment & Valuation Benchmark v1.0",
            version_tag="v1.0-synthetic",
            description=(
                "SYNTHETIC DEMONSTRATION DATASET: Matched evaluation fixture comparing Human Expert, "
                "LLM-Only Baseline, Unvalidated Multi-Agent, and Evidence-Validated Multi-Agent pipelines. "
                "Isolated for statistical pipeline verification only; no empirical accuracy claims are made."
            ),
            is_synthetic_demo=True,
            manifest_hash=manifest_hash,
            access_roles_json=["admin", "analyst", "expert_reviewer"],
            items_json=items,
        )
        db.add(ds)
        db.flush()

        eval_results = evaluate_four_conditions_dataset(items, is_synthetic_demo=True)
        exp = Experiment(
            dataset_id=ds.id,
            name="[SYNTHETIC DEMO] Baseline 4-Condition Benchmark Run #1",
            is_synthetic_demo=True,
            conditions_compared_json=["human_expert", "llm_only", "multi_agent", "multi_agent_validated"],
            manifest_json={
                "dataset_code": ds.code,
                "dataset_version": ds.version_tag,
                "manifest_hash": manifest_hash,
                "app_version": settings.APP_VERSION,
                "is_synthetic_demo": True,
            },
            metrics_summary_json=eval_results,
            per_condition_results_json=eval_results["conditions_summary"],
            matching_policy_note=EXTRACTION_MATCHING_POLICY,
            created_by=created_users["admin"].id,
        )
        db.add(exp)
        db.commit()

    return {
        "users_seeded": len(created_users),
        "references_seeded": len(refs_by_code),
        "demo_technology_code": "ITENAS-PAT-2026-001",
    }
