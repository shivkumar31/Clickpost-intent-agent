import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.schemas import RankedAccount, OutboundSequence, OutreachResult
from llm_client import get_llm

OUTREACH_PROMPT = """You are an SDR at ClickPost, a post-purchase and returns experience \
platform for D2C ecommerce brands doing $5M-$100M GMV. ClickPost replaces manual WISMO \
("where is my order") support and reduces return-to-origin losses with a unified tracking \
and returns experience.

You are writing outbound to: {company}
Target persona: Customer Experience Head / Customer Service Head / CTO / Founder

Strongest signal found for this account:
Category: {category}
Description: {description}
Evidence: {evidence}
Source: {source}

All signals found (for context, use only if relevant):
{all_signals}

Requirements:
1. LinkedIn message: under 100 words, personalized, must reference the strongest signal \
above directly, avoid generic sales language ("Hope you're well", "I came across your company").
2. Follow-up email: needs a subject line, an opening line, a reference to the same signal, \
a ClickPost value proposition framed in the buyer's terms (not generic), and exactly one \
clear call to action.
3. Do not invent facts about the company beyond what's in the signal evidence above.

Return the LinkedIn message and email.
"""


def format_all_signals(account: RankedAccount) -> str:
    if not account.signals:
        return "(none)"
    return "\n".join(
        f"  - [{s.category}] {s.description} (confidence {s.confidence})"
        for s in account.signals
    )


def generate_outreach(account: RankedAccount) -> OutreachResult | None:
    if not account.signals:
        print(f"    ! no signals for {account.company}, skipping outreach generation")
        return None

    top_signal = max(account.signals, key=lambda s: s.confidence)

    llm = get_llm()
    structured_llm = llm.with_structured_output(OutboundSequence)

    prompt = OUTREACH_PROMPT.format(
        company=account.company,
        category=top_signal.category,
        description=top_signal.description,
        evidence=top_signal.evidence,
        source=top_signal.source,
        all_signals=format_all_signals(account),
    )

    try:
        sequence: OutboundSequence = structured_llm.invoke(prompt)
    except Exception as e:
        print(f"    ! outreach generation failed for {account.company}: {e}")
        return None

    return OutreachResult(company=account.company, score=account.score, sequence=sequence)
