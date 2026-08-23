"""Synthetic training-data generator for the attribution classifier.

Design note (from the spec review): the classifier is trained on synthetic data,
so its calibration is measured against this generator's distribution — stated
plainly here and in the README, not implied to be real-chain calibration.

Rows are produced through the *same* signal feature layer used at inference
(`feature_vector` over a `GraphFacts`), so there is no train/serve skew. Labels
are drawn from an explicit logistic ground truth over the features, which makes
the Bayes-optimal predictor calibrated by construction and gives the calibration
curve real meaning.
"""

from __future__ import annotations

import math
import random

import numpy as np

from app.signals import FEATURE_NAMES, feature_vector
from app.signals.facts import GraphFacts, canonical_pattern_similarity

# Ground-truth weights over [hop, sweep, counterparty, temporal, label, pattern]
# (must line up with FEATURE_NAMES order). Reaching a labeled VASP hot wallet with
# your funds is strong evidence, so `label` and `sweep` dominate; hop distance
# still matters but does not sink an otherwise-clear attribution.
_LATENT_WEIGHTS = [1.5, 2.2, 0.8, 1.0, 2.6, 0.8]
_LATENT_K = 1.5
_LATENT_MID = 1.96

assert len(_LATENT_WEIGHTS) == len(FEATURE_NAMES)


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _sample_facts(rng: random.Random) -> GraphFacts:
    facts = GraphFacts(unknown="0xunknown", vasp_name="Candidate", hot_addresses={"0xhot"})

    # ~30% of candidates are unreachable => no evidence at all.
    if rng.random() < 0.30:
        return facts

    facts.reachable = True
    facts.min_hops = rng.randint(1, 7)
    facts.label_confidence = rng.uniform(0.55, 1.0)
    facts.counterparty_overlap_ratio = rng.random() * rng.random() * 0.6  # skew low

    if rng.random() < 0.55:
        facts.sweep_cluster_size = rng.randint(2, 15)
        facts.near_full_ratio = rng.uniform(0.4, 1.0)
        facts.interval_regularity = rng.uniform(0.3, 0.95)
        facts.temporal_correlation = rng.uniform(0.2, 0.95)
        facts.pattern_similarity = canonical_pattern_similarity(
            facts.near_full_ratio, facts.interval_regularity, facts.sweep_cluster_size
        )
    else:
        facts.temporal_correlation = rng.uniform(0.0, 0.25)

    return facts


def _latent(features: list[float]) -> float:
    return sum(w * f for w, f in zip(_LATENT_WEIGHTS, features, strict=True))


def generate_training_data(
    n: int = 6000, seed: int = 42
) -> tuple[np.ndarray, np.ndarray]:
    """Return (X, y): feature matrix and binary labels."""
    rng = random.Random(seed)
    rows: list[list[float]] = []
    labels: list[int] = []
    for _ in range(n):
        facts = _sample_facts(rng)
        features = feature_vector(facts)
        p = _sigmoid(_LATENT_K * (_latent(features) - _LATENT_MID))
        rows.append(features)
        labels.append(1 if rng.random() < p else 0)
    return np.asarray(rows, dtype=float), np.asarray(labels, dtype=int)
