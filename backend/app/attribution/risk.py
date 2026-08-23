"""Risk scoring — independent of VASP attribution.

Computes exposure to sanctioned / mixer / scam entities reachable from the wallet,
weighted by proximity. Deliberately separate from the attribution probability.
"""

from __future__ import annotations

from app.attribution.context_builder import AttributionContext
from app.schemas.risk import RiskIndicator, RiskLevel, RiskResult

# Category -> base severity weight.
_CATEGORY_WEIGHT = {
    "SANCTIONED": 1.0,
    "MIXER": 0.9,
    "SCAM": 0.8,
}


def _level(score: float) -> RiskLevel:
    if score >= 0.75:
        return RiskLevel.CRITICAL
    if score >= 0.50:
        return RiskLevel.HIGH
    if score >= 0.25:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


class RiskScorer:
    def score(self, context: AttributionContext) -> RiskResult:
        # Nearest hop distance to each address across both directions (funds sent
        # to a risky entity, or received from one).
        min_depth: dict[str, int] = {}
        for graph in (context.forward_graph, context.reverse_graph):
            for node in graph.nodes:
                d = min_depth.get(node.address)
                if d is None or node.depth < d:
                    min_depth[node.address] = node.depth

        indicators: list[RiskIndicator] = []
        score = 0.0
        for address, depth in min_depth.items():
            info = context.labels.get(address)
            if info is None:
                continue
            weight = _CATEGORY_WEIGHT.get(info.category)
            if weight is None:
                continue
            contribution = weight / (1.0 + depth)
            score = max(score, contribution)
            indicators.append(
                RiskIndicator(
                    category=info.category,
                    description=(
                        f"Funds are {depth} hop(s) from {info.name} "
                        f"({info.category.lower()})."
                    ),
                    address=address,
                    hops=depth,
                    contribution=round(contribution, 4),
                )
            )
        indicators.sort(key=lambda i: i.contribution, reverse=True)
        return RiskResult(
            wallet=context.unknown,
            score=round(min(score, 1.0), 4),
            level=_level(score),
            indicators=indicators,
        )
