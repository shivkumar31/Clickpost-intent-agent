# ClickPost Intent Capture & Outbound Activation Agent


The system researches D2C ecommerce brands using public web search, extracts buying-intent signals with Gemini 3.5 Flash-Lite, ranks accounts using deterministic scoring, and generates personalized LinkedIn messages and follow-up emails for the highest-intent accounts.

## Features

- Researches companies using targeted web searches
- Extracts structured buying-intent signals with Gemini
- Scores accounts using deterministic business rules
- Ranks companies based on buying intent
- Generates personalized outreach for the top-ranked accounts

## Tech Stack

- Python
- Gemini 3.5 Flash-Lite
- LangChain
- DuckDuckGo Search
- Pydantic

## Setup

```bash

python -m venv venv

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file:

```text
GOOGLE_API_KEY=your_api_key
```

## Run

Research all 25 companies:

```bash
python main.py
```

Run a quick test:

```bash
python main.py --limit 5
```

## Output

The generated files are saved in the `outputs/` folder:

- `taxonomy.json` – Scoring taxonomy
- `raw_search_results.json` – Collected search results
- `signals.json` – Extracted buying-intent signals
- `ranked_accounts.csv` – Ranked accounts with scores
- `outreach.md` – Personalized LinkedIn messages and follow-up emails

## Notes

- A valid Gemini API key (`GOOGLE_API_KEY`) is required.
