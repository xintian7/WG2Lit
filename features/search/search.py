import json
import re
from contextlib import nullcontext
from typing import Any
from xml.etree import ElementTree as ET

import pandas as pd
import streamlit as st

from core.constants import OPENALEX_PAGE_SIZE, MAX_WORK_TYPES
from services.openalex_client import (
    extract_status_code,
    fetch_page,
    fetch_results_with_count,
)
from services.reliefweb_client import (
    extract_status_code as extract_reliefweb_status_code,
    fetch_results_with_count as fetch_reliefweb_results_with_count,
)
from services.un_digital_library_client import (
    MARC_NS,
    extract_status_code as extract_un_digital_library_status_code,
    fetch_results_with_count as fetch_un_digital_library_results_with_count,
)
from services.world_bank_client import (
    extract_status_code as extract_world_bank_status_code,
    fetch_results_with_count as fetch_world_bank_results_with_count,
)


def _first_non_empty(values: list[Any]) -> str:
    """Return the first non-empty string value."""
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _join_non_empty(values: list[Any], separator: str = "; ") -> str:
    """Join non-empty values using the given separator."""
    cleaned = [str(v).strip() for v in values if str(v or "").strip()]
    return separator.join(cleaned)


def _safe_reliefweb_list(raw_value: Any) -> list[dict[str, Any]]:
    """Normalize ReliefWeb list-like fields to a list of dict objects."""
    if isinstance(raw_value, list):
        return [item for item in raw_value if isinstance(item, dict)]
    if isinstance(raw_value, dict):
        return [raw_value]
    return []


def _reliefweb_first_paragraph(raw_body: Any) -> str:
    """Extract the first paragraph from ReliefWeb body text/HTML."""
    text = str(raw_body or "").strip()
    if not text:
        return ""

    # Convert common HTML paragraph breaks to newlines before stripping tags.
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    paragraphs = [
        re.sub(r"\s+", " ", paragraph).strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]
    if paragraphs:
        return paragraphs[0]

    # Fallback when no explicit paragraph break exists.
    return re.sub(r"\s+", " ", text).strip()


def _normalize_reliefweb_records(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize ReliefWeb records into the app's tabular export schema."""
    normalized: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        fields = item.get("fields") if isinstance(item.get("fields"), dict) else {}

        title = _first_non_empty([
            fields.get("title"),
            (fields.get("headline") or {}).get("title") if isinstance(fields.get("headline"), dict) else None,
        ])
        headline_summary = (
            (fields.get("headline") or {}).get("summary")
            if isinstance(fields.get("headline"), dict)
            else None
        )
        body_first_paragraph = _reliefweb_first_paragraph(
            _first_non_empty([
                fields.get("body"),
                fields.get("body-html"),
                fields.get("body_html"),
            ])
        )
        abstract = _first_non_empty([
            headline_summary,
            body_first_paragraph,
        ])

        source_names = [entry.get("name") for entry in _safe_reliefweb_list(fields.get("source"))]
        language_names = [entry.get("name") for entry in _safe_reliefweb_list(fields.get("language"))]
        format_names = [entry.get("name") for entry in _safe_reliefweb_list(fields.get("format"))]
        theme_names = [entry.get("name") for entry in _safe_reliefweb_list(fields.get("theme"))]

        raw_publication_date = fields.get("date")
        if isinstance(raw_publication_date, dict):
            publication_date = _first_non_empty([
                raw_publication_date.get("original"),
                raw_publication_date.get("created"),
                raw_publication_date.get("changed"),
            ])
        else:
            publication_date = str(raw_publication_date or "").strip()
        if "T" in publication_date:
            publication_date = publication_date.split("T", maxsplit=1)[0]
        publication_year = ""
        if publication_date:
            publication_year = publication_date[:4]

        url = _first_non_empty([
            fields.get("url"),
            fields.get("url_alias"),
        ])

        normalized.append({
            "Source": "ReliefWeb",
            "OpenAlex": f'<a href="{url}" target="_blank">View</a>' if url else "",
            "OpenAlex URL": url,
            "Title": title,
            "Publication Date": publication_date,
            "Publication Year": publication_year,
            "Journal": _join_non_empty(source_names),
            "Type": _join_non_empty(format_names),
            "Authors": "",
            "Open Access": "",
            "OA Status": "",
            "Citations": "",
            "DOI": "",
            "Relevance Score": "",
            "Keywords": _join_non_empty(theme_names),
            "Topics": _join_non_empty(theme_names),
            "Abstract": abstract,
            "Publisher": _join_non_empty(source_names),
            "URL": url,
            "Language": _join_non_empty(language_names),
        })

    return normalized


def _marc_subfield_values(record: ET.Element, tag: str, code: str) -> list[str]:
    """Extract MARCXML subfield values for one datafield tag/code pair."""
    values: list[str] = []
    for datafield in record.findall(f"{{{MARC_NS}}}datafield[@tag='{tag}']"):
        for subfield in datafield.findall(f"{{{MARC_NS}}}subfield[@code='{code}']"):
            text = str(subfield.text or "").strip()
            if text:
                values.append(text)
    return values


def _marc_controlfield_value(record: ET.Element, tag: str) -> str:
    """Extract one MARCXML controlfield value by tag."""
    field = record.find(f"{{{MARC_NS}}}controlfield[@tag='{tag}']")
    if field is None:
        return ""
    return str(field.text or "").strip()


def _extract_un_year(record: ET.Element) -> str:
    """Extract publication year from MARC fields when available."""
    year_candidates: list[str] = []
    for tag, code in (("269", "a"), ("269", "c"), ("260", "c"), ("264", "c")):
        year_candidates.extend(_marc_subfield_values(record, tag, code))

    for candidate in year_candidates:
        match = re.search(r"(19|20)\d{2}", candidate)
        if match:
            return match.group(0)
    return ""


def _extract_un_record_url(record: ET.Element) -> str:
    """Prefer the UN Digital Library record page URL over file attachment URLs."""
    record_id = _marc_controlfield_value(record, "001")
    if record_id.isdigit():
        return f"https://digitallibrary.un.org/record/{record_id}"
    return _first_non_empty(_marc_subfield_values(record, "856", "u"))


def _normalize_un_digital_library_records(records: list[ET.Element]) -> list[dict[str, Any]]:
    """Normalize UN Digital Library MARC records to the app's export schema."""
    normalized: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, ET.Element):
            continue

        title = _join_non_empty(
            _marc_subfield_values(record, "245", "a") + _marc_subfield_values(record, "245", "b"),
            separator=" ",
        )
        source = _first_non_empty(
            _marc_subfield_values(record, "773", "t") + _marc_subfield_values(record, "490", "a")
        )
        authors = _join_non_empty(
            _marc_subfield_values(record, "100", "a")
            + _marc_subfield_values(record, "110", "a")
            + _marc_subfield_values(record, "700", "a")
            + _marc_subfield_values(record, "710", "a"),
            separator=", ",
        )
        abstract = _join_non_empty(_marc_subfield_values(record, "520", "a"), separator=" ")
        topics = _join_non_empty(_marc_subfield_values(record, "650", "a"))
        url = _extract_un_record_url(record)
        doi = _first_non_empty(_marc_subfield_values(record, "024", "a"))

        publication_year = _extract_un_year(record)

        normalized.append({
            "Source": "UN Digital Library",
            "OpenAlex": f'<a href="{url}" target="_blank">View</a>' if url else "",
            "OpenAlex URL": url,
            "Title": title,
            "Publication Date": publication_year,
            "Publication Year": publication_year,
            "Journal": source,
            "Type": "UN Document",
            "Authors": authors,
            "Open Access": "",
            "OA Status": "",
            "Citations": "",
            "DOI": doi,
            "Relevance Score": "",
            "Keywords": topics,
            "Topics": topics,
            "Abstract": abstract,
            "Publisher": "United Nations",
            "URL": url,
            "Language": "",
        })

    return normalized


