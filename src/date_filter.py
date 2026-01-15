# date_filter.py
"""Date filtering utilities for web search results."""
import re
import logging
from datetime import datetime, timedelta
from dateutil import parser

logger = logging.getLogger(__name__)


def parse_page_age(page_age_str: str) -> datetime:
    """
    Parse page_age string to datetime object.
    Handles both absolute dates and relative time expressions.
    
    Args:
        page_age_str: Date string like "April 30, 2025" or "3 weeks ago"
    
    Returns:
        datetime object or None if parsing fails
    """
    try:
        # Handle relative time expressions like "3 weeks ago", "2 days ago"
        if 'ago' in page_age_str.lower():
            now = datetime.now()
            match = re.search(r'(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago', page_age_str.lower())
            if match:
                amount = int(match.group(1))
                unit = match.group(2)
                
                time_deltas = {
                    'second': timedelta(seconds=amount),
                    'minute': timedelta(minutes=amount),
                    'hour': timedelta(hours=amount),
                    'day': timedelta(days=amount),
                    'week': timedelta(weeks=amount),
                    'month': timedelta(days=amount * 30),
                    'year': timedelta(days=amount * 365)
                }
                return now - time_deltas.get(unit, timedelta(0))
        
        # Try parsing as absolute date
        return parser.parse(page_age_str)
    except Exception as e:
        logger.warning(f"Failed to parse page_age '{page_age_str}': {e}")
        return None


def is_within_last_month(page_date: datetime) -> bool:
    """Check if a date is within the last month (30 days)."""
    if page_date is None:
        return False
    return page_date >= datetime.now() - timedelta(days=30)


def filter_search_results(response) -> tuple[set, dict, list]:
    """
    Filter web search results to only include recent pages (within last month).
    
    Args:
        response: The API response from Claude
    
    Returns:
        Tuple of (valid_urls set, statistics dict, all_results list with dates)
    """
    valid_urls = set()
    stats = {"total": 0, "filtered": 0, "kept": 0, "no_date": 0}
    all_results = []
    
    for block in response.content:
        if block.type == "web_search_tool_result":
            for result in block.content:
                if result.type == "web_search_result":
                    stats["total"] += 1
                    
                    url = result.url if hasattr(result, 'url') else 'unknown'
                    title = result.title if hasattr(result, 'title') else 'No title'
                    page_age = result.page_age if hasattr(result, 'page_age') else None
                    
                    if not page_age:
                        stats["no_date"] += 1
                        all_results.append({
                            'url': url, 'title': title, 'page_age': 'No date',
                            'kept': False, 'reason': 'No date'
                        })
                        continue
                    
                    page_date = parse_page_age(page_age)
                    if is_within_last_month(page_date):
                        valid_urls.add(url)
                        stats["kept"] += 1
                        all_results.append({
                            'url': url, 'title': title, 'page_age': page_age,
                            'kept': True, 'reason': 'Recent (within 30 days)'
                        })
                    else:
                        stats["filtered"] += 1
                        all_results.append({
                            'url': url, 'title': title, 'page_age': page_age,
                            'kept': False, 'reason': 'Too old (>30 days)'
                        })
    
    return valid_urls, stats, all_results


def log_filtering_report(stats: dict, all_results: list):
    """Log detailed filtering report."""
    percentage_kept = (stats['kept'] / stats['total'] * 100) if stats['total'] > 0 else 0
    
    logger.info("=" * 80)
    logger.info("SEARCH RESULTS FILTERING REPORT")
    logger.info("=" * 80)
    logger.info(
        f"Total results: {stats['total']} | "
        f"Kept: {stats['kept']} ({percentage_kept:.1f}%) | "
        f"Filtered (old): {stats['filtered']} | "
        f"No date: {stats['no_date']}"
    )
    logger.info("-" * 80)
    
    for i, result in enumerate(all_results, 1):
        status = "✓ KEPT" if result['kept'] else "✗ FILTERED"
        logger.info(f"{i}. [{status}] {result['page_age']}")
        logger.info(f"   Title: {result['title']}")
        logger.info(f"   URL: {result['url']}")
        logger.info(f"   Reason: {result['reason']}")
        logger.info("-" * 80)
    
    logger.info("=" * 80)


def extract_filtered_text(response, valid_urls: set) -> str:
    """
    Extract text content, keeping only blocks with valid citations or no citations.
    
    Args:
        response: The API response from Claude
        valid_urls: Set of URLs from recent search results
    
    Returns:
        Filtered text content
    """
    text_content = ""
    search_completed = False
    
    for content_block in response.content:
        if content_block.type == 'server_tool_use':
            search_completed = True
        elif content_block.type == 'text' and search_completed:
            if hasattr(content_block, 'citations') and content_block.citations:
                # Validate all citations are from recent sources
                all_valid = all(
                    citation.url in valid_urls 
                    for citation in content_block.citations
                    if hasattr(citation, 'url')
                )
                if all_valid:
                    text_content += content_block.text
            elif hasattr(content_block, 'text'):
                # No citations - include general text
                text_content += content_block.text
    
    return text_content
