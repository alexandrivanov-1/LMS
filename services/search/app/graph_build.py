import os
from datetime import date
from typing import Any, Dict, List, Optional

import psycopg
from neo4j import GraphDatabase
from psycopg.rows import dict_row

DSN = os.getenv("POSTGRES_DSN")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "neo4j")

LABEL_MAP = {
    "source": "Source",
    "norm_unit": "NormUnit",
    "chunk": "Chunk",
    "knowledge_atom": "KnowledgeAtom",
}


def _iso(value: Optional[date]) -> Optional[str]:
    return value.isoformat() if value else None


def _pg_conn():
    if not DSN:
        raise RuntimeError("POSTGRES_DSN is required for graph build")
    return psycopg.connect(DSN, row_factory=dict_row)


def _load_data() -> Dict[str, Any]:
    with _pg_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id::text AS id, kind, title, valid_from, valid_to
            FROM source
            """
        )
        sources = [
            {
                "id": row["id"],
                "kind": row["kind"],
                "title": row.get("title"),
                "valid_from": _iso(row.get("valid_from")),
                "valid_to": _iso(row.get("valid_to")),
            }
            for row in cur.fetchall()
        ]

        cur.execute(
            """
            SELECT id::text AS id, source_id::text AS source_id, law, article, part, point, subpoint,
                   valid_from, valid_to
            FROM norm_unit
            """
        )
        norm_units = [
            {
                "id": row["id"],
                "source_id": row.get("source_id"),
                "law": row.get("law"),
                "article": row.get("article"),
                "part": row.get("part"),
                "point": row.get("point"),
                "subpoint": row.get("subpoint"),
                "valid_from": _iso(row.get("valid_from")),
                "valid_to": _iso(row.get("valid_to")),
            }
            for row in cur.fetchall()
        ]

        cur.execute(
            """
            SELECT id::text AS id, source_id::text AS source_id, norm_unit_id::text AS norm_unit_id,
                   page, slide, timecode, valid_from, valid_to
            FROM chunk
            """
        )
        chunks = [
            {
                "id": row["id"],
                "source_id": row.get("source_id"),
                "norm_unit_id": row.get("norm_unit_id"),
                "page": row.get("page"),
                "slide": row.get("slide"),
                "timecode": row.get("timecode"),
                "valid_from": _iso(row.get("valid_from")),
                "valid_to": _iso(row.get("valid_to")),
            }
            for row in cur.fetchall()
        ]

        cur.execute(
            """
            SELECT id, title, type, status, version, prerequisites
            FROM knowledge_atom
            """
        )
        atoms = [
            {
                "id": row["id"],
                "title": row.get("title"),
                "type": row.get("type"),
                "status": row.get("status"),
                "version": row.get("version"),
                "prerequisites": row.get("prerequisites") or [],
            }
            for row in cur.fetchall()
        ]

        cur.execute(
            """
            SELECT atom_id, norm_unit_id::text AS norm_unit_id, chunk_id::text AS chunk_id
            FROM atom_citation
            """
        )
        citations = cur.fetchall()

        cur.execute(
            """
            SELECT id, from_type, from_id, to_type, to_id, relation_type, weight
            FROM impact_link
            """
        )
        impact_links = cur.fetchall()

    return {
        "sources": sources,
        "norm_units": norm_units,
        "chunks": chunks,
        "atoms": atoms,
        "citations": citations,
        "impact_links": impact_links,
    }


def build_graph() -> None:
    data = _load_data()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    with driver.session() as session:
        session.execute_write(_reset_graph)
        session.execute_write(_merge_nodes, "Source", data["sources"])
        session.execute_write(_merge_nodes, "NormUnit", data["norm_units"])
        session.execute_write(_merge_nodes, "Chunk", data["chunks"])
        session.execute_write(_merge_nodes, "KnowledgeAtom", data["atoms"])
        session.execute_write(_connect_has_unit, data["norm_units"])
        session.execute_write(_connect_has_chunk, data["chunks"])
        session.execute_write(_connect_evidenced_by, data["citations"])
        session.execute_write(_connect_prerequisites, data["atoms"])
        session.execute_write(_connect_impacts, data["impact_links"])
        session.execute_write(_connect_valid_during, data["norm_units"], data["chunks"])
    driver.close()


def _reset_graph(tx):
    tx.run("MATCH (n) DETACH DELETE n")


def _merge_nodes(tx, label: str, nodes: List[Dict[str, Any]]):
    if not nodes:
        return
    tx.run(
        f"UNWIND $nodes AS node MERGE (n:{label} {{id: node.id}}) SET n += node",
        nodes=nodes,
    )


def _connect_has_unit(tx, norm_units: List[Dict[str, Any]]):
    rels = [nu for nu in norm_units if nu.get("source_id")]
    if not rels:
        return
    tx.run(
        """
        UNWIND $rels AS rel
        MATCH (s:Source {id: rel.source_id}), (n:NormUnit {id: rel.id})
        MERGE (s)-[:HAS_UNIT]->(n)
        """,
        rels=rels,
    )


def _connect_has_chunk(tx, chunks: List[Dict[str, Any]]):
    norm_links = [ch for ch in chunks if ch.get("norm_unit_id")]
    if norm_links:
        tx.run(
            """
            UNWIND $rels AS rel
            MATCH (n:NormUnit {id: rel.norm_unit_id}), (c:Chunk {id: rel.id})
            MERGE (n)-[:HAS_CHUNK]->(c)
            """,
            rels=norm_links,
        )
    source_links = [ch for ch in chunks if ch.get("source_id")]
    if source_links:
        tx.run(
            """
            UNWIND $rels AS rel
            MATCH (s:Source {id: rel.source_id}), (c:Chunk {id: rel.id})
            MERGE (s)-[:HAS_CHUNK]->(c)
            """,
            rels=source_links,
        )


def _connect_evidenced_by(tx, citations):
    if not citations:
        return
    tx.run(
        """
        UNWIND $rows AS row
        MATCH (a:KnowledgeAtom {id: row.atom_id}), (c:Chunk {id: row.chunk_id})
        MERGE (a)-[:EVIDENCED_BY]->(c)
        """,
        rows=[row for row in citations if row["atom_id"] and row["chunk_id"]],
    )


def _connect_prerequisites(tx, atoms: List[Dict[str, Any]]):
    rows = []
    for atom in atoms:
        for pre in atom.get("prerequisites", []):
            rows.append({"pre": pre, "atom": atom["id"]})
    if not rows:
        return
    tx.run(
        """
        UNWIND $rows AS row
        MATCH (a:KnowledgeAtom {id: row.atom}), (p:KnowledgeAtom {id: row.pre})
        MERGE (p)-[:PREREQUISITE_OF]->(a)
        """,
        rows=rows,
    )


def _connect_impacts(tx, impacts):
    for row in impacts:
        start_label = LABEL_MAP.get((row["from_type"] or "").lower())
        end_label = LABEL_MAP.get((row["to_type"] or "").lower())
        if not start_label or not end_label:
            continue
        cypher = (
            f"MATCH (s:{start_label} {{id: $sid}}), (t:{end_label} {{id: $tid}}) "
            "MERGE (s)-[r:AFFECTS]->(t) "
            "SET r.relation_type = $relation_type, r.weight = $weight"
        )
        tx.run(
            cypher,
            sid=row["from_id"],
            tid=row["to_id"],
            relation_type=row.get("relation_type"),
            weight=row.get("weight"),
        )


def _connect_valid_during(tx, norm_units: List[Dict[str, Any]], chunks: List[Dict[str, Any]]):
    source_rel = [nu for nu in norm_units if nu.get("source_id") and (nu.get("valid_from") or nu.get("valid_to"))]
    if source_rel:
        tx.run(
            """
            UNWIND $rows AS row
            MATCH (s:Source {id: row.source_id}), (n:NormUnit {id: row.id})
            MERGE (s)-[r:VALID_DURING]->(n)
            SET r.from = row.valid_from, r.to = row.valid_to
            """,
            rows=source_rel,
        )
    chunk_rel = [ch for ch in chunks if ch.get("norm_unit_id") and (ch.get("valid_from") or ch.get("valid_to"))]
    if chunk_rel:
        tx.run(
            """
            UNWIND $rows AS row
            MATCH (n:NormUnit {id: row.norm_unit_id}), (c:Chunk {id: row.id})
            MERGE (n)-[r:VALID_DURING]->(c)
            SET r.from = row.valid_from, r.to = row.valid_to
            """,
            rows=chunk_rel,
        )


def get_subgraph(node_id: str, depth: int) -> Dict[str, Any]:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    with driver.session() as session:
        node_result = session.run(
            """
            MATCH (start {id: $id})
            OPTIONAL MATCH (start)-[*1..$depth]-(node)
            WITH COLLECT(DISTINCT node) AS nodes, start
            WITH [n IN nodes WHERE n IS NOT NULL] + start AS all_nodes
            UNWIND all_nodes AS n
            RETURN DISTINCT labels(n) AS labels, n.id AS id, properties(n) AS props
            """,
            id=node_id,
            depth=depth,
        )
        for record in node_result:
            props = dict(record["props"])
            props["id"] = record["id"]
            nodes.append({"id": record["id"], "labels": record["labels"], "properties": props})
        if not nodes:
            driver.close()
            return {"nodes": [], "edges": []}
        edge_result = session.run(
            """
            MATCH (start {id: $id})
            MATCH path=(start)-[*1..$depth]-(node)
            UNWIND relationships(path) AS rel
            WITH DISTINCT rel
            RETURN type(rel) AS type,
                   startNode(rel).id AS start_id,
                   labels(startNode(rel)) AS start_labels,
                   endNode(rel).id AS end_id,
                   labels(endNode(rel)) AS end_labels,
                   properties(rel) AS props
            """,
            id=node_id,
            depth=depth,
        )
        for record in edge_result:
            edges.append(
                {
                    "type": record["type"],
                    "from": {"id": record["start_id"], "labels": record["start_labels"]},
                    "to": {"id": record["end_id"], "labels": record["end_labels"]},
                    "properties": dict(record["props"]),
                }
            )
    driver.close()
    return {"nodes": nodes, "edges": edges}
