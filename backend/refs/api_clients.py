"""Thin clients for the REST APIs backing the fetch-style tools.

Each client exposes a small number of typed methods. Tools wrap these
methods; they do NOT hand raw URLs to the model.

A simple in-memory cache keyed on query args avoids re-hitting slow APIs
within a session.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional


class _SessionCache:
    def __init__(self, max_entries: int = 2000):
        self._data: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._max = max_entries

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            return self._data.get(key)

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            if len(self._data) >= self._max:
                # Drop the oldest (Python dicts preserve insertion order).
                for k in list(self._data)[: len(self._data) - self._max + 1]:
                    self._data.pop(k, None)
            self._data[key] = value


def _http_get_json(url: str, *, timeout: int = 60, headers: Optional[Dict[str, str]] = None) -> Any:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "sc-agent/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class EnsemblClient:
    BASE = "https://rest.ensembl.org"

    def __init__(self):
        self._cache = _SessionCache()

    def gene_info(self, symbol: str, species: str = "homo_sapiens") -> Dict[str, Any]:
        key = f"gene:{species}:{symbol}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        url = f"{self.BASE}/lookup/symbol/{species}/{symbol}?expand=0"
        data = _http_get_json(url, headers={"Accept": "application/json", "User-Agent": "sc-agent/1.0"})
        self._cache.put(key, data)
        return data


class JasparClient:
    BASE = "https://jaspar.genereg.net/api/v1"

    def __init__(self):
        self._cache = _SessionCache()

    def motif(self, motif_id: str) -> Dict[str, Any]:
        key = f"motif:{motif_id}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        data = _http_get_json(f"{self.BASE}/matrix/{motif_id}/")
        self._cache.put(key, data)
        return data

    def search_by_tf(self, tf_symbol: str, species_tax_id: Optional[str] = None) -> Dict[str, Any]:
        key = f"tf:{tf_symbol}:{species_tax_id}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        params = {"name": tf_symbol}
        if species_tax_id:
            params["tax_id"] = species_tax_id
        url = f"{self.BASE}/matrix/?{urllib.parse.urlencode(params)}"
        data = _http_get_json(url)
        self._cache.put(key, data)
        return data


class CellxGeneClient:
    BASE = "https://api.cellxgene.cziscience.com"

    def __init__(self):
        self._cache = _SessionCache()

    def search_datasets(
        self,
        tissue: Optional[str] = None,
        species: Optional[str] = None,
        assay: Optional[str] = None,
    ) -> Dict[str, Any]:
        key = f"atlas:{tissue}:{species}:{assay}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        # CellxGene Discover's collections endpoint — kept simple; real-world
        # usage may require pagination and auth headers.
        data = _http_get_json(f"{self.BASE}/dp/v1/collections")
        filtered = []
        for entry in data.get("collections", []) if isinstance(data, dict) else data:
            if tissue and tissue.lower() not in json.dumps(entry).lower():
                continue
            if species and species.lower() not in json.dumps(entry).lower():
                continue
            filtered.append(entry)
        result = {"n_matches": len(filtered), "matches": filtered[:20]}
        self._cache.put(key, result)
        return result

    def dataset_metadata(self, dataset_id: str) -> Dict[str, Any]:
        key = f"dsmeta:{dataset_id}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        data = _http_get_json(f"{self.BASE}/dp/v1/datasets/{dataset_id}")
        self._cache.put(key, data)
        return data


class ReactomeClient:
    BASE = "https://reactome.org/ContentService"

    def __init__(self):
        self._cache = _SessionCache()

    def pathway_members(self, pathway_id: str) -> Dict[str, Any]:
        key = f"reactome:{pathway_id}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        url = f"{self.BASE}/data/participants/{pathway_id}"
        data = _http_get_json(url)
        self._cache.put(key, data)
        return data


class KeggClient:
    BASE = "https://rest.kegg.jp"

    def __init__(self):
        self._cache = _SessionCache()

    def pathway_members(self, pathway_id: str) -> Dict[str, Any]:
        key = f"kegg:{pathway_id}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        req = urllib.request.Request(f"{self.BASE}/get/{pathway_id}")
        with urllib.request.urlopen(req, timeout=60) as resp:
            text = resp.read().decode("utf-8")
        genes: list[str] = []
        in_genes = False
        for line in text.splitlines():
            if line.startswith("GENE"):
                in_genes = True
                parts = line[4:].strip().split()
                if len(parts) >= 2:
                    genes.append(parts[1].rstrip(";"))
            elif in_genes and line.startswith(" "):
                parts = line.strip().split()
                if len(parts) >= 2:
                    genes.append(parts[1].rstrip(";"))
            elif in_genes:
                break
        result = {"pathway_id": pathway_id, "n_genes": len(genes), "genes": genes}
        self._cache.put(key, result)
        return result


class StringClient:
    BASE = "https://string-db.org/api"

    def __init__(self):
        self._cache = _SessionCache()

    def interactions(self, gene_symbol: str, species_tax_id: str = "9606", score_min: float = 0.7) -> Dict[str, Any]:
        key = f"string:{species_tax_id}:{gene_symbol}:{score_min}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        params = {
            "identifiers": gene_symbol,
            "species": species_tax_id,
            "required_score": int(score_min * 1000),
        }
        url = f"{self.BASE}/json/network?{urllib.parse.urlencode(params)}"
        data = _http_get_json(url)
        result = {"gene": gene_symbol, "n_interactions": len(data) if isinstance(data, list) else 0, "interactions": data}
        self._cache.put(key, result)
        return result


class OpenTargetsClient:
    BASE = "https://api.platform.opentargets.org/api/v4/graphql"

    def __init__(self):
        self._cache = _SessionCache()

    def disease_associations(self, gene_symbol: str) -> Dict[str, Any]:
        key = f"ot:{gene_symbol}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        query = (
            "query($sym:String!){ search(queryString:$sym, entityNames:[\"target\"]){ hits{ id name } } }"
        )
        body = json.dumps({"query": query, "variables": {"sym": gene_symbol}}).encode("utf-8")
        req = urllib.request.Request(
            self.BASE,
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": "sc-agent/1.0"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        self._cache.put(key, data)
        return data


class QuickGoClient:
    BASE = "https://www.ebi.ac.uk/QuickGO/services"

    def __init__(self):
        self._cache = _SessionCache()

    def annotations(self, gene_symbol: str, species_tax_id: str = "9606", ontology: str = "molecular_function") -> Dict[str, Any]:
        key = f"quickgo:{species_tax_id}:{gene_symbol}:{ontology}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        url = (
            f"{self.BASE}/annotation/search?geneProductId={gene_symbol}"
            f"&taxonId={species_tax_id}&aspect={ontology}&limit=100"
        )
        data = _http_get_json(url, headers={"Accept": "application/json"})
        self._cache.put(key, data)
        return data


def build_default_api_clients() -> Dict[str, Any]:
    return {
        "ensembl": EnsemblClient(),
        "jaspar": JasparClient(),
        "cellxgene": CellxGeneClient(),
        "reactome": ReactomeClient(),
        "kegg": KeggClient(),
        "string": StringClient(),
        "opentargets": OpenTargetsClient(),
        "quickgo": QuickGoClient(),
    }
