import sys
import os
import re
from urllib.parse import urlparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.search_tool import search
from models.schemas import SearchHit

SIGNAL_QUERIES = {
    "Hiring Signals": '"{company}" hiring logistics returns',
    "Customer Pain": '"{company}" shipping complaints',
    "Competitor Usage (Loop Returns)": '"{company}" "Loop Returns"',
    "Competitor Usage (AfterShip)": '"{company}" "AfterShip"',
    "Competitor Usage (Redo)": '"{company}" "Redo"',
    "Competitor Usage (Onward)": '"{company}" "Onward"',
    "Growth Signals": '"{company}" funding expansion',
    "Leadership Changes": '"{company}" CTO customer experience',
}

CATEGORY_HINT_ALIASES = {
    "Competitor Usage (Loop Returns)": "Competitor Usage",
    "Competitor Usage (AfterShip)": "Competitor Usage",
    "Competitor Usage (Redo)": "Competitor Usage",
    "Competitor Usage (Onward)": "Competitor Usage",
}

BLOCKED_DOMAINS = {
    "in.pinterest.com",
    "tiktok.com",
    "amazon.com",
    "youtube.com",
    "instagram.com",
    "facebook.com",
    "etsy.com",
    "ebay.com",
}

TRUSTED_DOMAINS_BY_CATEGORY = {
    "Hiring Signals": {"linkedin.com", "greenhouse.com"},
    "Customer Pain": {"reddit.com", "trustpilot.com"},
    "Competitor Usage": {"loopreturns.com", "aftership.com", "redo.com", "onward-logistics.com"},
    "Growth Signals": {"techcrunch.com", "crunchbase.com", "pitchbook.com"},
    "Leadership Changes": {"linkedin.com", "techcrunch.com"},
}

MAX_KEPT_PER_QUERY = 4


def domain_of(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
    except Exception:
        return ""
    return netloc[4:] if netloc.startswith("www.") else netloc


def is_blocked(url: str) -> bool:
    domain = domain_of(url)
    return any(domain == d or domain.endswith("." + d) for d in BLOCKED_DOMAINS)


def company_slug(company: str) -> str:
    return re.sub(r"[^a-z0-9]", "", company.lower())


def is_trusted(url: str, company: str, category: str) -> bool:
    domain = domain_of(url)
    category_domains = TRUSTED_DOMAINS_BY_CATEGORY.get(category, set())
    if any(domain == d or domain.endswith("." + d) for d in category_domains):
        return True
    slug = company_slug(company)
    if len(slug) >= 3 and slug in domain.replace(".", ""):
        return True
    return False


def research_company(company: str, max_results_per_query: int = 8) -> list:
    by_url = {}
    blocked_count = 0
    capped_count = 0

    for query_key, template in SIGNAL_QUERIES.items():
        category = CATEGORY_HINT_ALIASES.get(query_key, query_key)

        query = template.format(company=company)
        print(f"    searching: {query}")
        try:
            results = search(query, max_results=max_results_per_query)
        except Exception as e:
            print(f"    ! search failed for '{query}': {e}")
            results = []

        not_blocked = []
        for r in results:
            if is_blocked(r["url"]):
                blocked_count += 1
                continue
            not_blocked.append(r)
        not_blocked.sort(key=lambda r: not is_trusted(r["url"], company, category))

        kept = not_blocked[:MAX_KEPT_PER_QUERY]
        capped_count += len(not_blocked) - len(kept)

        for r in kept:
            url = r["url"]
            trusted_here = is_trusted(url, company, category)
            if url not in by_url:
                by_url[url] = SearchHit(
                    title=r["title"],
                    url=url,
                    snippet=r["snippet"],
                    queries=[],
                    category_hints=[],
                    is_trusted=trusted_here,
                )
            existing = by_url[url]
            existing.is_trusted = existing.is_trusted or trusted_here
            if query not in existing.queries:
                existing.queries.append(query)
            if category not in existing.category_hints:
                existing.category_hints.append(category)

    raw_count = sum(len(h.queries) for h in by_url.values()) + blocked_count + capped_count
    trusted_count = sum(1 for h in by_url.values() if h.is_trusted)
    print(f"    {raw_count} raw hits collected, {blocked_count} dropped (blocked domain), "
          f"{capped_count} dropped (beyond top {MAX_KEPT_PER_QUERY}/query), "
          f"{len(by_url)} unique URLs kept ({trusted_count} from trusted domains)")

    return list(by_url.values())
