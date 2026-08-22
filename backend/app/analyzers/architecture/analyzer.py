"""Architecture analyzer.

Builds the site architecture graph (pages, technologies, third parties,
resources, domains) and produces architecture-level findings.

Deterministic: nodes/edges come directly from crawl data.
"""

import logging
from collections import Counter

from app.analyzers.architecture.technology_detector import detect_technologies
from app.analyzers.base import AnalyzerResult, BaseAnalyzer, ScanContext
from app.analyzers.registry import AnalyzerRegistry

logger = logging.getLogger("wisewebai.analyzers.architecture")


class ArchitectureAnalyzer(BaseAnalyzer):
    name = "architecture"
    category = "ARCHITECTURE"

    async def analyze(self, context: ScanContext) -> AnalyzerResult:
        result = AnalyzerResult()
        result.metrics["page_count"] = len(context.pages)

        if not context.pages:
            result.metrics["status"] = "NO_PAGES"
            return result

        # Graph data (persisted by the orchestrator).
        nodes, edges = self._build_graph(context)
        result.metrics["nodes"] = nodes
        result.metrics["edges"] = edges

        # Findings.
        if len(context.pages) <= 1:
            result.findings.append(
                self.finding(
                    "ARCH_SINGLE_PAGE",
                    "Site appears to consist of a single page",
                    severity="LOW", impact="LOW", effort="LOW",
                    confidence=0.9,
                    description=(
                        "Only one page was discovered. Single-page sites limit "
                        "SEO surface and user navigation depth."
                    ),
                    affected_url=context.base_url,
                )
            )

        external_domains = Counter(r.domain for r in context.resources if r.is_external and r.domain)
        if len(external_domains) >= 8:
            result.findings.append(
                self.finding(
                    "ARCH_MANY_THIRD_PARTIES",
                    f"High number of third-party domains ({len(external_domains)})",
                    severity="MEDIUM", impact="MEDIUM", effort="MEDIUM",
                    confidence=0.85,
                    description=(
                        "The site loads resources from many third-party domains. "
                        "This increases attack surface, page weight and tracking exposure."
                    ),
                    evidence=[self.evidence(
                        "URL", source=context.base_url,
                        value=", ".join(list(external_domains)[:15]),
                        metadata={"count": len(external_domains)},
                    )],
                )
            )

        cdn_count = sum(1 for d in external_domains if "cloudfront" in d or "cdn" in d)
        if cdn_count == 0 and len(context.pages) > 1:
            result.findings.append(
                self.finding(
                    "ARCH_NO_CDN",
                    "No CDN usage detected",
                    severity="INFO", impact="LOW", effort="MEDIUM",
                    confidence=0.6,
                    description=(
                        "No resources appear to be served through a CDN. A CDN can "
                        "improve global latency for static assets."
                    ),
                )
            )

        avg_depth = sum(p.depth for p in context.pages) / max(1, len(context.pages))
        if avg_depth > 2.5:
            result.findings.append(
                self.finding(
                    "ARCH_DEEP_NESTING",
                    "Pages require deep navigation (average depth {:.1f})".format(avg_depth),
                    severity="LOW", impact="LOW", effort="MEDIUM",
                    confidence=0.7,
                    description=(
                        "Discovered pages sit deep in the site hierarchy, which can "
                        "hurt crawlability and user navigation."
                    ),
                )
            )

        return result

    def _build_graph(self, context: ScanContext) -> tuple[list[dict], list[dict]]:
        nodes: list[dict] = []
        edges: list[dict] = []
        node_id: dict[tuple[str, str], str] = {}

        def node_id_for(nkey: tuple[str, str]) -> str:
            if nkey not in node_id:
                nid = f"n{len(node_id)}"
                node_id[nkey] = nid
            return node_id[nkey]

        def add_node(nkey: tuple[str, str], node_type: str, name: str, label: str | None = None,
                     metadata: dict | None = None) -> str:
            nid = node_id_for(nkey)
            nodes.append({
                "key": nid, "node_type": node_type, "name": name,
                "label": label or name, "metadata": metadata or {},
            })
            return nid

        def add_edge(source_key: tuple[str, str], target_key: tuple[str, str], relationship: str) -> None:
            edges.append({
                "source": node_id_for(source_key), "target": node_id_for(target_key),
                "relationship": relationship,
            })

        base_domain_key = ("DOMAIN", context.base_url.split("//")[1].split("/")[0] if "//" in context.base_url else context.base_url)
        base_host = context.base_url.split("//")[1].split("/")[0] if "//" in context.base_url else ""
        base_domain_name = base_host
        base_domain_id = add_node(base_domain_key, "DOMAIN", base_domain_name, "Site domain")

        page_keys = {}
        for page in context.pages:
            key = ("PAGE", page.url)
            pkey = add_node(key, "PAGE", page.url, page.title or page.url,
                            {"status_code": page.status_code, "depth": page.depth})
            page_keys[page.url] = pkey
            add_edge(base_domain_key, key, "HOSTS")

        for tech in context.technologies:
            tkey = ("TECHNOLOGY", tech.name)
            add_node(tkey, "TECHNOLOGY", tech.name, f"{tech.category} Â· {tech.confidence:.0%}",
                     {"category": tech.category, "confidence": tech.confidence})

        resource_domain_counts = Counter(r.domain for r in context.resources if r.domain)
        for domain, count in resource_domain_counts.most_common(20):
            if domain == base_host:
                continue
            dkey = ("THIRD_PARTY", domain)
            add_node(dkey, "THIRD_PARTY", domain, domain, {"resource_count": count})

        # Page -> resource edges (top resources only, bounded).
        for page in context.pages:
            if page.url not in page_keys:
                continue
            for r in page.resources[:15]:
                rkey = ("RESOURCE", r.url)
                add_node(rkey, "RESOURCE", r.url, f"{r.resource_type}: {r.url[:80]}",
                         {"resource_type": r.resource_type, "size_bytes": r.size_bytes})
                add_edge(("PAGE", page.url), rkey, "REFERENCES")
                if r.is_external and r.domain:
                    add_edge(rkey, ("THIRD_PARTY", r.domain), "LOADED_FROM")

        # Deduplicate node entries by key.
        seen_nodes: dict[str, dict] = {}
        for n in nodes:
            seen_nodes[n["key"]] = n
        seen_edges: set[tuple[str, str, str]] = set()
        dedup_edges = []
        for e in edges:
            key = (e["source"], e["target"], e["relationship"])
            if key not in seen_edges:
                seen_edges.add(key)
                dedup_edges.append(e)

        return list(seen_nodes.values()), dedup_edges


AnalyzerRegistry.register(ArchitectureAnalyzer)
