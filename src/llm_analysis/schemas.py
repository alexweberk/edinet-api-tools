# schemas.py
from pydantic import BaseModel, Field

from src.constants import (
    MAX_COMPANY_DESCRIPTION_WORDS,
    MAX_IMPACT_RATIONALE_WORDS,
    MAX_SUMMARY_WORDS,
)


class OneLineSummary(BaseModel):
    """Concise one-line summary of the key event or data point in the disclosure."""

    company_name_en: str = Field(..., description="Company name in English.")
    summary: str = Field(
        ...,
        description=f"Ultra concise (<{MAX_SUMMARY_WORDS} words) explanation of the key event or data point, focusing on what was decided or done.",
    )


class ExecutiveSummary(BaseModel):
    """Insightful, concise executive summary and key highlights."""

    company_name_en: str = Field(..., description="Company name in English (all caps).")
    company_description_short: str | None = Field(
        None,
        description=f"Very concise (<{MAX_COMPANY_DESCRIPTION_WORDS} words) summary of what the company does.",
    )
    summary: str = Field(
        ...,
        description="Insightful and concise executive summary interpreting the data with a strategic lens.",
    )
    key_highlights: list[str] = Field(
        ...,
        description="Key takeaways or important points from the disclosure as bullet points.",
    )
    potential_impact_rationale: str | None = Field(
        None,
        description=f"Very concise (<{MAX_IMPACT_RATIONALE_WORDS} words) summary of the potential impact, with rationale.",
    )
