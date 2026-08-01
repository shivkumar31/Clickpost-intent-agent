import argparse
import json
import os

import pandas as pd

from agents.research_agent import research_company
from agents.signal_extraction_agent import extract_signals
from agents.outreach_agent import generate_outreach
from scoring.intent_scoring import rank_companies, WEIGHTS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMPANIES_CSV = os.path.join(BASE_DIR, "data", "companies.csv")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

TOP_N_FOR_OUTREACH = 5


def load_companies(limit: int) -> list:
    df = pd.read_csv(COMPANIES_CSV)
    companies = df["company"].tolist()
    return companies[:limit] if limit else companies


def build_outreach_markdown(outreach_results: list) -> str:
    lines = ["# ClickPost Outbound Sequences — Top Accounts\n"]
    for r in outreach_results:
        lines.append(f"## {r.company} (score: {r.score}/100)\n")
        lines.append(f"**Signal referenced:** {r.sequence.signal_referenced}\n")
        lines.append("### LinkedIn Message\n")
        lines.append(f"{r.sequence.linkedin_message}\n")
        lines.append("### Follow-up Email\n")
        lines.append(f"**Subject:** {r.sequence.email_subject}\n")
        lines.append(f"{r.sequence.email_body}\n")
        lines.append("---\n")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="ClickPost Intent Capture & Outbound Activation Agent")
    parser.add_argument("--limit", type=int, default=25, help="Number of companies to research (default: 25, the full dataset)")
    args = parser.parse_args()

    os.makedirs(OUTPUTS_DIR, exist_ok=True)

    taxonomy_path = os.path.join(OUTPUTS_DIR, "taxonomy.json")
    with open(taxonomy_path, "w") as f:
        json.dump(WEIGHTS, f, indent=2)
    print(f"Saved {taxonomy_path}")

    companies = load_companies(args.limit)
    print(f"Researching {len(companies)} companies: {companies}\n")

    all_company_signals = []
    all_raw_results = []

    for company in companies:
        print(f"[+] Researching: {company}")
        hits = research_company(company)
        print(f"    {len(hits)} unique search hits after dedup")
        all_raw_results.append({
            "company": company,
            "hits": [h.model_dump() for h in hits],
        })

        print(f"    extracting signals via LLM...")
        company_signals = extract_signals(company, hits)
        print(f"    {len(company_signals.signals)} signals extracted")

        all_company_signals.append(company_signals)

    raw_results_path = os.path.join(OUTPUTS_DIR, "raw_search_results.json")
    with open(raw_results_path, "w") as f:
        json.dump(all_raw_results, f, indent=2)
    print(f"\nSaved {raw_results_path}")

    print("\n[+] Scoring accounts (deterministic, no LLM)...")
    ranked = rank_companies(all_company_signals)
    for r in ranked:
        print(f"    {r.company}: {r.score}/{r.max_score} — {', '.join(r.categories_found) or 'no signals'}")

    signals_path = os.path.join(OUTPUTS_DIR, "signals.json")
    with open(signals_path, "w") as f:
        json.dump([cs.model_dump() for cs in all_company_signals], f, indent=2)
    print(f"\nSaved {signals_path}")

    def top_signal(r):
        if not r.signals:
            return None, None, None
        best = max(r.signals, key=lambda s: s.confidence)
        return best.category, best.description, best.source

    ranked_rows = []
    for r in ranked:
        top_category, top_evidence, top_source = top_signal(r)
        ranked_rows.append({
            "company": r.company,
            "score": r.score,
            "max_score": r.max_score,
            "categories_found": "; ".join(r.categories_found),
            "reasons": " | ".join(r.reasons),
            "top_category": top_category or "",
            "top_evidence": top_evidence or "",
            "top_source": top_source or "",
        })
    ranked_df = pd.DataFrame(ranked_rows)
    ranked_csv_path = os.path.join(OUTPUTS_DIR, "ranked_accounts.csv")
    ranked_df.to_csv(ranked_csv_path, index=False)
    print(f"Saved {ranked_csv_path}")

    print(f"\n[+] Generating outreach for top {TOP_N_FOR_OUTREACH} accounts...")
    top_accounts = ranked[:TOP_N_FOR_OUTREACH]
    outreach_results = []
    for account in top_accounts:
        print(f"    generating outreach for {account.company}...")
        result = generate_outreach(account)
        if result:
            outreach_results.append(result)

    outreach_md = build_outreach_markdown(outreach_results)
    outreach_path = os.path.join(OUTPUTS_DIR, "outreach.md")
    with open(outreach_path, "w") as f:
        f.write(outreach_md)
    print(f"Saved {outreach_path}")

    print("\nDone. Check outputs/ for taxonomy.json, raw_search_results.json, signals.json, ranked_accounts.csv, and outreach.md")


if __name__ == "__main__":
    main()
