import time
from ddgs import DDGS
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=20))
def search(query: str, max_results: int = 4) -> list:
    with DDGS() as ddgs:
        raw_results = list(ddgs.text(query, max_results=max_results))

    results = []
    for r in raw_results:
        results.append({
            "title": r.get("title", ""),
            "url": r.get("href", ""),
            "snippet": r.get("body", ""),
        })

    time.sleep(1.5)
    return results
