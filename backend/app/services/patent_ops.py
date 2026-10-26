from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from app.config import settings


HARHOFF_CITATION_NOTE = (
    "Per Harhoff, Scherer, & Vopel (2003), Research Policy 32(8), 1343–1363 (Sections 3–4, pp. 1348–1358), "
    "forward patent citations, family size, and opposition survival are treated strictly as contextual "
    "qualitative/ordinal signals of technological importance and never as universal monetary multipliers."
)


class EPOOPSAdapter:
    """
    Adapter for European Patent Office (EPO) Open Patent Services (OPS) v3.2 API,
    plus structured manual import support.
    """

    TOKEN_URL = "https://ops.epo.org/3.2/auth/accesstoken"
    PUBLISHED_DATA_URL = "https://ops.epo.org/3.2/rest-services/published-data/publication/epodoc"

    def __init__(
        self,
        consumer_key: Optional[str] = None,
        consumer_secret: Optional[str] = None,
    ) -> None:
        self.consumer_key = (consumer_key or settings.EPO_OPS_CONSUMER_KEY or "").strip()
        self.consumer_secret = (consumer_secret or settings.EPO_OPS_CONSUMER_SECRET or "").strip()

    @property
    def is_configured(self) -> bool:
        return bool(self.consumer_key and self.consumer_secret)

    def fetch_patent_record(self, publication_number: str) -> Dict[str, Any]:
        """
        Queries EPO OPS if credentials are configured. If credentials are not configured,
        explicitly reports the live integration as unavailable rather than inventing data.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        if not self.is_configured:
            return {
                "live_integration_verified": False,
                "status": "unavailable_missing_credentials",
                "message": (
                    "EPO Open Patent Services (OPS) credentials (EPO_OPS_CONSUMER_KEY / EPO_OPS_CONSUMER_SECRET) "
                    "are not configured. Live EPO query was not executed; use structured manual import."
                ),
                "source_timestamp": now_iso,
                "publication_number": publication_number,
            }

        try:
            with httpx.Client(timeout=15.0) as client:
                token_resp = client.post(
                    self.TOKEN_URL,
                    data={"grant_type": "client_credentials"},
                    auth=(self.consumer_key, self.consumer_secret),
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                token_resp.raise_for_status()
                access_token = token_resp.json().get("access_token")

                bib_resp = client.get(
                    f"{self.PUBLISHED_DATA_URL}/{publication_number}/biblio",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                )
                bib_resp.raise_for_status()
                return {
                    "live_integration_verified": True,
                    "status": "verified_live_epo_ops",
                    "source": "EPO Open Patent Services v3.2",
                    "source_timestamp": now_iso,
                    "publication_number": publication_number,
                    "family_definition": "DOCDB / INPADOC simple & extended patent family",
                    "legal_status_limitations": (
                        "EPO OPS legal status (INPADOC) reflects national office reporting latencies "
                        "and does not constitute a formal freedom-to-operate legal opinion."
                    ),
                    "harhoff_contextual_rule": HARHOFF_CITATION_NOTE,
                    "raw_biblio": bib_resp.json(),
                }
        except Exception as exc:
            return {
                "live_integration_verified": False,
                "status": "live_query_failed",
                "message": f"EPO OPS request failed: {exc}",
                "source_timestamp": now_iso,
                "publication_number": publication_number,
            }


def build_manual_patent_signal_record(
    patent_number: str,
    jurisdiction: str,
    family_size: int,
    forward_citations: int,
    backward_citations: int,
    family_jurisdictions: List[str],
    family_definition: str = "DOCDB simple patent family (same priority claim set)",
    legal_status: str = "Granted / Active (Subject to national fee renewal verification)",
    source_citation: str = "DGIP Indonesia (PDKI) & WIPO Patentscope manual registry export",
) -> Dict[str, Any]:
    """
    Constructs a structured patent signal record from manual imports or extracted patent documents,
    preserving source timestamps, jurisdictions, family definitions, legal-status limitations,
    and Harhoff et al. (2003) contextual interpretation rules.
    """
    if family_size < 0 or forward_citations < 0 or backward_citations < 0:
        raise ValueError("Patent family size and citation counts must be non-negative integers.")

    return {
        "patent_number": patent_number,
        "primary_jurisdiction": jurisdiction,
        "family_size": int(family_size),
        "family_jurisdictions": family_jurisdictions,
        "family_definition": family_definition,
        "forward_citations_count": int(forward_citations),
        "backward_citations_count": int(backward_citations),
        "legal_status": legal_status,
        "legal_status_limitations": (
            "National patent register legal-status entries are subject to administrative publication lags, "
            "annual maintenance fee grace periods, and jurisdictional scope boundaries."
        ),
        "source_citation": source_citation,
        "source_timestamp": datetime.now(timezone.utc).isoformat(),
        "contextual_signal_interpretation": HARHOFF_CITATION_NOTE,
        "monetary_conversion_prohibited": True,
    }
