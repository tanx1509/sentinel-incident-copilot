"""
Sentinel Memory — the 'learning' layer.

THREE-TIER DESIGN:
  - Working memory:  in-process dict, scoped to current incident
  - Episodic memory: past resolved incidents, queryable by semantic similarity
  - Semantic memory: service graph + runbooks (in telemetry.json)

The episodic memory uses TF-IDF + cosine similarity as a stand-in for a 
vector DB. This is fully deterministic and works offline — perfect for a demo — 
but the interface mirrors exactly what you'd do with Pinecone/Weaviate/FAISS.
"""
import json
import math
import re
from pathlib import Path
from collections import Counter
from typing import Any

DATA_DIR = Path(__file__).parent.parent / "data"

# ---------------- Episodic Memory (Vector-DB equivalent) ----------------

def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[a-zA-Z][a-zA-Z0-9-]+", text) if len(t) > 2]

class EpisodicMemory:
    """Vector store of past incidents. Queryable by natural language."""

    def __init__(self):
        data = json.loads((DATA_DIR / "incidents.json").read_text())
        self.incidents = data["historical_incidents"]
        self._build_index()

    def _build_index(self):
        """TF-IDF index — stand-in for embedding model."""
        # Document = concatenated searchable fields
        self.docs = []
        for inc in self.incidents:
            text = " ".join([
                inc["title"],
                inc["symptoms"],
                inc["root_cause"],
                " ".join(inc["services_involved"]),
                inc.get("region", ""),
                " ".join(inc.get("tags", [])),
            ])
            self.docs.append(_tokenize(text))

        # Document frequency for IDF
        df = Counter()
        for doc in self.docs:
            for term in set(doc):
                df[term] += 1
        N = len(self.docs)
        self.idf = {t: math.log((N + 1) / (c + 1)) + 1 for t, c in df.items()}

        # TF-IDF vectors
        self.vectors = []
        for doc in self.docs:
            tf = Counter(doc)
            vec = {t: (tf[t] / len(doc)) * self.idf.get(t, 1.0) for t in tf}
            self.vectors.append(vec)

    @staticmethod
    def _cosine(a: dict, b: dict) -> float:
        if not a or not b:
            return 0.0
        common = set(a) & set(b)
        dot = sum(a[t] * b[t] for t in common)
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        return dot / (na * nb) if na and nb else 0.0

    def similar_incidents(self, query: str, top_k: int = 5, min_similarity: float = 0.1) -> list[dict]:
        """Semantic search. Returns incidents with similarity scores."""
        q_tokens = _tokenize(query)
        q_tf = Counter(q_tokens)
        q_vec = {t: (q_tf[t] / max(len(q_tokens), 1)) * self.idf.get(t, 1.0) for t in q_tf}

        scored = []
        for i, vec in enumerate(self.vectors):
            sim = self._cosine(q_vec, vec)
            if sim >= min_similarity:
                scored.append((sim, self.incidents[i]))
        scored.sort(key=lambda x: -x[0])
        return [{"similarity": round(s, 3), **inc} for s, inc in scored[:top_k]]

    def add_incident(self, incident: dict) -> None:
        """Learning loop — new resolved incident becomes future memory."""
        self.incidents.append(incident)
        self._build_index()


# ---------------- Working Memory (per-incident state) ----------------

class WorkingMemory:
    """Scratchpad for the current incident. TTL would be 24h in prod."""

    def __init__(self, incident_id: str):
        self.incident_id = incident_id
        self.observations: list[dict] = []     # Tool call results
        self.hypotheses: list[dict] = []       # Ranked root-cause theories
        self.actions_taken: list[dict] = []    # Audit trail
        self.slack_transcript: list[str] = []  # For Scribe agent

    def record_observation(self, tool: str, args: dict, result: Any):
        self.observations.append({"tool": tool, "args": args, "result": result})

    def set_hypotheses(self, hypotheses: list[dict]):
        self.hypotheses = hypotheses

    def record_action(self, action: dict):
        self.actions_taken.append(action)
