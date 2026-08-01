# ClickPost Intent Capture & Outbound Activation Agent

A CLI-based Python prototype that identifies which D2C ecommerce brands are
showing buying intent for ClickPost's post-purchase, shipping intelligence,
and returns platform — and generates grounded, personalized outbound for
the highest-intent accounts.

Built for the ClickPost AI Engineer Intern take-home.

## 1. Project Overview

Given a list of D2C brands, the system:

1. **Researches** each company via public search (hiring pages, complaint
   mentions, competitor-tool mentions, funding/growth news, leadership
   changes).
2. **Extracts** structured buying-intent signals from that raw research
   using an LLM, grounded strictly in the evidence found (no invented
   signals).
3. **Scores** each account deterministically — plain Python, no LLM
   involved in the actual number — against a fixed weighted taxonomy.
4. **Explains** every score with the specific signals that produced it.
5. **Generates** a personalized LinkedIn message + follow-up email for the
   top 5 accounts, each explicitly grounded in the strongest signal found.

No web app, no FastAPI, no SQL database — this is a straight CLI pipeline
that reads a CSV and writes JSON/CSV/Markdown files.

## 2. Architecture

```
Company List (data/companies.csv)
      |
      v
Research Agent  ---------- tools/search_tool.py (DuckDuckGo)
      |                     tools/scraper.py (BeautifulSoup4, optional enrichment)
      v
Raw Search Results (JSON) -- saved to outputs/raw_search_results.json
      |
      v
Signal Extraction Agent  -- LLM (Gemini 3.5 Flash-Lite), structured output
      |
      v
Validated Signals (Pydantic) -- saved to outputs/signals.json
      |
      v
Deterministic Scoring  ---- scoring/intent_scoring.py (pure Python, NO LLM)
      |                      weights exported to outputs/taxonomy.json
      v
Ranked Accounts -- saved to outputs/ranked_accounts.csv
      |
      v
Top 5 Accounts
      |
      v
Outreach Agent  ----------- LLM (Gemini 3.5 Flash-Lite), structured output
      |
      v
LinkedIn Message + Email -- saved to outputs/outreach.md
```

**Why scoring has no LLM in it:** the rubric this project is built against
explicitly wants a score "a sales leader can trust or push back on," not a
black box. A fixed weighted sum is 100% reproducible — the same signals
always produce the same score. The LLM's job stops at extracting what's
in the evidence; it never decides how many points that's worth.

### Directory layout

```
clickpost-intent-agent/
├── main.py                        # CLI entry point, orchestrates the pipeline
├── llm_client.py                  # LLM config (Gemini 3.5 Flash-Lite via langchain-google-genai)
├── requirements.txt
├── agents/
│   ├── research_agent.py          # fires category-scoped search queries
│   ├── signal_extraction_agent.py # LLM: raw hits -> structured Signal objects
│   └── outreach_agent.py          # LLM: top accounts -> LinkedIn + email
├── tools/
│   ├── search_tool.py             # DuckDuckGo wrapper
│   └── scraper.py                 # BeautifulSoup4 page fetcher (optional enrichment)
├── scoring/
│   └── intent_scoring.py          # deterministic weighted scoring, NO LLM
├── models/
│   └── schemas.py                 # all Pydantic models
├── data/
│   └── companies.csv              # the 25 sample D2C brands
├── outputs/
│   ├── taxonomy.json               # exported scoring weights (from scoring/intent_scoring.py)
│   ├── raw_search_results.json    # every raw search hit, before extraction/scoring
│   ├── signals.json               # every extracted signal, all companies
│   ├── ranked_accounts.csv        # scored + ranked accounts (with top_evidence, top_source)
│   └── outreach.md                # top 5 LinkedIn + email sequences
└── memo.md                        # taxonomy reasoning, methodology, tradeoffs
```

## 3. Installation

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 4. Environment Setup

This project uses **Gemini 3.5 Flash-Lite** via `langchain-google-genai`
— no Anthropic/Claude API, no local model server.

```bash
cp .env.example .env
# edit .env and add your key:
# GOOGLE_API_KEY=your-api-key
```

Get a free key at https://aistudio.google.com/apikey. `llm_client.py`
loads `.env` automatically via `python-dotenv` — no other setup needed.

**Swapping models later**: every other file (`agents/*.py`,
`main.py`, `scoring/*.py`) only ever calls `get_llm()` and then uses
standard LangChain `BaseChatModel` methods — `.invoke(...)` and
`.with_structured_output(...)`. None of them know or care which
provider is behind `get_llm()`. To switch models, the only file that
needs to change is `llm_client.py`:

```python
from langchain_google_genai import ChatGoogleGenerativeAI

def get_llm():
    return ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", temperature=0.2)
```

Swapping to, say, Anthropic or OpenAI is a one-file change — install the
matching `langchain-*` package, replace the import and the constructor
call, keep `get_llm()`'s signature the same. Everything downstream
(prompts, structured-output schemas, scoring, orchestration) is
unaffected because it was written against LangChain's model interface,
not any provider-specific API.

## 5. Running

```bash
python main.py                  # researches all 25 companies (default)
python main.py --limit 5        # quick test run while iterating
```

