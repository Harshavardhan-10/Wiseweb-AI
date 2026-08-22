"""Analyzer registry.

New analyzers register themselves here; scan orchestration only knows
about ``registry.run_all(context)``, so adding an analyzer never requires
rewriting the orchestrator.
"""

import logging
from dataclasses import dataclass

from app.analyzers.base import AnalyzerResult, BaseAnalyzer, ScanContext

logger = logging.getLogger("wisewebai.analyzers.registry")


@dataclass
class AnalyzerRun:
    name: str
    category: str
    status: str
    error: str | None = None
    findings_count: int = 0


class AnalyzerRegistry:
    _analyzers: list[type[BaseAnalyzer]] = []

    @classmethod
    def register(cls, analyzer_cls: type[BaseAnalyzer]) -> type[BaseAnalyzer]:
        if analyzer_cls not in cls._analyzers:
            cls._analyzers.append(analyzer_cls)
        return analyzer_cls

    @classmethod
    def all(cls) -> list[type[BaseAnalyzer]]:
        return list(cls._analyzers)

    @classmethod
    def by_category(cls, category: str) -> list[type[BaseAnalyzer]]:
        return [a for a in cls._analyzers if a.category == category]

    @classmethod
    async def run_all(cls, context: ScanContext) -> tuple[dict[str, AnalyzerResult], list[AnalyzerRun]]:
        """Run every registered analyzer.

        A failure in one analyzer never fails the whole scan: each result is
        recorded individually with its status.
        """
        results: dict[str, AnalyzerResult] = {}
        runs: list[AnalyzerRun] = []
        for analyzer_cls in cls._analyzers:
            analyzer = analyzer_cls()
            category = analyzer.category
            try:
                result = await analyzer.analyze(context)
                for f in result.findings:
                    f.category = category
                results[category] = result
                runs.append(
                    AnalyzerRun(
                        name=analyzer.name, category=category,
                        status=result.status, findings_count=len(result.findings),
                    )
                )
                logger.info(
                    "analyzer %s (%s): %d findings, status=%s",
                    analyzer.name, category, len(result.findings), result.status,
                    extra={"analyzer": analyzer.name, "category": category},
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "analyzer %s (%s) failed: %s", analyzer.name, category, exc,
                    extra={"analyzer": analyzer.name, "category": category, "error": str(exc)},
                )
                results[category] = AnalyzerResult(status="FAILED", error=str(exc))
                runs.append(
                    AnalyzerRun(name=analyzer.name, category=category, status="FAILED", error=str(exc))
                )
        return results, runs
