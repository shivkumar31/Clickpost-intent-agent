# Memo: ClickPost Intent Capture & Outbound Activation Agent

## 1. Signal Taxonomy

The system ranks companies using five buying-intent signal categories.

| Category | Weight | Reason |
|----------|-------:|--------|
| Competitor Usage | 30 | Indicates the company already uses a competing post-purchase solution, making replacement opportunities more likely. |
| Customer Pain | 25 | Public complaints about shipping, returns, or refunds suggest immediate operational pain. |
| Hiring Signals | 20 | Hiring for logistics, returns, or customer operations indicates investment in post-purchase processes. |
| Growth Signals | 15 | Funding, expansion, or new product launches often increase logistics complexity. |
| Leadership Changes | 10 | New technology or customer experience leaders may evaluate existing tools and vendors. |

The score is the sum of the weights for all detected signal categories.

---

## 2. Methodology

Pipeline:

```
Companies
    ↓
DuckDuckGo Search
    ↓
Filter & Deduplicate Results
    ↓
Gemini Signal Extraction
    ↓
Validation
    ↓
Deterministic Scoring
    ↓
Rank Accounts
    ↓
Generate Outreach
```

For each company, the system performs targeted searches for:

- Hiring
- Customer Pain
- Competitor Usage (Loop Returns, AfterShip, Redo, Onward)
- Growth
- Leadership

Search results are filtered to remove noisy domains, deduplicated by URL, and then passed to Gemini for structured signal extraction. The extracted signals are validated before deterministic scoring.

---

## 3. Key Tradeoffs

- Used DuckDuckGo instead of paid data providers to satisfy the assignment constraints.
- Used deterministic scoring instead of LLM-based scoring to keep rankings explainable and reproducible.
- Relied on search snippets instead of full-page scraping because many relevant websites restrict automated scraping.
- Prioritized trusted sources while still allowing other relevant search results to improve coverage.

---

## 4. Future Improvements

With more time or data, I would:

- Integrate official APIs (Greenhouse, Lever, Ashby) etc. for hiring signals.
- Use historical sales outcomes to learn better scoring weights.
- Store previous runs to track new signals and avoid duplicate outreach.
- Add human review for low-confidence signals before outreach generation.