Researching all 25 companies means 200 search calls total (8 queries per
company: Hiring, Customer Pain, Growth, and Leadership each get one
query, and Competitor Usage gets four — one per named competitor, Loop
Returns / AfterShip / Redo / Onward — for cleaner per-competitor
evidence). DuckDuckGo can still rate-limit an aggressive client, so
`tools/search_tool.py` retries with backoff and sleeps between calls. Use
`--limit` for fast iteration during development; the default researches
the full dataset since the assignment provides all 25 accounts as the
working set.

Outputs land in `outputs/`:
- `taxonomy.json` — the scoring weights (`{"Competitor Usage": 30, ...}`),
  exported from `scoring/intent_scoring.py` so they're inspectable
  without reading code.
- `raw_search_results.json` — every unique search hit (title, snippet,
  URL, `is_trusted` flag, plus the list of queries and category hints
  that surfaced it), saved before extraction/scoring even runs. Hits are
  deduplicated by URL, not by query: if two different queries return the
  same page (e.g. a Loop Returns case study page showing up for both the
  hiring query and the competitor query), it's stored once with both
  queries and categories attached, not twice. This is the ground truth:
  any signal or score can be traced back to a specific hit here.
- `signals.json` — every extracted signal for every researched company,
  each with its source URL, so any claim is traceable to real evidence.
- `ranked_accounts.csv` — company, score, categories found, reasons, plus
  `top_category`/`top_evidence`/`top_source` for the single strongest
  signal per account (e.g. `Customer Pain`, `"Reddit thread complaining
  about delayed refunds"`, `https://reddit.com/...`), so a reviewer can
  see the evidence without opening any JSON file.
- `outreach.md` — LinkedIn message + email for the top 5 scored accounts.

Verification chain: `Signal (signals.json)` → `Search Result
(raw_search_results.json)` → `URL (top_source column in
ranked_accounts.csv)`. If a reviewer asks "why did Vuori score 80?",
`ranked_accounts.csv` alone answers it — `top_evidence` and `top_source`
are right there in the row.

## 6. Example Output

`ranked_accounts.csv`:
```
company,score,max_score,categories_found,reasons,top_category,top_evidence,top_source
Rothy's,75,100,Competitor Usage; Hiring Signals; Growth Signals,"Competitor Usage: ... (+30) | Hiring Signals: ... (+20) | Growth Signals: ... (+15)",Competitor Usage,"Job posting mentions migrating off Loop Returns",https://...
```

`outreach.md` excerpt:
```
## Rothy's (score: 75/100)

**Signal referenced:** Rothy's job posting for a Returns Manager, indicating growing returns-operations complexity.

### LinkedIn Message
...

### Follow-up Email
**Subject:** ...
...
```

(Actual values depend on live search results at run time — see
`outputs/` after running the pipeline yourself.)

## 7. Limitations

- Search relies on DuckDuckGo result snippets, not full-page scraping of
  sites that block automated access (LinkedIn, G2, Trustpilot) — some
  nuance is lost versus reading a full review or job post.
- `tools/scraper.py` exists for optional enrichment but is not called on
  every hit by default, since many of the highest-value sources (careers
  pages behind JS-rendered SPAs, LinkedIn) won't yield clean text via a
  simple GET request anyway.
- `agents/research_agent.py:BLOCKED_DOMAINS` filters out known-irrelevant
  platforms (Pinterest, TikTok, Amazon, YouTube, etc.) that tend to
  surface when a company name is also a common word (e.g. "Chubbies"
  matching unrelated Pinterest boards). This is a blocklist, not an
  exhaustive filter — a random blog or unrelated shopping page not on
  the list can still get through; the extraction agent's own
  evidence-grounding instruction is the second line of defense.
- Signal extraction is LLM-based and Gemini 3.5 Flash-Lite occasionally misses a
  subtle signal or slightly over/under-states confidence — the defensive
  filter in `signal_extraction_agent.py` catches out-of-range
  `source_index` references but can't catch every judgment error.
  Spot-check `signals.json` before trusting scores fully.
- Confidence threshold for counting a category (0.5) is a reasonable
  starting point, not empirically tuned — would want real conversion
  data to calibrate it properly. The confidence values themselves are a
  model's self-reported judgment, not a statistically validated
  probability — treat them as relative ordering, not ground truth.
- A full 25-company run takes noticeably longer than a `--limit`-restricted
  one due to DuckDuckGo's rate limiting; budget time accordingly if
  re-running close to a deadline.

## 8. Future Improvements

- Job-board API integration (Greenhouse/Lever/Ashby JSON endpoints) for
  hiring signals instead of search-based detection — more reliable than
  DuckDuckGo snippets for that specific category.
- Feedback loop: track which flagged accounts convert to SDR-worked
  opportunities and use that to re-calibrate category weights over time.
- Human-in-the-loop review step for extracted signals before scoring,
  especially for borderline-confidence signals.
- Swap the confidence threshold for a per-category threshold, since some
  categories (e.g. Leadership Changes) may warrant a higher bar than
  others (e.g. Customer Pain) before counting.
