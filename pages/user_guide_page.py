import streamlit as st


_USER_GUIDE_MD = """
# **User guide**

This guide explains how to use **Climate Literature Navigator** for searching, reviewing, analyzing, and exporting climate-related literature across multiple sources.

---

# 1) What the app does

Climate Literature Navigator helps you:

- search literature from multiple sources in one workflow;
- keep the latest search as a cached working dataset;
- review records as cards, then narrow them by source and topic;
- analyze one source at a time from the cached search results;
- export the working results as CSV, JSON, BibTeX, and Neo4j Cypher.

The current user-facing data sources are:

- [OpenAlex](https://openalex.org/) for large-scale scholarly metadata and related grey literature;
- [ReliefWeb](https://reliefweb.int/) for humanitarian and policy-oriented documents;
- [United Nations Digital Library](https://digitallibrary.un.org/) for UN publications and official records;
- [World Bank Documents & Reports](https://documents.worldbank.org/) for World Bank reports and official documents.

---

# 2) Before you start

You need:

- a web browser;
- internet access;
- a clear search topic, ideally with a geographic, thematic, or institutional focus.

Web app URL:

[Climate Literature Navigator Web App](https://wg2literature.streamlit.app/)

---

# 3) How the app is organized

The workflow is split into four main pages:

- **Literature Search**: build a query and retrieve records;
- **Literature Analysis**: run charts on the cached results for one selected source;
- **Literature Review**: read results as cards, then filter by source and topic;
- **Literature Export**: download the current working dataset.

Important behavior:

- The app stores the **latest search result** in session memory as the current cached payload.
- The Analysis, Review, and Export pages all depend on that cached payload.
- If you run a new search, the cached payload is replaced by the latest results.

---

# 4) Literature Search page

## 4.1 Data source

Use **Data source** to select one or more sources.

Practical guidance:

- Select **OpenAlex only** when you need the fullest filtering options.
- Select multiple sources when you want broader coverage across scholarly, humanitarian, UN, and development-bank material.
- Mixed-source searches may take longer because each selected source is queried separately.

## 4.2 Keyword

The **Keyword** box is the most important search control.

Regular search supports:

- `AND` to require multiple concepts;
- `OR` to allow alternatives;
- parentheses such as `(water OR drought)` to group logic;
- double quotes such as `"climate change"` for exact phrases.

Recommended examples:

```text
"climate change" AND adaptation AND Kenya
```

```text
"climate change" AND (water OR drought) AND India
```

```text
"loss and damage" OR resilience
```

Use narrower queries when possible. A very broad query such as `climate change` alone can take longer and may return many marginal results.

## 4.3 Search behavior

The current search page uses the regular keyword-search path.

Practical guidance:

- use exact phrases in quotes for tighter matching;
- use `AND` and `OR` to control retrieval logic;
- narrow broad topics with a country, sector, or policy term.

## 4.4 Publication year

Use **Publication year** to define an inclusive date range.

Practical guidance:

- use recent years for fast policy scans;
- widen the range when a narrow period returns too little;
- remember that some source metadata may contain partial or inconsistent date fields.

## 4.5 Type

The **Type** selector is always visible, but it applies to **OpenAlex only**.

Examples include:

- `report`
- `article`
- `book`
- `dataset`
- `preprint`
- `review`
- `standard`

Practical guidance:

- Keep `report` if your focus is grey literature or policy documents.
- Add `article` if you also want academic studies.
- Do not expect this filter to restrict ReliefWeb, UN Digital Library, or World Bank results.

## 4.6 Language

The **Language** filter is shown only when **OpenAlex is the only selected source**.

Current options include:

- Any
- English
- Arabic
- Chinese
- French
- Russian
- Spanish

Practical guidance:

- The default is English.
- If you switch to another language, test the search both in English and in the target language because retrieval can differ.

## 4.7 UN member states

The **UN member states** filter is shown only when **OpenAlex is the only selected source**.

What it does:

- It filters to works where **at least one institution or affiliation** in the publication is associated with the selected member state.

What it does not do:

- It does not mean the publication is about that country.
- It does not filter ReliefWeb, UN Digital Library, or World Bank.

Use this filter when you want a country-linked institutional perspective rather than a pure topical search.

## 4.8 Max Number / Source

The **Max Number / Source** slider controls how many results to retrieve per selected source.

Current behavior:

- the slider currently allows **1 to 1000**;
- the default is **200**;
- the number applies **per selected source**, not to the combined total.

Example:

- if you select 4 sources and set **Max Number / Source = 200**, the theoretical upper limit before filtering and deduplication is 800 records.

Practical guidance:

- Start with 50 to 200 for exploration.
- Increase only after you confirm the query is behaving well.
- Larger numbers can be slower, especially for very broad OpenAlex queries.

## 4.9 Search button

Click **Search Selected Source(s)** to run the current query.

After the search finishes:

- the app stores the results as the current cached payload;
- a summary message appears;
- the other pages can now use those results.

If the app suggests a cleaned or normalized query before searching, review that suggestion carefully before proceeding.

---

# 5) Search strategy recommendations

For better results, combine the topic with at least one narrowing element:

- geography: `Kenya`, `India`, `Pacific Islands`;
- sector: `water`, `health`, `agriculture`, `energy`;
- policy framing: `adaptation`, `mitigation`, `loss and damage`, `finance`;
- institution or governance terms: `policy`, `national adaptation plan`, `resilience`, `disaster risk reduction`.

Strong example queries:

```text
"climate change" AND adaptation AND Kenya
```

```text
"climate change" AND (water OR irrigation) AND India
```

```text
"disaster risk reduction" AND resilience AND Bangladesh
```

When a search is too broad:

- add an exact phrase in quotes;
- add a country or region;
- narrow the year range;
- reduce the number of selected sources;
- reduce **Max Number / Source**.

When a search is too narrow:

- remove one restrictive term;
- widen the year range;
- try alternative keywords or synonyms for OpenAlex;
- test synonyms or related phrasing.

---

# 6) Literature Analysis page

The **Literature Analysis** page works on the cached search results.

Important behavior:

- You must run a search first.
- You can analyze **one source at a time**.
- Use the **Data source** dropdown at the top of the page to choose which source to analyze.

Click **Analyze Results** to generate charts.

General interpretation guidance:

- OpenAlex usually has the richest structured metadata.
- ReliefWeb and UN Digital Library may rely more heavily on theme or topic metadata than keyword-style scholarly metadata.
- Charts depend on the metadata actually available in the selected source.

Use **Clear Results** on this page when you want to clear the currently displayed analysis output. This does **not** delete the cached search results themselves.

Recommended workflow:

1. Search first.
2. Open Literature Analysis.
3. Choose one source from the dropdown.
4. Run analysis.
5. Switch source and rerun if you want to compare sources separately.

---

# 7) Literature Review page

The **Literature Review** page is designed for reading and narrowing the cached results.

## 7.1 Filter Data Source

Use **Filter Data Source** to keep only one or more sources visible in the review interface.

This is especially useful when your search combined multiple sources and you want to inspect them separately.

## 7.2 Filter Topic

Use **Filter Topic** to narrow the visible records using the topics present in the cached results.

Current behavior:

- topic choices are built from the records currently remaining after the source filter;
- the topic popover supports **Select all**, **Clear**, and topic search;
- a **No Generated Topics** option may appear when some records do not have topic metadata.

## 7.3 Filter Type

Use **Filter Type** to keep only selected publication types in the review set.

Current behavior:

- the type filter uses the same popover interaction style as the topic filter;
- it supports **Select all**, **Clear**, and type search;
- available types are built from the records currently remaining after the source filter.

## 7.4 Filter Keyword

Use **Filter Keyword** to keep only records whose visible text contains the keywords you enter.

Current behavior:

- the filter checks text from fields such as title, abstract, topics, keywords, authors, source, journal, and type;
- if you separate entries with `;`, the review filter requires all entered fragments to be present somewhere in the searchable record text;
- example: `adaptation; risks` keeps only records containing both fragments.

## 7.5 Sort by

Sorting options depend on the cached records:

- **Relevance** is available when OpenAlex records are present;
- **Date** is always available and is often the most practical option for policy review.

## 7.6 Publication year filter

Use **Publication year filter** to limit the review set to records with publication years inside the selected range.

Current behavior:

- the slider is built from the available year values in the currently source-filtered records;
- records without usable year metadata are excluded when the year filter is active on a dataset that has year values.

## 7.7 Read Publications

Click **Read Publications** to open the card-style review display.

Current review behavior:

- results are paginated at **10 records per page**;
- the page shows filtered counts and page numbers;
- you can enable **Hide abstracts** if you want a more compact review view.

## 7.8 Skip

Use **Skip** on individual records to remove items you do not want in the current review/export workflow.

Important behavior:

- skipped records are removed from the review workflow for the current cached session;
- the review-refined export section uses the post-filter, post-skip working set;
- analysis does **not** use the skipped review subset and instead works from the cached search payload.

Practical advice:

- use Review to curate a cleaner export set;
- use Analysis to understand the full searched set for a selected source.

## 7.9 Load CSV

The **Load CSV** button is present but still under construction.

---

# 8) Literature Export page

The **Literature Export** page provides two separate export sections.

Available downloads:

- **Download CSV**
- **Download JSON**
- **Download BibTex (for Zotero)**
- **Download Neo4j**

Current file names are fixed by the app.

Important behavior:

- export is enabled only after a search has produced a cached payload;
- the first section, **Download All Files**, exports the full cached search result set without Literature Review filtering or skipping;
- the second section, **Download Files After Literature Review**, exports only the records remaining after the active Literature Review filters and skipped items are applied.

Practical difference between the two sections:

- use **Download All Files** when you need the complete search output for archiving or later reprocessing;
- use **Download Files After Literature Review** when you want the curated working set you kept after review.

Practical uses:

- CSV for spreadsheet review and quick sharing;
- JSON for structured downstream processing;
- BibTeX for Zotero import;
- Neo4j Cypher for graph-oriented exploration.

Basic Zotero workflow:

1. Run a search.
2. Choose either the full export section or the review-refined export section.
3. Export **BibTex**.
3. Open Zotero.
4. Use **File -> Import**.
5. Import the downloaded `.bib` file into a selected collection.

---

# 9) Source-specific notes

## OpenAlex

OpenAlex supports the richest search behavior in the app.

It is the only source that currently supports in-app:

- type filtering;
- language filtering;
- UN member state affiliation filtering.

OpenAlex `keywords` and `topics` are generated by OpenAlex's own enrichment and classification pipeline. They are not direct copies of your input terms.

That means:

- a relevant record may not display your exact search wording;
- displayed topics may be broader, normalized, or inferred;
- topic and keyword enrichment may still surface useful records without exact wording overlap.

References:

- [OpenAlex searching guide](https://developers.openalex.org/guides/searching)
- [OpenAlex keywords](https://help.openalex.org/hc/en-us/articles/24736201130391-Keywords)
- [OpenAlex topics](https://help.openalex.org/hc/en-us/articles/24736129405719-Topics)

## ReliefWeb

ReliefWeb is useful for humanitarian, disaster, crisis, and response-oriented literature.

Expect stronger value when your search includes terms related to:

- adaptation;
- resilience;
- disasters;
- humanitarian response;
- recovery and vulnerability.

## United Nations Digital Library

The UN Digital Library is especially useful when you need:

- UN reports and publications;
- official UN system materials;
- institutionally authored multilateral documents.

## World Bank Documents & Reports

World Bank is especially useful for:

- development policy reports;
- sector diagnostics;
- country and regional reports;
- financing, resilience, and development planning literature.

---

# 10) Scenarios

## Workflow A: fast exploration

Use this when you are just scoping a topic.

1. Select **OpenAlex**.
2. Enter a broad but not minimal keyword query.
3. Keep **Max Number / Source** at 50 to 200.
4. Try alternative phrasings or synonyms if regular search looks too strict.
5. Review the result summary.
6. Open Literature Review and inspect topics.

## Workflow B: multi-source policy scan

Use this when you want a wider evidence base.

1. Select OpenAlex, ReliefWeb, UN Digital Library, and World Bank.
2. Use a focused Boolean query.
3. Keep the year range reasonably tight.
4. Start with **Max Number / Source = 100 to 200**.
5. Search.
6. In Literature Analysis, inspect one source at a time.
7. In Literature Review, filter by source, topic, type, keyword, and year as needed.
8. Skip weak records.
9. In Literature Export, use **Download Files After Literature Review** to export the curated set.

## Workflow C: country-linked OpenAlex scan

Use this when you want OpenAlex literature connected to institutions from one country.

1. Select **OpenAlex only**.
2. Enter a focused query.
3. Set **Language** if needed.
4. Set **UN member states**.
5. Keep `report` or add `article` depending on your purpose.
6. Search and review.

---

# 11) Troubleshooting

## No results

Try the following:

- remove one restrictive term;
- widen the year range;
- remove the UN member state filter;
- use fewer exact phrases;
- try alternative OpenAlex phrasings or synonyms.

## Too many results

Try the following:

- add a country, region, sector, or policy term;
- use exact phrases in quotes;
- reduce the year range;
- reduce **Max Number / Source**;
- limit the search to fewer sources.

## Search is slow

Common causes:

- very broad queries such as `climate change` alone;
- large **Max Number / Source** values;
- multiple sources selected at once.

Ways to improve speed:

- narrow the query;
- add quoted phrases;
- reduce the result limit;
- search one source first, then expand.

## Analysis page shows a warning

Check whether:

- you already ran a search;
- the cached payload contains records for the selected source;
- the selected source has the metadata needed for the chart being generated.

## Review page looks empty

Check whether:

- all source filters were deselected;
- all topic filters were cleared;
- all matching records were skipped;
- you still need to click **Read Publications**.

## Export buttons are disabled

Run a search first so the app has a cached payload to export.

---

# 12) Current limitations

At the moment:

- type filtering applies only to OpenAlex;
- language and UN member state filters appear only when OpenAlex is the sole selected source;
- analysis is source-by-source rather than combined into one chart set;
- review filters and skips affect the review-refined export section but not analysis;
- **Load CSV** is still under construction.

---

# Appendix: Behavior of the keyword-based search in OpenAlex

In this app, the `Keyword` box is sent to OpenAlex as a text query over indexed document metadata (primarily title/abstract and related indexed fields), and when you separate terms with `;` in regular mode the app treats them as a Boolean AND (all terms must be present for the search), while semantic mode sends a broader natural-language style query where OpenAlex relevance ranking can return conceptually related records even if exact terms are not all present.

OpenAlex `keywords` and `topics` shown in results are metadata produced by OpenAlex's own enrichment/classification pipeline, so they may differ from your input wording because they are normalized labels, synonyms, higher-level concepts, or model-assigned themes; this is especially common for grey literature, where source metadata is often sparse (missing abstracts, weak indexing, non-standard formats), so keyword/topic extraction can be limited, noisy, or absent. That is why a record can still be relevant even when its displayed keywords do not exactly match your entered terms, and why semantic mode typically increases recall (more potentially relevant items) while Boolean mode increases precision (stricter term matching).

Practical points to keep in mind: use Boolean mode for reproducible, narrow searches; use semantic mode for discovery; test a few term variants/synonyms; and remember that publication type, language, date, and institution filters can change results as much as the keyword query itself.

In this application, the `Keyword` field is passed to OpenAlex as a search query against indexed document metadata. According to the [OpenAlex API documentation](https://developers.openalex.org/guides/searching), the default search parameter for works searches across titles, abstracts, and, where available, indexed full text. Full-text indexing is only available for a subset of records, primarily open-access materials for which OpenAlex has searchable text available.

The application supports two search modes:

- [Boolean (regular) mode](https://developers.openalex.org/guides/searching)

When terms are separated with `;`, the application interprets them as a Boolean AND query. In practice, this means all specified terms must be represented in the indexed searchable fields for a record to match. This mode favors precision and is generally better for focused, reproducible retrieval strategies.

- [Semantic mode](https://developers.openalex.org/guides/semantic-search)

Semantic mode submits a broader natural-language style query. OpenAlex's relevance ranking and semantic retrieval mechanisms may return records that are conceptually related even when the exact query terms are absent from the searchable metadata. This mode favors recall and is often more useful for exploratory searching and topic discovery. OpenAlex's newer semantic retrieval features are explicitly designed to identify related works based on meaning rather than exact keyword overlap.

The [`keywords`](https://help.openalex.org/hc/en-us/articles/24736201130391-Keywords?utm_source=chatgpt.com) and [`topics`](https://help.openalex.org/hc/en-us/articles/24736129405719-Topics?utm_source=chatgpt.com) displayed in results are **not** direct reflections of the user's input terms. Instead, they are generated through OpenAlex's own enrichment and classification pipeline, which applies normalized concepts, inferred themes, hierarchical topic mappings, and synonym handling.

In practice:

- use Boolean mode for narrow, auditable, and reproducible searches;
- use semantic mode for broader discovery and literature exploration.
"""


def render_user_guide_page() -> None:
    st.divider()
    lines = _USER_GUIDE_MD.splitlines()
    normalized_lines: list[str] = []
    first_h1_seen = False

    for line in lines:
        if line.startswith("# "):
            if not first_h1_seen:
                normalized_lines.append(line)
                first_h1_seen = True
            else:
                normalized_lines.append("## " + line[2:])
        elif line.startswith("## "):
            normalized_lines.append("### " + line[3:])
        else:
            normalized_lines.append(line)

    st.markdown("\n".join(normalized_lines))
