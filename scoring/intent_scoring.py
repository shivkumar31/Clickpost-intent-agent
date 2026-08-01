import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.schemas import CompanySignals, RankedAccount

WEIGHTS = {
    "Competitor Usage": 30,
    "Customer Pain": 25,
    "Hiring Signals": 20,
    "Growth Signals": 15,
    "Leadership Changes": 10,
}

MAX_SCORE = sum(WEIGHTS.values())

CONFIDENCE_THRESHOLD = 0.5


def score_company(company_signals: CompanySignals) -> RankedAccount:
    categories_found = set()
    reasons = []

    for category in WEIGHTS:
        matching = [
            s for s in company_signals.signals
            if s.category == category and s.confidence >= CONFIDENCE_THRESHOLD
        ]
        if matching:
            categories_found.add(category)
            best = max(matching, key=lambda s: s.confidence)
            reasons.append(f"{category}: {best.description} (+{WEIGHTS[category]})")

    score = sum(WEIGHTS[c] for c in categories_found)

    return RankedAccount(
        company=company_signals.company,
        score=score,
        max_score=MAX_SCORE,
        reasons=reasons,
        categories_found=sorted(categories_found),
        signals=company_signals.signals,
    )


def rank_companies(all_company_signals: list) -> list:
    ranked = [score_company(cs) for cs in all_company_signals]
    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked
