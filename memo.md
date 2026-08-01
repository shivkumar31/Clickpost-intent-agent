# Memo: ClickPost Intent Capture & Outbound Activation Agent

## 1. Intent Taxonomy

Five signal categories, weighted by how directly they predict a live
buying conversation for ClickPost's post-purchase/returns platform:

| Category | Weight | Why it signals intent |
|---|---|---|
| Competitor Usage | 30 | The company already uses Loop, AfterShip, Redo, or Onward — they understand the problem space and have a concrete incumbent to displace. This is the strongest signal because it confirms an active vendor relationship, not just a hypothetical need. |
| Customer Pain | 25 | Public complaints about shipping/returns/refunds indicate current, felt pain — not a future risk. Urgency is highest when the pain is visible and public. |
| Hiring Signals | 20 | Job postings for Returns Manager, Logistics Manager, CX Manager, or Operations Manager indicate the company is actively building out the function ClickPost serves — a buying committee is forming. |
| Growth Signals | 15 | Funding, market expansion, and new product launches predict *future* logistics complexity, but don't confirm current pain. Weighted lower deliberately — this is the easiest signal to find and the weakest on its own. |
| Leadership Changes | 10 | A new CTO or VP of CX often re-evaluates the vendor stack in their first 90 days, but this is speculative until paired with another signal. Weighted lowest because a title change alone says little about current pain. |

**Design choice**: Competitor Usage and Customer Pain (the two
"pain-is-real-right-now" categories) together make up 55 of the 100
points, while Growth Signals and Leadership Changes (the two
"pain-might-be-coming" categories) make up only 25. This mirrors the
brief's explicit caution against over-indexing on generic growth news —
an account that just raised funding but shows no other signal should not
outrank one with an active competitor-tool complaint.

## 2. Data Collection Methodology

- **Search tool**: DuckDuckGo (`duckduckgo-search`), free and
  unauthenticated. No paid enrichment or data-broker tools used, per the
  constraints.
- **Query design**: one short query per signal category per company,
  except Competitor Usage, which gets one query per named competitor (8
  total: 1 Hiring, 1 Customer Pain, 4 Competitor Usage — Loop Returns,
  AfterShip, Redo, Onward, each quoted separately — 1 Growth, 1
  Leadership). Splitting Competitor Usage into four queries instead of
  combining competitor names into one query produces cleaner
  per-competitor evidence, at the cost of more search calls. Queries
  deliberately avoid `site:` filters, `OR` operators, and long boolean
  chains — DuckDuckGo's free-text search returns more relevant results
  for short, natural-language-style queries than for search-engine-style
  operator chains. Each hit tracks the research intent(s) that surfaced
  it via `category_hints` on the SearchHit. One caveat worth naming:
  "Redo" and "Onward" are common English words on their own (unlike
  "Loop Returns" or "AfterShip," which are distinctive multi-word
  phrases), so those two queries are more prone to false-positive
  matches even with exact-phrase quoting — the domain
  filtering/preference layer below is the main mitigation.
- **Domain filtering**: some queries collide on the company name as a
  common word rather than the company itself — e.g. a query containing
  "Chubbies" can surface Pinterest boards or TikTok videos that merely
  contain the word "chubbies," which is not buying-intent evidence.
  `agents/research_agent.py:BLOCKED_DOMAINS` drops known irrelevant
  platforms (Pinterest, TikTok, Amazon, YouTube, Instagram, Facebook,
  Etsy, eBay) before a hit is even added to the dedup set, so they never
  reach the LLM prompt or `raw_search_results.json`. This is a
  blocklist, not a strict allowlist of "good" domains — an allowlist
  risked dropping legitimate sources like Greenhouse/Lever job pages
  (essential for Hiring Signals) or smaller press outlets that wouldn't
  be on any curated list. The blocklist can't catch every irrelevant
  result (a random blog mentioning the company in passing, for example,
  still gets through), so this is a partial fix — the extraction agent's
  own "only extract what's grounded in evidence" instruction is the
  second line of defense against noise that slips past the filter.
