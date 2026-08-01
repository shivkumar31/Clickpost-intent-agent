from typing import List, Optional
from pydantic import BaseModel, Field

SIGNAL_CATEGORIES = [
    "Competitor Usage",
    "Customer Pain",
    "Hiring Signals",
    "Growth Signals",
    "Leadership Changes",
]


class SearchHit(BaseModel):
    title: str
    url: str
    snippet: str
    queries: List[str]
    category_hints: List[str]
    is_trusted: bool = False


class Signal(BaseModel):
    category: str = Field(description=f"Must be one of: {SIGNAL_CATEGORIES}")
    description: str = Field(description="Short plain-English description of the signal")
    evidence: str = Field(description="The specific fact from the source that supports this")
    source: str = Field(description="URL the evidence came from")
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="0-1 confidence that this is a real, current signal (not stale or ambiguous)"
    )


class ExtractedSignal(BaseModel):
    category: str = Field(description=f"Must be one of: {SIGNAL_CATEGORIES}")
    description: str = Field(description="Short plain-English description of the signal")
    evidence: str = Field(description="The specific fact from the source that supports this")
    source_index: int = Field(description="The number of the search result this signal came from, exactly as shown in the numbered list (e.g. 3 for result 3.)")
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="0-1 confidence that this is a real, current signal (not stale or ambiguous)"
    )


class SignalExtractionResult(BaseModel):
    signals: List[ExtractedSignal] = Field(default_factory=list)


class CompanySignals(BaseModel):
    company: str
    signals: List[Signal] = Field(default_factory=list)


class RankedAccount(BaseModel):
    company: str
    score: int
    max_score: int
    reasons: List[str]
    categories_found: List[str]
    signals: List[Signal]


class OutboundSequence(BaseModel):
    linkedin_message: str = Field(
        description="Under 100 words, personalized, references the actual signal, no generic sales language"
    )
    email_subject: str
    email_body: str = Field(
        description="Opening line, signal reference, ClickPost value proposition, one clear CTA"
    )
    signal_referenced: str = Field(
        description="One sentence naming exactly which signal this sequence is grounded in"
    )


class OutreachResult(BaseModel):
    company: str
    score: int
    sequence: OutboundSequence
