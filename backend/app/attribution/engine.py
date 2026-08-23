"""Attribution engine: assemble calibrated candidates + evidence into a result.

Pure and synchronous — it takes precomputed GraphFacts, so it is trivially unit
tested against the demo scenarios. The DB/graph gathering lives in
context_builder.py.
"""

from __future__ import annotations

from app.attribution.model import AttributionModel
from app.schemas.attribution import AttributionResult, VaspCandidate
from app.signals import SIGNALS, feature_vector
from app.signals.facts import GraphFacts

# How close the top two candidates must be (in probability) to be "ambiguous".
AMBIGUITY_MARGIN = 0.15


class AttributionEngine:
    def __init__(self, model: AttributionModel, threshold: float | None = None) -> None:
        self._model = model
        self._threshold = threshold if threshold is not None else model.threshold

    def _candidate(self, facts: GraphFacts) -> VaspCandidate:
        vec = feature_vector(facts)
        prob = self._model.predict_proba(vec)
        contribs = self._model.contributions(vec)
        evidence = []
        for sig in SIGNALS:
            ev = sig.evidence(facts)
            if ev is None:
                continue
            ev.weight = round(contribs.get(sig.feature_name, 0.0), 4)
            evidence.append(ev)
        evidence.sort(key=lambda e: e.weight, reverse=True)
        return VaspCandidate(
            vasp_name=facts.vasp_name,
            probability=round(prob, 4),
            evidence=evidence,
            hot_wallet=facts.reached_hot,
        )

    def attribute(self, candidate_facts: list[GraphFacts]) -> AttributionResult:
        candidates = [self._candidate(f) for f in candidate_facts]
        candidates.sort(key=lambda c: c.probability, reverse=True)
        return self._decide(candidates)

    def _decide(self, candidates: list[VaspCandidate]) -> AttributionResult:
        thr = self._threshold
        floor = max(thr - 0.10, 0.40)
        version = self._model.model_version

        def result(**kw: object) -> AttributionResult:
            return AttributionResult(
                confidence_threshold=thr, model_version=version, **kw
            )

        if not candidates:
            return result(
                candidates=[],
                insufficient_evidence=True,
                explanation="No labeled VASP was reachable from this wallet within bounds.",
            )

        top = candidates[0]
        if top.probability < floor:
            return result(
                candidates=candidates[:3],
                insufficient_evidence=True,
                explanation=(
                    f"No candidate cleared the confidence floor of {floor:.0%}; the "
                    f"strongest was {top.vasp_name} at {top.probability:.0%}."
                ),
            )

        if len(candidates) >= 2:
            second = candidates[1]
            if (
                second.probability >= floor
                and (top.probability - second.probability) <= AMBIGUITY_MARGIN
            ):
                return result(
                    candidates=[c for c in candidates if c.probability >= floor][:4],
                    ambiguous=True,
                    explanation=(
                        f"Multiple VASPs are plausible and none dominates: "
                        f"{top.vasp_name} ({top.probability:.0%}) vs "
                        f"{second.vasp_name} ({second.probability:.0%})."
                    ),
                )

        if top.probability >= thr:
            return result(
                candidates=[c for c in candidates if c.probability >= floor][:5],
                explanation=(
                    f"Attributed to {top.vasp_name} at {top.probability:.0%} "
                    f"(threshold {thr:.0%})."
                ),
            )

        return result(
            candidates=candidates[:3],
            insufficient_evidence=True,
            explanation=(
                f"Strongest candidate {top.vasp_name} at {top.probability:.0%} did not "
                f"clear the {thr:.0%} confidence threshold."
            ),
        )
