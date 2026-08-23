"""Model training / calibration / persistence (offline, small)."""

from __future__ import annotations

from pathlib import Path

from app.attribution.model import AttributionModel
from app.signals import FEATURE_NAMES
from app.synthetic.training import generate_training_data


def test_train_predict_and_calibrate() -> None:
    X, y = generate_training_data(n=1500, seed=7)
    model = AttributionModel.train(X, y, seed=7)

    # Chosen calibrator is the lower-Brier of the two.
    assert model.method in {"isotonic", "sigmoid"}
    assert model.metrics.chosen_brier == min(
        model.metrics.brier_isotonic, model.metrics.brier_sigmoid
    )
    # Calibration should not be worse than raw margins by much, and be sane.
    assert 0.0 <= model.metrics.chosen_brier < 0.25
    assert model.metrics.calibration_curve["prob_pred"]


def test_predict_proba_bounds_and_monotonic_signal() -> None:
    X, y = generate_training_data(n=1500, seed=7)
    model = AttributionModel.train(X, y, seed=7)

    strong = [0.5, 1.0, 0.3, 0.9, 1.0, 1.0]  # close, strong sweep, labeled
    weak = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # unreachable / no evidence
    p_strong = model.predict_proba(strong)
    p_weak = model.predict_proba(weak)
    assert 0.0 <= p_weak <= 1.0
    assert 0.0 <= p_strong <= 1.0
    assert p_strong > p_weak


def test_contributions_cover_all_features() -> None:
    X, y = generate_training_data(n=1000, seed=1)
    model = AttributionModel.train(X, y, seed=1)
    contribs = model.contributions([0.33, 1.0, 0.0, 1.0, 0.9, 1.0])
    assert set(contribs) == set(FEATURE_NAMES)


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    X, y = generate_training_data(n=800, seed=3)
    model = AttributionModel.train(X, y, seed=3)
    path = tmp_path / "m.joblib"
    model.save(path)
    loaded = AttributionModel.load(path)
    features = [0.33, 0.8, 0.1, 0.7, 0.9, 0.8]
    assert abs(loaded.predict_proba(features) - model.predict_proba(features)) < 1e-9
    assert loaded.model_version == model.model_version
