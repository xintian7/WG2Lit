import json
from typing import Any


def _escape_cypher_string(value: Any) -> str:
    """Escape values for safe single-quoted Cypher string literals."""
    if value is None:
        return ""
    text = str(value)
    return text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")


def _to_lc(value: Any) -> str:
    return str(value or "").strip().lower()


def _split_multi_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = [str(v).strip() for v in value if str(v).strip()]
    else:
        items = [v.strip() for v in str(value).split(";") if v.strip()]

    # case-insensitive dedupe while preserving first-seen display case
    seen = set()
    deduped = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def build_neo4j_cypher(payload: dict | None) -> bytes:
    """Convert search payload JSON records to an importable Neo4j Cypher script.

    Graph model:
    - (:Publication {title_lc, title, ...metadata})
    - (:Type {name_lc, name})
    - (:Keyword {name_lc, name})
    - (:Topic {name_lc, name})
    Relationships:
    - (Publication)-[:HAS_TYPE]->(Type)
    - (Publication)-[:HAS_KEYWORD]->(Keyword)
    - (Publication)-[:HAS_TOPIC]->(Topic)

    Case-insensitive merge keys:
    - Publication.title_lc
    - Type.name_lc
    - Keyword.name_lc
    - Topic.name_lc
    """
    if not payload:
        return b""

    raw_json = payload.get("json")
    if raw_json is None:
        return b""

    try:
        records = json.loads(raw_json)
    except Exception:
        return b""

    if not isinstance(records, list) or not records:
        return b""

    lines: list[str] = [
        "// Auto-generated Neo4j Cypher script",
        "// Run this file in Neo4j Browser or cypher-shell",
        "",
        "CREATE CONSTRAINT publication_title_lc IF NOT EXISTS FOR (p:Publication) REQUIRE p.title_lc IS UNIQUE;",
        "CREATE CONSTRAINT type_name_lc IF NOT EXISTS FOR (t:Type) REQUIRE t.name_lc IS UNIQUE;",
        "CREATE CONSTRAINT keyword_name_lc IF NOT EXISTS FOR (k:Keyword) REQUIRE k.name_lc IS UNIQUE;",
        "CREATE CONSTRAINT topic_name_lc IF NOT EXISTS FOR (tp:Topic) REQUIRE tp.name_lc IS UNIQUE;",
        "",
    ]

    for rec in records:
        if not isinstance(rec, dict):
            continue

        title = str(rec.get("Title") or "").strip()
        if not title:
            # title is the publication node key
            continue

        work_type = str(rec.get("Type") or "Unknown").strip() or "Unknown"
        keywords = _split_multi_values(rec.get("Keywords"))
        topics = _split_multi_values(rec.get("Topics"))

        # Metadata: all fields except graph-structure fields
        metadata = {
            k: v
            for k, v in rec.items()
            if k not in {"Title", "Type", "Keywords", "Topics"}
        }

        meta_parts = []
        for mk, mv in metadata.items():
            if mv is None:
                continue
            mk_safe = _escape_cypher_string(mk)
            mv_safe = _escape_cypher_string(mv)
            meta_parts.append(f"p.`{mk_safe}` = '{mv_safe}'")

        title_lc = _to_lc(title)
        title_safe = _escape_cypher_string(title)
        type_safe = _escape_cypher_string(work_type)
        type_lc = _to_lc(work_type)

        lines.append(f"MERGE (p:Publication {{title_lc: '{_escape_cypher_string(title_lc)}'}})")
        lines.append(f"SET p.title = '{title_safe}'")
        if meta_parts:
            lines.append("SET " + ", ".join(meta_parts))

        lines.append(f"MERGE (t:Type {{name_lc: '{_escape_cypher_string(type_lc)}'}})")
        lines.append(f"SET t.name = '{type_safe}'")
        lines.append("MERGE (p)-[:HAS_TYPE]->(t)")

        for kw in keywords:
            kw_safe = _escape_cypher_string(kw)
            kw_lc = _escape_cypher_string(_to_lc(kw))
            lines.append(f"MERGE (k:Keyword {{name_lc: '{kw_lc}'}})")
            lines.append(f"SET k.name = '{kw_safe}'")
            lines.append("MERGE (p)-[:HAS_KEYWORD]->(k)")

        for topic in topics:
            tp_safe = _escape_cypher_string(topic)
            tp_lc = _escape_cypher_string(_to_lc(topic))
            lines.append(f"MERGE (tp:Topic {{name_lc: '{tp_lc}'}})")
            lines.append(f"SET tp.name = '{tp_safe}'")
            lines.append("MERGE (p)-[:HAS_TOPIC]->(tp)")

        lines.append("")

    return "\n".join(lines).encode("utf-8")
