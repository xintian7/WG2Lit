import streamlit as st


_USER_GUIDE_MD = """
# **User guide**

This document helps IPCC AR7 WGII authors use **Climate Literature Navigator (version 0.1)** to look for climate-related literature.

---

# 1) What this app does

**Climate Literature Navigator** is a web app designed for:

- Searching climate-related grey literature from [OpenAlex](https://openalex.org/?utm_source=chatgpt.com)
- Reviewing and analyzing returned records
- Filtering and refining records
- Exporting results as CSV, JSON, and Neo4j Cypher

---

# 2) Quick Start

## Prerequisites

- Web browser (*Google Chrome is recommended*)
- Internet access (*required for OpenAlex*)

## Web App URL

[Climate Literature Navigator Web App](https://wg2literature.streamlit.app/?utm_source=chatgpt.com)

---

# 3) Core Controls in Literature Searching

- **Keyword**  
Separate terms with `;` (*AND logic*).

- **Publication year**  
Inclusive year range.

- **Type**  
Up to 3 selected types are used:

Article

- Book
- Book Chapter
- Dataset
- Dissertation
- Editorial
- Erratum
- Letter
- Monograph
- Paratext
- Peer Review
- Preprint
- Reference Entry
- Report
- Review
- Standard
- Supplementary Materials

- **Language**  
Language filter (*default: English*).  
Available languages:

English

- Arabic
- Chinese
- French
- Russian
- Spanish

- **UN member states**  
Include only works with at least one institution from the selected member state.

- **Max Number / Type**  
Fetch size per type.

- **Sort by**

Relevance

- Citation count
- Date

---

# 4) Buttons and Outputs

## In *Literature Searching*

- **Search OpenAlex**  
Runs the query and updates the current payload.

- **Analyze Results**  
Runs analysis on the latest payload (*cached data*).

- **Clear Results**  
Clears the current visible output state.

- **Download CSV / JSON / Neo4j**  
Exports the current search results.

- **Download BibTex**  
Exports the current search results as a `.bib` file (BibTeX format), ready for direct import into Zotero.  
Step 1: search and save the result in bib  
Step 2: start Zotero and click File-Import  
Step 3: Import the downloaded .bib file to a Zotero folder  
Step 4: Read and manage your imported literature in Zotero

## In *Grey Literature Review & Export*

- **View HTML**  
Shows card-style records.

- **Filter Topic**  
Narrows displayed cards.

- **Skip**  
Removes a search result.  
You can download the results again using the **Download CSV / JSON / Neo4j buttons.**

- **Similar works / Citing works / Cited works**  
Currently under construction.

---

# 5) User Scenario (Recommended Workflow)

## Scenario

You are preparing references on climate change-water in Kenya and are looking for policy-relevant grey literature published in recent years.

## Steps

1. Set **Keyword** to:

```
climate change; water
```

2. Set **Publication year** to:

```
(2020, 2026)
```

3. Set **Type** to:

`report`

4. `preprint`

5. Keep **Language** as `English` (*default*).

6. Set **UN member states** to `Kenya` (*or another focus country*).

7. Set:  
**Max Number / Type** = `325`

8. **Sort by** = `Relevance`

9. Click **Search OpenAlex**.

10. Click **Analyze Results**. The analysis includes:  
Number of publications per year

11. Occurrence of top 10 keywords
12. Co-occurrence of keywords
13. Most related topics per year (*via OpenAlex's topic modeling*)
14. Word cloud of keywords (*under construction*)

15. Save the results as:

CSV

16. JSON
17. Neo4j files

18. Click **View HTML** and select topics.
19. Review publication metadata and abstracts.

1. For less relevant publications, click **Skip**.  
You can optionally download the remaining filtered results again.

2. Other buttons and functions are still under construction.

3. To search for another topic, refresh the page and start a new search.

---

# 7) Troubleshooting

- **No results**  
Broaden publication years or remove the country filter.

- **Too many results**  
Tighten keywords, narrow publication years, or reduce selected types.

- **Slow response**  
Lower **Max Number / Type**.

- **Analyze disabled**  
Run **Search OpenAlex** first.

---

# 8) Notes

- Data is sourced from [OpenAlex](https://openalex.org/?utm_source=chatgpt.com) and may vary depending on metadata quality.

# 9) Behavior of the keyword-based search in OpenAlex

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
