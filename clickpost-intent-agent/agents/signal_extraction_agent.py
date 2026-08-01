import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.schemas import SearchHit, Signal, SignalExtractionResult, CompanySignals, SIGNAL_CATEGORIES
from llm_client import get_llm

EXTRACTION_PROMPT = """You are analyzing public search results to identify buying-intent \
signals for a B2B sales team at ClickPost, a post-purchase/returns/shipping-intelligence \
platform for D2C ecommerce brands ($5M-$100M GMV).

Company being researched: {company}

Signal taxonomy (a signal must fit exactly one of these categories):
- "Competitor Usage": evidence the company uses Loop Returns, AfterShip, Redo, or Onward
- "Customer Pain": public complaints about shipping delays, returns, or refunds
- "Hiring Signals": job postings for Returns Manager, Logistics Manager, CX Manager, Operations Manager
- "Growth Signals": funding, market expansion, new product launches
- "Leadership Changes": new CTO, new VP/Head of Customer Experience

Raw search results, numbered 1 to {num_hits}:
{hits_block}

Instructions:
1. Only extract a signal if a specific numbered result actually supports it. Do not infer or \
guess signals that aren't backed by one of the results above.
2. For "source_index", give the number of the result the signal came from (just the integer, \
e.g. 3 for result 3.) Do not copy the URL itself, just its number.
3. Assign a confidence score reflecting how directly the evidence supports the signal. \
Use the full 0.0-1.0 range with realistic precision (e.g. 0.68, 0.74, 0.81, 0.93) rather than \
round numbers like 1.0, 0.95, or 0.9 -- real evidence quality varies continuously, and a score \
should reflect specific factors like: is this an explicit statement or an inference, how \
recent does the evidence appear, and how directly does it match the category definition. Do \
not default to a round number out of convenience.
4. If none of the results support a given category, do not produce a signal for that category \
-- it's fine and expected for a company to have zero, one, or several signals.
5. Do not fabricate facts not present in the results above.

Return the extracted signals.
"""


def format_hits_block(hits: list) -> str:
    lines = []
    for i, h in enumerate(hits, 1):
        categories = ", ".join(h.category_hints)
        lines.append(
            f"{i}. [{categories}] \"{h.title}\"\n"
            f"   snippet: {h.snippet}\n"
            f"   url: {h.url}"
        )
    return "\n".join(lines) if lines else "(no search results found)"


def extract_signals(company: str, hits: list) -> CompanySignals:
    if not hits:
        return CompanySignals(company=company, signals=[])

    llm = get_llm()
    structured_llm = llm.with_structured_output(SignalExtractionResult)

    prompt = EXTRACTION_PROMPT.format(
        company=company,
        num_hits=len(hits),
        hits_block=format_hits_block(hits),
    )

    try:
        result: SignalExtractionResult = structured_llm.invoke(prompt)
    except Exception as e:
        print(f"    ! signal extraction failed for {company}: {e}")
        return CompanySignals(company=company, signals=[])

    proposed = result.signals
    print(f"    LLM proposed {len(proposed)} signal(s) before validation")

    clean_signals = []
    for s in proposed:
        if s.category not in SIGNAL_CATEGORIES:
            print(f"    ! dropped signal: unknown category '{s.category}'")
            continue
        if not (1 <= s.source_index <= len(hits)):
            print(f"    ! dropped signal: source_index {s.source_index} out of range (1-{len(hits)})")
            continue
        matched_hit = hits[s.source_index - 1]
        clean_signals.append(Signal(
            category=s.category,
            description=s.description,
            evidence=s.evidence,
            source=matched_hit.url,
            confidence=s.confidence,
        ))

    print(f"    {len(clean_signals)} signal(s) survived validation")

    return CompanySignals(company=company, signals=clean_signals)
