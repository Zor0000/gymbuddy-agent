"""Neo4j driver singleton.

Usage:
    from gymbuddy.graph_client import get_driver, run
    rows = run("MATCH (e:Exercise) RETURN count(e) AS n").records
"""
from __future__ import annotations

import atexit
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

from neo4j import GraphDatabase, Driver, Session

from gymbuddy.config import settings

_driver: Driver | None = None


def get_driver() -> Driver:
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        atexit.register(_driver.close)
    return _driver


@contextmanager
def session() -> Iterator[Session]:
    with get_driver().session(database=settings.neo4j_database) as s:
        yield s


@dataclass
class QueryResult:
    records: list[dict[str, Any]]
    summary_counters: dict[str, int]


def run(cypher: str, **params: Any) -> QueryResult:
    """Execute Cypher, return a small dataclass with records + write counters."""
    with session() as s:
        result = s.run(cypher, **params)
        records = [r.data() for r in result]
        summary = result.consume()
        counters = summary.counters.__dict__ if summary.counters else {}
    return QueryResult(records=records, summary_counters=counters)