- **Trusted-domain preference and cap**: alongside the blocklist,
  `agents/research_agent.py:TRUSTED_DOMAINS_BY_CATEGORY` names sources
  especially relevant to each specific taxonomy category — trust is
  scoped per category, not global. Reddit and Trustpilot are trusted for
  Customer Pain, but not for Hiring, Growth, or Leadership; LinkedIn is
  trusted for both Hiring and Leadership Changes (job postings and
  executive-hire announcements both show up there), but not for
  Competitor Usage. A domain being generally reputable doesn't make it
  authoritative for every kind of claim — Reddit is a strong source for
  a customer complaining about shipping, but not for verifying a funding
  round. Plus a lightweight heuristic, applied regardless of category,
  that treats a domain containing the company's own name as a likely
  official source. If the same URL is later revisited under a different
  query/category (e.g. a page found by both the Hiring query and the
  Competitor Usage query), its `is_trusted` flag is OR'd across every
  category it was found under, rather than only reflecting whichever
  query happened to discover it first. Sorting trusted hits first isn't
  enough on its own: if a query returns mostly noise with one trusted
  result buried in it, sorting just reorders the noise, it doesn't
  remove it. So each query fetches up to 8 raw results, and after
  sorting trusted-first (within that query's own category), only the
  top `MAX_KEPT_PER_QUERY` (4) are kept — the rest are dropped, not just
  deprioritized. Because trusted hits are always sorted to the front,
  they always survive the cap; low-quality results only get cut once
  there's no room left after the trusted ones. Non-trusted sources
  aren't blocked outright (unlike `BLOCKED_DOMAINS`), so a legitimate
  but unlisted source can still make it in if it ranks in the top 4 —
  the cap trims volume, it doesn't enforce a strict allowlist. Every
  hit's `is_trusted` status is saved to `raw_search_results.json` for
  transparency, but it isn't surfaced
  in the LLM prompt itself — extraction quality is judged on evidence
  content, not domain reputation.
- **Deduplication**: hits are deduplicated by URL, not by query. Two
  different queries can easily return the same page — e.g. a Loop
  Returns customer case study showing up for both the hiring query and
  the competitor query — and what matters for scoring is the evidence
  (the page), not which query happened to find it. Deduplicated hits
  keep a `queries` list (every query that surfaced that URL) and a
  `category_hints` list, so traceability isn't lost, but the same page
  is never sent to the LLM twice. This meaningfully cuts prompt size —
  a company with 40+ raw hits across 8 queries often collapses to
  significantly fewer unique URLs once overlap is removed.
- **Scraping**: `tools/scraper.py` (BeautifulSoup4) is available for
  light enrichment of a specific URL when needed, but the primary
  evidence source is search snippets, since sites most useful for this
  research (LinkedIn, G2, Trustpilot) actively block scraping. Relying
  on DuckDuckGo's indexed snippets stays within each source's ToS at the
  cost of losing some full-text nuance.
- **Coverage**: default run researches all 25 companies in
  `data/companies.csv` — 8 search queries per company (200 total). Every
  unique (deduplicated) search hit is saved to
  `outputs/raw_search_results.json` independently of signal extraction,
  so evidence coverage is verifiable even for accounts that ended up
  with zero extracted signals.

## 3. Scoring Methodology

Deterministic, rule-based, implemented in plain Python
(`scoring/intent_scoring.py`) with **no LLM involvement in the score
itself**:

1. The LLM (signal extraction agent) proposes structured signals from
   raw search evidence, each tagged with a category and a confidence
   score (0.0-1.0), and required to cite the exact source URL.
2. A defensive filter drops any signal whose category isn't in the fixed
   taxonomy or whose source URL doesn't match one of the actual search
   hits — this guards against the LLM fabricating evidence despite
   prompt instructions.
3. For each category, if at least one surviving signal has confidence
   ≥ 0.5, that category counts and its full weight is added to the
   score. (Binary per-category, not summed per-signal — so an account
   with three weak Customer Pain mentions doesn't outscore one with a
   single strong one; presence of the category is what matters, per the
   taxonomy's design.)
4. The final score, its category breakdown, and the specific
   description/evidence backing each category are all saved together —
   nothing in `ranked_accounts.csv` is a bare number without a reason
   attached in the same row. The CSV also includes `top_category` and
   `top_source`, pointing at the single highest-confidence signal for
   the account, so a reviewer can click straight through to the source
   URL without opening `signals.json`.

**Verification chain**: every score traces back through three saved
artifacts — `Signal (signals.json)` → `Search Result
(raw_search_results.json)` → `URL (top_source in ranked_accounts.csv)`.
Nothing in the pipeline is a claim without a URL behind it.

This keeps the score fully auditable: given `signals.json` and
`scoring/intent_scoring.py`, anyone can recompute any account's score by
hand.

## 4. Tradeoffs

- **Search snippets over full scraping**: faster and ToS-compliant, but
  loses some nuance — a snippet might miss context a full page would
  show. Documented as a known limitation rather than worked around with
  a scraper that would violate site ToS.
- **Binary per-category scoring over volume-weighted scoring**: simpler
  to defend to a sales leader ("Customer Pain is present, +25") than a
  formula that also factors in *how many* pain mentions were found,
  which would need more calibration data to weight sensibly.
- **Fixed 0.5 confidence threshold**: applied uniformly across all five
  categories for simplicity. In practice, some categories (e.g.
  Leadership Changes, which is easy to state with false confidence from
  a stale press mention) probably warrant a higher bar than others (e.g.
  a literal job-posting title, which is either there or it isn't).
- **Full 25-company default**: prioritizes complete dataset coverage,
  matching what the assignment actually provides, over a faster partial
  run. This is 200 search calls (8 queries x 25 companies) with
  polite delays between them, which is manageable but still carries some
  risk of a DuckDuckGo rate-limit interrupting a run partway through —
  `tools/search_tool.py` retries each query with backoff to reduce that
  risk.
- **Gemini 3.5 Flash-Lite**: fast and cost-effective for structured
  extraction/generation at this scope. Like any lighter-weight model, it
  can still miss subtle or implicit signals in ambiguous search
  snippets — some real signals are likely missed rather than fabricated,
  which is the safer failure mode for a "trust the score" system but
  does mean recall is imperfect.
- **Confidence score calibration**: the extraction prompt explicitly
  asks for realistic, non-round confidence values (e.g. 0.74 rather than
  0.9 or 1.0), since models tend to default to round numbers when a
  score isn't tightly anchored to a rubric. This makes output look more
  like genuine calibrated judgment, but it's worth being honest that
  it's still a model's self-reported confidence, not a statistically
  validated probability — treat relative ordering (is this signal more
  or less confident than that one) as more meaningful than the absolute
  number.

## 5. Limitations

- No SQL / persistent database — every run is a fresh pass over
  `data/companies.csv`. There's no dedup or "already contacted"
  tracking across runs; that would be the first thing to add before any
  production use.
- Signal extraction accuracy depends on DuckDuckGo's index actually
  surfacing the relevant page (career listing, review, press mention)
  in the first few results — for companies with weak SEO presence per
  category, the system will under-report signals rather than over-report
  them.
- No verification that a company's GMV is actually in ClickPost's
  $5M-$100M ICP band; the take-home brief says to assume qualification
  unless research clearly shows otherwise, and this prototype doesn't
  independently check company size.
- `MAX_KEPT_PER_QUERY` (4) trims noise by volume, not by relevance
  judgment — if a query happens to return several trusted results, a
  legitimate but untrusted/unlisted source ranked 5th or lower in that
  same query gets dropped along with the actual noise, even though it
  might have been real evidence. This trades a small amount of recall
  for a real cut in irrelevant content reaching the LLM; raising the cap
  is a one-line change if that tradeoff should go the other way.

## 6. Coverage — This Run

All 25 companies in `data/companies.csv` were researched (default
`python main.py`, no `--limit` override). `[FILL IN after running: note
any companies that returned near-zero search hits, or whose signals
didn't clear the confidence threshold and so scored 0 — check
outputs/raw_search_results.json for those companies to confirm it's a
genuine lack of public signal versus a search-query gap.]`

## 7. Future Improvements

- Job-board API integration (Greenhouse/Lever/Ashby have public JSON
  endpoints) for Hiring Signals instead of search-based detection —
  much more reliable than DuckDuckGo snippets for that category
  specifically, and avoids the SEO-visibility problem entirely.
- A feedback loop: track which AI-flagged accounts actually convert to
  SDR-worked opportunities, and use that data to empirically re-weight
  the taxonomy instead of the current fixed weights.
- Per-category confidence thresholds, tuned once real outcome data
  exists.
- A lightweight persistence layer (even just an append-only JSON log,
  still no SQL needed) to avoid re-surfacing accounts an SDR has already
  worked, and to track signal recency across repeated runs.