def _world_bank_authors(raw_authors: Any) -> str:
    """Extract author names from World Bank author mapping objects."""
    if not isinstance(raw_authors, dict):
        return ""

    authors: list[str] = []
    for item in raw_authors.values():
        if not isinstance(item, dict):
            continue
        author_name = str(item.get("author") or "").strip()
        if author_name:
            authors.append(author_name)
    return _join_non_empty(authors, separator=", ")


def _world_bank_abstract(raw_abstracts: Any) -> str:
    """Extract a readable abstract string from World Bank abstract payloads."""
    if isinstance(raw_abstracts, dict):
        text = str(raw_abstracts.get("cdata!") or "").strip()
    else:
        text = str(raw_abstracts or "").strip()
    return re.sub(r"\s+", " ", text)


def _normalize_world_bank_records(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize World Bank documents to the app's tabular export schema."""
    normalized: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue

        title = _first_non_empty([
            item.get("display_title"),
            item.get("title"),
        ])
        publication_date = str(item.get("docdt") or item.get("disclosure_date") or "").strip()
        if "T" in publication_date:
            publication_date = publication_date.split("T", maxsplit=1)[0]
        publication_year = publication_date[:4] if publication_date else ""
        url = _first_non_empty([
            item.get("url"),
            item.get("pdfurl"),
            item.get("txturl"),
        ])
        theme_names = [part.strip() for part in str(item.get("theme") or "").split(",") if part.strip()]

        normalized.append({
            "Source": "World Bank",
            "OpenAlex": f'<a href="{url}" target="_blank">View</a>' if url else "",
            "OpenAlex URL": url,
            "Title": title,
            "Publication Date": publication_date,
            "Publication Year": publication_year,
            "Journal": _first_non_empty([item.get("majdocty"), item.get("count")]),
            "Type": str(item.get("docty") or "").strip(),
            "Authors": _world_bank_authors(item.get("authors")),
            "Open Access": "",
            "OA Status": "",
            "Citations": "",
            "DOI": "",
            "Relevance Score": "",
            "Keywords": _join_non_empty(theme_names),
            "Topics": _join_non_empty(theme_names),
            "Abstract": _world_bank_abstract(item.get("abstracts")),
            "Publisher": "World Bank",
            "URL": url,
            "Language": str(item.get("lang") or "").strip(),
        })

    return normalized


def _build_normalized_record_text_blob(record: dict[str, Any]) -> str:
    """Build a lowercase text blob from normalized record fields."""
    fields = [
        record.get("Title"),
        record.get("Abstract"),
        record.get("Keywords"),
        record.get("Topics"),
        record.get("Journal"),
        record.get("Publisher"),
    ]
    return " ".join(str(value or "") for value in fields).lower()


def _normalized_record_matches_local_filters(
    record: dict[str, Any],
    *,
    keyword_expr: str,
    year_range: tuple[int, int],
) -> bool:
    """Apply local post-filters to normalized (non-OpenAlex) records."""
    if not _normalized_record_matches_year_range(record, year_range=year_range):
        return False

    provider = str(record.get("Source") or "").strip().lower()
    if provider == "un digital library":
        return True

    return _normalized_record_matches_keyword_expr(record, keyword_expr=keyword_expr)


def _normalized_record_matches_year_range(
    record: dict[str, Any],
    *,
    year_range: tuple[int, int],
) -> bool:
    """Apply the local year-range guard to normalized records."""
    start_year, end_year = year_range

    pub_year = str(record.get("Publication Year") or "").strip()
    if pub_year.isdigit():
        year_value = int(pub_year)
        if year_value < start_year or year_value > end_year:
            return False

    return True


def _normalized_record_matches_keyword_expr(
    record: dict[str, Any],
    *,
    keyword_expr: str,
) -> bool:
    """Evaluate the local boolean keyword expression against normalized record text."""

    blob = _build_normalized_record_text_blob(record)
    tokens = _tokenize_boolean_query(keyword_expr)
    if not tokens:
        return True

    try:
        expression_tokens = _insert_implicit_and(tokens)
        rpn = _to_rpn(expression_tokens)
        stack: list[bool] = []
        for token in rpn:
            if token in ("AND", "OR"):
                if len(stack) < 2:
                    return False
                right = stack.pop()
                left = stack.pop()
                stack.append(left and right if token == "AND" else left or right)
            else:
                stack.append(token in blob)
        return len(stack) == 1 and bool(stack[0])
    except ValueError:
        literals = _extract_literals(tokens)
        if not literals:
            return True
        return all(literal.lower() in blob for literal in literals)


def _build_reliefweb_query_value(keyword_expr: str) -> str:
    """Translate app boolean input into ReliefWeb query syntax."""
    raw_query = str(keyword_expr or "").strip()
    if not raw_query:
        return ""

    tokens = _tokenize_boolean_query(raw_query)
    if not tokens:
        return raw_query

    translated: list[str] = []

    def is_operand(token: str) -> bool:
        upper = token.upper()
        return token not in ("(", ")") and upper not in ("AND", "OR")

    for index, token in enumerate(tokens):
        upper = token.upper()
        normalized_token = upper if upper in ("AND", "OR") else token

        if index > 0:
            previous = translated[-1]
            if (is_operand(previous) or previous == ")") and (is_operand(normalized_token) or normalized_token == "("):
                translated.append("AND")

        translated.append(normalized_token)

    return " ".join(translated)


def _normalized_record_date_sort_key(record: dict[str, Any]) -> tuple[int, str]:
    """Build a descending-friendly sort key from normalized publication date text."""
    publication_date = str(record.get("Publication Date") or "").strip()
    publication_year = str(record.get("Publication Year") or "").strip()
    normalized = publication_date or publication_year
    digits_only = "".join(ch for ch in normalized if ch.isdigit())
    numeric_key = int(digits_only[:8]) if digits_only else 0
    return numeric_key, normalized


def _openalex_matches_local_filters(
    work: dict[str, Any],
    *,
    keyword_expr: str,
    year_range: tuple[int, int],
    work_types: list[str] | None,
    language: str | None,
    is_global_south: bool,
    institution_country_code: str | None,
    use_semantic_search: bool,
) -> bool:
    """Apply a local post-filter pass after OpenAlex API results are fetched."""
    start_year, end_year = year_range

    publication_year = work.get("publication_year")
    if isinstance(publication_year, int):
        if publication_year < start_year or publication_year > end_year:
            return False

    if work_types:
        work_type = str(work.get("type") or "")
        if work_type and work_type not in work_types:
            return False

    if language:
        work_language = str(work.get("language") or "")
        if work_language and work_language != language:
            return False

    if institution_country_code or is_global_south:
        has_matching_country = False
        has_global_south = False
        authorships = work.get("authorships") or []
        if isinstance(authorships, list):
            for authorship in authorships:
                institutions = (authorship or {}).get("institutions") or []
                if not isinstance(institutions, list):
                    continue
                for institution in institutions:
                    if not isinstance(institution, dict):
                        continue
                    if institution_country_code and institution.get("country_code") == institution_country_code:
                        has_matching_country = True
                    if is_global_south and bool(institution.get("is_global_south")):
                        has_global_south = True
        if institution_country_code and not has_matching_country:
            return False
        if is_global_south and not has_global_south:
            return False

    # Semantic search is intentionally broader; rely on API semantics for keyword matching.
    if use_semantic_search:
        return True

    tokens = _tokenize_boolean_query(keyword_expr)
    if not tokens:
        return True

    try:
        expression_tokens = _insert_implicit_and(tokens)
        rpn = _to_rpn(expression_tokens)
        return _evaluate_rpn_expression(work, rpn)
    except ValueError:
        literals = _extract_literals(tokens)
        if not literals:
            return True
        return _matches_all_keywords(work, literals)


def perform_non_openalex_search(
    keyword: str,
    year_range: tuple[int, int],
    num_results: int,
    *,
    sources: list[str],
    container: Any = None,
    status_callback=None,
    emit_ui: bool = True,
) -> dict[str, Any] | None:
    """Search non-OpenAlex sources and return a combined payload."""
    display = container if container is not None else st

    if not keyword or not keyword.strip():
        st.warning("Please enter a keyword for the search.")
        return None
    if not year_range or len(year_range) != 2:
        st.warning("Please select a valid publication year range.")
        return None

    normalized_sources = {str(source).strip().lower() for source in (sources or []) if str(source).strip()}
    selected_non_openalex_sources = [
        source for source in normalized_sources if source in {"reliefweb", "un digital library", "world bank"}
    ]
    if not selected_non_openalex_sources:
        return None

    start_year, end_year = year_range
    requested_n = max(int(num_results), 1)
    reliefweb_query = _build_reliefweb_query_value(keyword)

    combined_records: list[dict[str, Any]] = []
    source_totals: dict[str, int] = {}

    spinner_context = st.spinner("Searching selected non-OpenAlex sources...") if emit_ui else nullcontext()
    with spinner_context:
        if "reliefweb" in selected_non_openalex_sources:
            try:
                if callable(status_callback):
                    status_callback("Searching ReliefWeb...")
                reliefweb_results, reliefweb_total = fetch_reliefweb_results_with_count(
                    search=reliefweb_query,
                    from_year=start_year,
                    to_year=end_year,
                    limit=requested_n,
                    page_size=min(200, requested_n),
                    timeout=30,
                )
                reliefweb_records = _normalize_reliefweb_records(reliefweb_results)
                source_totals["ReliefWeb"] = int(reliefweb_total)
                combined_records.extend(reliefweb_records)
                if callable(status_callback):
                    status_callback(f"Finished searching ReliefWeb. Fetched {len(reliefweb_records)} ReliefWeb records.")
            except Exception as exc:
                if callable(status_callback):
                    status_callback(f"ReliefWeb search failed: {exc}")
                status = extract_reliefweb_status_code(exc)
                if status:
                    display.warning(f"ReliefWeb search failed with HTTP {status}.")
                else:
                    display.warning(f"ReliefWeb search failed: {exc}")

        if "un digital library" in selected_non_openalex_sources:
            try:
                if callable(status_callback):
                    status_callback("Searching UN Digital Library...")
                un_results, un_total = fetch_un_digital_library_results_with_count(
                    search=keyword.strip(),
                    from_year=start_year,
                    to_year=end_year,
                    limit=requested_n,
                    page_size=min(200, requested_n),
                    timeout=30,
                )
                un_records = _normalize_un_digital_library_records(un_results)
                source_totals["UN Digital Library"] = int(un_total)
                combined_records.extend(un_records)
                if callable(status_callback):
                    status_callback(f"Finished searching UN Digital Library. Fetched {len(un_records)} UN Digital Library records.")
            except Exception as exc:
                if callable(status_callback):
                    status_callback(f"UN Digital Library search failed: {exc}")
                status = extract_un_digital_library_status_code(exc)
                if status:
                    display.warning(f"UN Digital Library search failed with HTTP {status}.")
                else:
                    display.warning(f"UN Digital Library search failed: {exc}")

        if "world bank" in selected_non_openalex_sources:
            try:
                if callable(status_callback):
                    status_callback("Searching World Bank...")
                world_bank_results, world_bank_total = fetch_world_bank_results_with_count(
                    search=keyword.strip(),
                    limit=requested_n,
                    page_size=min(200, requested_n),
                    timeout=30,
                )
                world_bank_records = _normalize_world_bank_records(world_bank_results)
                source_totals["World Bank"] = int(world_bank_total)
                combined_records.extend(world_bank_records)
                if callable(status_callback):
                    status_callback(f"Finished searching World Bank. Fetched {len(world_bank_records)} World Bank records.")
            except Exception as exc:
                if callable(status_callback):
                    status_callback(f"World Bank search failed: {exc}")
                status = extract_world_bank_status_code(exc)
                if status:
                    display.warning(f"World Bank search failed with HTTP {status}.")
                else:
                    display.warning(f"World Bank search failed: {exc}")

    if not combined_records:
        display.warning("No results were returned from the selected non-OpenAlex source(s).")
        return None

    api_returned_count = len(combined_records)
    filtered_records = [
        record
        for record in combined_records
        if (
            str(record.get("Source") or "").strip() == "ReliefWeb"
            or _normalized_record_matches_local_filters(
                record,
                keyword_expr=keyword.strip(),
                year_range=year_range,
            )
        )
    ]

    if not filtered_records:
        display.warning("Results were found from non-OpenAlex sources, but none remained after local post-filtering.")
        return None

    filtered_records = sorted(
        filtered_records,
        key=_normalized_record_date_sort_key,
        reverse=True,
    )

    df = pd.DataFrame(filtered_records)
    csv = df.to_csv(index=False).encode("utf-8")
    json_full = json.dumps(
        df.to_dict(orient="records"),
        indent=2,
        ensure_ascii=False,
    ).encode("utf-8")

    summary_parts: list[str] = []
    if "ReliefWeb" in source_totals:
        summary_parts.append(f"ReliefWeb reports {source_totals['ReliefWeb']} matches")
    if "UN Digital Library" in source_totals:
        summary_parts.append(f"UN Digital Library returned {source_totals['UN Digital Library']} records")
    if "World Bank" in source_totals:
        summary_parts.append(f"World Bank returned {source_totals['World Bank']} records")
    selected_source_labels = list(source_totals.keys())
    if len(selected_source_labels) == 1:
        fetched_summary = f"API fetched {api_returned_count} {selected_source_labels[0]} records"
        filtered_summary = f"local post-filter retained {len(df)} {selected_source_labels[0]} records"
    else:
        fetched_summary = f"API fetched {api_returned_count} records from selected non-OpenAlex sources"
        filtered_summary = f"local post-filter retained {len(df)} records"
    summary_text = (
        ". ".join(summary_parts)
        + f". {fetched_summary}; {filtered_summary}."
    )

    return {
        "csv": csv,
        "json": json_full,
        "total": len(df),
        "shown": len(df),
        "summary": summary_text,
        "summary_lines": summary_parts,
        "api_returned_count": api_returned_count,
        "source_totals": source_totals,
    }


def get_work_topics(work: dict[str, Any]) -> str:
    """Extract topic display names from an OpenAlex work.

    Uses both `primary_topic` and `topics` (if present), de-duplicated in order.
    """
    names = []

    primary_topic = work.get("primary_topic") or {}
    if isinstance(primary_topic, dict):
        primary_name = primary_topic.get("display_name")
        if primary_name:
            names.append(primary_name)

    topics = work.get("topics") or []
    if isinstance(topics, list):
        for t in topics:
            if not isinstance(t, dict):
                continue
            t_name = t.get("display_name")
            if t_name:
                names.append(t_name)

    # de-duplicate while preserving order
    deduped = []
    seen = set()
    for n in names:
        if n in seen:
            continue
        seen.add(n)
        deduped.append(n)

    return "; ".join(deduped)


def _build_work_text_blob(work: dict[str, Any]) -> str:
    """Build a lowercase text blob from key searchable fields."""
    title = str(work.get("title") or "")

    # Reconstruct abstract text from OpenAlex inverted index.
    abstract_text = ""
    inverted = work.get("abstract_inverted_index")
    if isinstance(inverted, dict) and inverted:
        try:
            max_pos = max((max(pos) for pos in inverted.values() if pos), default=-1)
            if max_pos >= 0:
                tokens = [""] * (max_pos + 1)
                for word, positions in inverted.items():
                    if not isinstance(positions, list):
                        continue
                    for p in positions:
                        if isinstance(p, int) and 0 <= p < len(tokens):
                            tokens[p] = str(word)
                abstract_text = " ".join(tok for tok in tokens if tok)
        except Exception:
            abstract_text = ""

    keywords_text = " ".join(
        str(k.get("display_name") or "")
        for k in (work.get("keywords") or [])
        if isinstance(k, dict)
    )

    topics_text = " ".join(
        str(t.get("display_name") or "")
        for t in (work.get("topics") or [])
        if isinstance(t, dict)
    )

    return " ".join([title, abstract_text, keywords_text, topics_text]).lower()


def _matches_all_keywords(work: dict[str, Any], keywords_list: list[str]) -> bool:
    """Return True only if all keyword phrases are present (AND semantics)."""
    blob = _build_work_text_blob(work)
    return all(kw.lower() in blob for kw in keywords_list)


def _tokenize_boolean_query(query: str) -> list[str]:
    """Tokenize a boolean expression supporting quotes, AND/OR, and parentheses."""
    pattern = r'"[^"\\]*(?:\\.[^"\\]*)*"|\(|\)|,|;|\bAND\b|\bOR\b|[^\s(),;]+'
    return [t for t in re.findall(pattern, query, flags=re.IGNORECASE) if t.strip()]


def _normalize_term(token: str) -> str:
    token = token.strip()
    if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
        return token[1:-1].strip().lower()
    return token.lower()


def _insert_implicit_and(tokens: list[str]) -> list[str]:
    """Insert implicit AND between adjacent operands/parentheses."""
    if not tokens:
        return tokens

    out: list[str] = []

    def _is_operand(tok: str) -> bool:
        upper = tok.upper()
        return tok not in ("(", ")") and upper not in ("AND", "OR")

    for i, tok in enumerate(tokens):
        if i > 0:
            prev = tokens[i - 1]
            if (
                (_is_operand(prev) or prev == ")")
                and (_is_operand(tok) or tok == "(")
            ):
                out.append("AND")
        out.append(tok)

    return out


def _to_rpn(tokens: list[str]) -> list[str]:
    """Convert infix boolean tokens to RPN using shunting-yard."""
    precedence = {"OR": 1, "AND": 2}
    output: list[str] = []
    operators: list[str] = []

    for tok in tokens:
        upper = tok.upper()
        if tok == "(":
            operators.append(tok)
        elif tok == ")":
            while operators and operators[-1] != "(":
                output.append(operators.pop())
            if not operators or operators[-1] != "(":
                raise ValueError("Mismatched parentheses in keyword expression.")
            operators.pop()
        elif upper in ("AND", "OR"):
            while (
                operators
                and operators[-1] in precedence
                and precedence[operators[-1]] >= precedence[upper]
            ):
                output.append(operators.pop())
            operators.append(upper)
        else:
            output.append(_normalize_term(tok))

    while operators:
        op = operators.pop()
        if op in ("(", ")"):
            raise ValueError("Mismatched parentheses in keyword expression.")
        output.append(op)

    return output


def _extract_literals(tokens: list[str]) -> list[str]:
    literals: list[str] = []
    seen: set[str] = set()
    for tok in tokens:
        upper = tok.upper()
        if tok in ("(", ")") or upper in ("AND", "OR"):
            continue
        lit = _normalize_term(tok)
        if not lit or lit in seen:
            continue
        seen.add(lit)
        literals.append(lit)
    return literals


def _evaluate_rpn_expression(work: dict[str, Any], rpn: list[str]) -> bool:
    """Evaluate parsed boolean expression against a work text blob."""
    blob = _build_work_text_blob(work)
    stack: list[bool] = []

    for tok in rpn:
        if tok in ("AND", "OR"):
            if len(stack) < 2:
                raise ValueError("Invalid keyword expression.")
            right = stack.pop()
            left = stack.pop()
            stack.append(left and right if tok == "AND" else left or right)
        else:
            stack.append(tok in blob)

    if len(stack) != 1:
        raise ValueError("Invalid keyword expression.")
    return stack[0]


def normalize_keyword_query(query: str) -> tuple[str, bool, str]:
    """Normalize a keyword query for boolean search.

    Returns a tuple of (corrected_query, needs_review, explanation).
    """
    raw_query = (query or "").strip()
    if not raw_query:
        return raw_query, False, ""

    converted_plain_and = False
    if (
        '"' not in raw_query
        and not re.search(r"\b(AND|OR)\b", raw_query)
        and re.search(r"\band\b", raw_query)
    ):
        parts = re.split(r"\band\b", raw_query, maxsplit=1)
        if len(parts) == 2 and parts[0].strip() and parts[1].strip():
            raw_query = f"{parts[0].strip()} AND {parts[1].strip()}"
            converted_plain_and = True

    tokens = _tokenize_boolean_query(raw_query)
    if not tokens:
        return raw_query, False, ""

    corrected_tokens: list[str] = []
    phrase_terms: list[str] = []
    quoted_phrases: list[str] = []
    grouped_or_chain = False

    def is_boolean_operator(token: str) -> bool:
        # Treat only uppercase AND/OR as Boolean operators to avoid rewriting
        # natural-language phrases like "climate change and ...".
        return token in ("AND", "OR")

    def flush_phrase() -> None:
        nonlocal phrase_terms
        if not phrase_terms:
            return
        if len(phrase_terms) == 1:
            corrected_tokens.append(phrase_terms[0])
        else:
            phrase = " ".join(phrase_terms)
            corrected_tokens.append(f'"{phrase}"')
            quoted_phrases.append(phrase)
        phrase_terms = []

    for tok in tokens:
        if tok in (",", ";"):
            # Treat separators as delimiters between terms.
            flush_phrase()
            continue
        if tok in ("(", ")") or is_boolean_operator(tok):
            flush_phrase()
            corrected_tokens.append(tok)
            continue

        if len(tok) >= 2 and tok[0] == '"' and tok[-1] == '"':
            flush_phrase()
            corrected_tokens.append(f'"{tok[1:-1].strip()}"')
            continue

        phrase_terms.append(tok.strip())

    flush_phrase()

    final_tokens: list[str] = []
    inserted_and_count = 0

    def is_operand(token: str) -> bool:
        return token not in ("(", ")") and not is_boolean_operator(token)

    for index, token in enumerate(corrected_tokens):
        if index > 0:
            previous = corrected_tokens[index - 1]
            if (is_operand(previous) or previous == ")") and (is_operand(token) or token == "("):
                final_tokens.append("AND")
                inserted_and_count += 1
        final_tokens.append(token)

    def group_or_chain_after_and(tokens_list: list[str]) -> tuple[list[str], bool]:
        """Wrap RHS OR chains after AND: A AND B OR C -> A AND (B OR C)."""
        out: list[str] = []
        i = 0
        changed = False

        while i < len(tokens_list):
            token = tokens_list[i]
            if token != "AND":
                out.append(token)
                i += 1
                continue

            out.append("AND")
            rhs_start = i + 1
            if rhs_start >= len(tokens_list):
                i += 1
                continue
            # Already grouped.
            if tokens_list[rhs_start] == "(":
                i += 1
                continue

            rhs_end = rhs_start
            saw_or = False
            simple_chain = True
            while rhs_end < len(tokens_list):
                current = tokens_list[rhs_end]
                if current in ("(", ")"):
                    simple_chain = False
                    break
                if current == "OR":
                    saw_or = True
                if current == "AND" and rhs_end > rhs_start:
                    break
                rhs_end += 1

            segment = tokens_list[rhs_start:rhs_end]
            if simple_chain and saw_or and segment:
                out.append("(")
                out.extend(segment)
                out.append(")")
                changed = True
                i = rhs_end
                continue

            i += 1

        return out, changed

    final_tokens, grouped_or_chain = group_or_chain_after_and(final_tokens)

    corrected_query = " ".join(final_tokens).strip()
    needs_review = " ".join(raw_query.split()) != " ".join(corrected_query.split())

    if not needs_review:
        return raw_query, False, ""

    explanation_parts: list[str] = []
    if quoted_phrases:
        explanation_parts.append(
            "Wrapped these multi-word terms in double quotes: "
            + ", ".join(f'\"{phrase}\"' for phrase in quoted_phrases)
        )
    if inserted_and_count:
        explanation_parts.append("Inserted explicit AND between adjacent terms.")
    if grouped_or_chain:
        explanation_parts.append("Grouped OR terms with parentheses after AND for clearer Boolean logic.")
    if converted_plain_and:
        explanation_parts.append("Converted plain-language 'and' into Boolean AND for keyword combination.")

    if not explanation_parts:
        explanation_parts.append("Adjusted the keyword syntax to match Boolean search rules.")

    return corrected_query, True, " ".join(explanation_parts)


def perform_search(
    keyword: str,
    year_range: tuple[int, int],
    num_results: int,
    work_types: list[str] | None = None,
    language: str | None = None,
    is_global_south: bool = False,
    institution_country_code: str | None = None,
    container: Any = None,
    display_limit: int = 5,
    sort_by: str = "Relevance",
    use_semantic_search: bool = False,
    status_callback=None,
    emit_ui: bool = True,
) -> dict[str, Any] | None:
    """Perform a search against OpenAlex and render results.

    This function assumes a Search button in `app.py` calls it; it does not create its own button.
    """
    # Basic validation
    if not keyword or not keyword.strip():
        st.warning("Please enter a keyword for the search.")
        return

    if not year_range or len(year_range) != 2:
        st.warning("Please select a valid publication year range.")
        return

    start_year, end_year = year_range

    try:
        # Use provided container for rendering results to avoid extra spacing
        display = container if container is not None else st
        had_connection_issue = False
        connection_error_detail = ""
        connection_error_status: int | None = None

        # clear previous results in the container if possible
        if container is not None:
            container.empty()

        keyword_expr = keyword.strip()
        if not keyword_expr:
            st.warning("Please enter at least one keyword.")
            return

        if callable(status_callback):
            status_callback("Searching OpenAlex...")

        spinner_context = st.spinner("Searching...") if emit_ui else nullcontext()
        with spinner_context:
            # OpenAlex semantic search uses search.semantic as a query parameter, not a filter.
            # Regular search uses title_and_abstract.search as a filter.
            base_params: dict[str, Any] = {}

            if use_semantic_search:
                base_params["search.semantic"] = keyword_expr
                filter_parts = [
                    f"publication_year:{start_year}-{end_year}",
                ]
                if language:
                    filter_parts.append(f"language:{language}")
                if work_types:
                    types_to_query = work_types[:MAX_WORK_TYPES]
                    filter_parts.append(f"type:{'|'.join(types_to_query)}")
            else:
                filter_parts = [
                    f"title_and_abstract.search:{keyword_expr}",
                    f"from_publication_date:{start_year}-01-01",
                    f"to_publication_date:{end_year}-12-31",
                ]
                if language:
                    filter_parts.append(f"language:{language}")
                if institution_country_code:
                    filter_parts.append(f"institutions.country_code:{institution_country_code}")
                if is_global_south:
                    filter_parts.append("institutions.is_global_south:true")
                if work_types:
                    types_to_query = work_types[:MAX_WORK_TYPES]
                    filter_parts.append(f"type:{'|'.join(types_to_query)}")

            if filter_parts:
                base_params["filter"] = ",".join(filter_parts)

            requested_n = max(int(num_results), 1)
            openalex_total = 0
            post_filter_retained_count = 0
            post_filter_exhaustive = use_semantic_search

            # Map UI sort option to OpenAlex sort kwargs
            _sort_map = {
                "Relevance": None,
                "Citation count": {"cited_by_count": "desc"},
                "Date": {"publication_date": "desc"},
            }
            sort_kwargs = _sort_map.get(sort_by, None)

            def _apply_sort(params: dict[str, Any]) -> dict[str, Any]:
                new_params = dict(params)
                if not sort_kwargs:
                    return new_params
                sort_field, sort_dir = next(iter(sort_kwargs.items()))
                new_params["sort"] = f"{sort_field}:{sort_dir}"
                return new_params

            query_params = _apply_sort(base_params)

            page_size = min(OPENALEX_PAGE_SIZE, 100)

            def _dedupe_results(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
                seen_ids = set()
                unique_candidates: list[dict[str, Any]] = []
                for candidate in candidates:
                    rid = candidate.get("id") if isinstance(candidate, dict) else None
                    if not rid:
                        rid = (candidate.get("ids") or {}).get("openalex") if isinstance(candidate, dict) else None
                    if not rid or rid in seen_ids:
                        continue
                    seen_ids.add(rid)
                    unique_candidates.append(candidate)
                return unique_candidates

            def _fetch_regular_openalex_until_limit(params: dict[str, Any]) -> tuple[list[dict[str, Any]], int, bool]:
                page = 1
                scanned_results: list[dict[str, Any]] = []
                filtered_matches: list[dict[str, Any]] = []
                seen_ids: set[str] = set()
                total_count = 0

                while len(filtered_matches) < requested_n:
                    batch, batch_total = fetch_page(
                        params,
                        page=page,
                        page_size=page_size,
                        timeout=30,
                    )
                    if page == 1:
                        total_count = batch_total
                    if not batch:
                        return scanned_results, total_count, True

                    for candidate in batch:
                        rid = candidate.get("id") if isinstance(candidate, dict) else None
                        if not rid:
                            rid = (candidate.get("ids") or {}).get("openalex") if isinstance(candidate, dict) else None
                        if not rid or rid in seen_ids:
                            continue
                        seen_ids.add(rid)
                        scanned_results.append(candidate)
                        if _openalex_matches_local_filters(
                            candidate,
                            keyword_expr=keyword_expr,
                            year_range=year_range,
                            work_types=work_types,
                            language=language,
                            is_global_south=is_global_south,
                            institution_country_code=institution_country_code,
                            use_semantic_search=False,
                        ):
                            filtered_matches.append(candidate)
                            if len(filtered_matches) >= requested_n:
                                return scanned_results, total_count, False

                    if len(batch) < page_size:
                        return scanned_results, total_count, True

                    page += 1

            try:
                if use_semantic_search:
                    all_results, openalex_total = fetch_results_with_count(
                        query_params,
                        limit=requested_n,
                        use_semantic_search=True,
                        page_size=page_size,
                        timeout=30,
                    )
                else:
                    all_results, openalex_total, post_filter_exhaustive = _fetch_regular_openalex_until_limit(query_params)
            except Exception as exc:
                had_connection_issue = True
                connection_error_detail = str(exc)
                connection_error_status = extract_status_code(exc)
                all_results = []

                # Fallback: for plain multi-word queries, retry with quoted phrase.
                is_plain_phrase = (
                    not use_semantic_search
                    and " " in keyword_expr
                    and '"' not in keyword_expr
                    and not re.search(r"\b(AND|OR)\b", keyword_expr)
                    and "(" not in keyword_expr
                    and ")" not in keyword_expr
                )
                if is_plain_phrase:
                    fallback_filter_parts = [
                        f"title_and_abstract.search:\"{keyword_expr}\"",
                        f"from_publication_date:{start_year}-01-01",
                        f"to_publication_date:{end_year}-12-31",
                    ]
                    if language:
                        fallback_filter_parts.append(f"language:{language}")
                    if institution_country_code:
                        fallback_filter_parts.append(f"institutions.country_code:{institution_country_code}")
                    if is_global_south:
                        fallback_filter_parts.append("institutions.is_global_south:true")
                    if work_types:
                        types_to_query = work_types[:MAX_WORK_TYPES]
                        fallback_filter_parts.append(f"type:{'|'.join(types_to_query)}")

                    fallback_params = _apply_sort({"filter": ",".join(fallback_filter_parts)})
                    try:
                        all_results, openalex_total, post_filter_exhaustive = _fetch_regular_openalex_until_limit(fallback_params)
                        query_params = fallback_params
                        use_semantic_search = False
                        had_connection_issue = False
                        connection_error_detail = ""
                        connection_error_status = None
                    except Exception as fallback_exc:
                        connection_error_detail = str(fallback_exc)
                        connection_error_status = extract_status_code(fallback_exc)

            unique_results = _dedupe_results(all_results)
            api_returned_count = len(unique_results)
            if callable(status_callback):
                status_callback(f"Finished searching OpenAlex. Fetched {api_returned_count} OpenAlex records.")

            filtered_results = [
                work
                for work in unique_results
                if _openalex_matches_local_filters(
                    work,
                    keyword_expr=keyword_expr,
                    year_range=year_range,
                    work_types=work_types,
                    language=language,
                    is_global_south=is_global_south,
                    institution_country_code=institution_country_code,
                    use_semantic_search=use_semantic_search,
                )
            ]
            post_filter_retained_count = len(filtered_results)
            results = filtered_results[:int(num_results)]

    except Exception as e:
        if callable(status_callback):
            status_callback(f"OpenAlex search failed: {e}")
        if emit_ui:
            st.error(f"Unexpected error during search: {e}")
        return

    if not results:
        connection_hint = (
            "\n\n4. Connection problem: please refresh the app and try again."
            if had_connection_issue
            else "\n\n4. There could be occasional connection problems. In such cases, please refresh the app and try again. If the problem persists, please contact us via the feedback form from the left sidebar."
        )
        traffic_hint = (
            "\n\n5. OpenAlex may temporarily pause or fail requests because of API traffic, usage limits, or server-side issues. If this happens, please wait a moment and try again."
        )
        if callable(status_callback) and had_connection_issue:
            if connection_error_status == 429:
                status_callback(
                    "OpenAlex did not return usable results. The API reported HTTP 429, which usually means a traffic or usage-limit pause."
                )
            elif connection_error_status in {500, 502, 503, 504}:
                status_callback(
                    f"OpenAlex did not return usable results. The API reported HTTP {connection_error_status}, which is likely a temporary server-side problem."
                )
            else:
                status_callback(
                    "OpenAlex did not return usable results. This may be due to a temporary connection or API traffic problem."
                )
        if had_connection_issue and connection_error_status in {500, 502, 503}:
            connection_hint += (
                f"\n\nOpenAlex server returned HTTP {connection_error_status}. "
                "This is likely temporary. Please try again in a moment."
            )
        display.warning(
            """
No results were returned. This can happen when:

1. Your search string and/or publication year range is too strict. Please loosen them and try again.

2. Some terms used in scientific literature are less common in grey literature (for example, indigenous knowledge systems).

3. Check the spelling of your keywords and use of boolean operators. The search supports AND/OR logic, parentheses, and double quoted phrases. For example: "climate change" AND (adaptation OR mitigation) AND "indigenous knowledge"`.
"""
            + connection_hint
            + traffic_hint
        )
        return None

    records = []
    for work in results:
        openalex_id = work.get("id")
        title = work.get("title")
        pub_date = work.get("publication_date")
        pub_year = work.get("publication_year")
        cited = work.get("cited_by_count")
        doi = work.get("doi")
        work_type = work.get("type")
        relevance_score = work.get("relevance_score")
        if relevance_score is None:
            relevance_score = work.get("_score")

        # Safely extract nested fields; some entries may have None instead of dict
        primary_loc = work.get("primary_location") or {}
        if not isinstance(primary_loc, dict):
            primary_loc = {}
        source_obj = primary_loc.get("source") or {}
        if not isinstance(source_obj, dict):
            source_obj = {}
        source = source_obj.get("display_name") or ""

        openalex_link = f'<a href="{openalex_id}" target="_blank">View</a>' if openalex_id else ""

        landing_url = primary_loc.get("landing_page_url") or ""
        oa_info = work.get("open_access") or {}
        if not isinstance(oa_info, dict):
            oa_info = {}
        oa_status = oa_info.get("oa_status") or ""
        is_oa = oa_info.get("is_oa")
        oa_flag = "Yes" if is_oa is True else "No" if is_oa is False else ""

        # Authors (limit to first 5 for readability)
        authorships = work.get("authorships") or []
        author_names = []
        if isinstance(authorships, list):
            for auth in authorships[:5]:
                name = (
                    (auth or {}).get("author", {}) or {}
                ).get("display_name")
                if name:
                    author_names.append(name)
        authors_display = ", ".join(author_names)

        # Abstract (OpenAlex uses inverted index; reconstruct if present)
        abstract_text = ""
        inverted = work.get("abstract_inverted_index")
        if isinstance(inverted, dict) and inverted:
            positions = []
            for word, idxs in inverted.items():
                for i in idxs:
                    positions.append((i, word))
            if positions:
                abstract_text = " ".join(word for _, word in sorted(positions))

        publisher = source_obj.get("publisher") or ""

        # Keywords
        kw_list = work.get("keywords") or []
        keywords_display = "; ".join(
            kw.get("display_name", "") for kw in kw_list if isinstance(kw, dict) and kw.get("display_name")
        )
        topics_display = get_work_topics(work)

        records.append({
            "OpenAlex": openalex_link,
            "OpenAlex URL": openalex_id,
            "Title": title,
            "Publication Date": pub_date,
            "Publication Year": pub_year,
            "Journal": source,
            "Type": work_type,
            "Authors": authors_display,
            "Open Access": oa_flag,
            "OA Status": oa_status,
            "Citations": cited,
            "DOI": doi,
            "Relevance Score": relevance_score,
            "Keywords": keywords_display,
            "Topics": topics_display,
            # CSV-only fields
            "Abstract": abstract_text,
            "Publisher": publisher,
            "URL": landing_url,
        })

    df = pd.DataFrame(records)

    # Display table (omit Language/URL and CSV-only columns)
    display_columns = [
        "OpenAlex",
        "Title",
        "Publication Date",
        "Publication Year",
        "Journal",
        "Type",
        "Authors",
        "Open Access",
        "OA Status",
        "Citations",
        "DOI",
        "Relevance Score",
        "Keywords",
        "Topics",
    ]
    df_display = df[[c for c in display_columns if c in df.columns]].copy()
    df_display = df_display.head(int(display_limit))

    # remove duplicates using raw ID
    try:
        df["raw_id"] = [r.get("id") for r in results]
        df = df.drop_duplicates(subset="raw_id").drop(columns="raw_id")
    except Exception:
        # If results structure differs, skip dedupe step
        pass

    openalex_total_text = str(openalex_total) if openalex_total else "an unknown number of"
    if not post_filter_exhaustive:
        filter_summary = (
            f"local post-filter retained at least {post_filter_retained_count} results before applying the max-number limit; "
            f"download files include the first {len(df)} filtered results"
        )
    elif post_filter_retained_count > len(df):
        filter_summary = (
            f"local post-filter retained {post_filter_retained_count} results before applying the max-number limit; "
            f"download files include the first {len(df)} filtered results"
        )
    else:
        filter_summary = f"local post-filter retained {post_filter_retained_count} results"

    summary_text = (
        f"OpenAlex reports {openalex_total_text} matches. "
        f"API returned {api_returned_count} records for this request; {filter_summary}. "
        "Json & CSV are available for download."
    )

    csv = df.to_csv(index=False).encode("utf-8")
    json_full = json.dumps(
        df.to_dict(orient="records"),
        indent=2,
        ensure_ascii=False,
    ).encode("utf-8")
    return {
        "csv": csv,
        "json": json_full,
        "total": len(df),
        "openalex_total": openalex_total,
        "shown": len(df_display),
        "summary": summary_text,
        "summary_lines": [f"OpenAlex reports {openalex_total_text} matches."],
        "api_returned_count": api_returned_count,
    }

