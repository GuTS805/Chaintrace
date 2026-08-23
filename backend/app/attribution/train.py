"""Train + calibrate the attribution model and persist the artifact.

Run: python -m app.attribution.train  (or `make train`).
Writes models/attribution_model.joblib, attribution_metrics.json, and
calibration_curve.png.
"""

from __future__ import annotations

import json
from pathlib import Path

import structlog

from app.attribution.model import DEFAULT_MODEL_PATH, AttributionModel
from app.config import get_settings
from app.synthetic.training import generate_training_data

log = structlog.get_logger(__name__)


def _plot_calibration(model: AttributionModel, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    curve = model.metrics.calibration_curve
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], "--", color="grey", label="perfectly calibrated")
    ax.plot(
        curve["prob_pred"],
        curve["prob_true"],
        marker="o",
        label=f"{model.method} (Brier={model.metrics.chosen_brier:.3f})",
    )
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed frequency")
    ax.set_title("Attribution model calibration (held-out test)")
    ax.legend(loc="upper left")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main(n: int = 6000, seed: int = 42) -> None:
    settings = get_settings()
    X, y = generate_training_data(n=n, seed=seed)
    model = AttributionModel.train(X, y, seed=seed, threshold=settings.confidence_threshold)
    model_path = model.save()

    metrics_path = DEFAULT_MODEL_PATH.parent / "attribution_metrics.json"
    metrics_path.write_text(json.dumps(model.metrics.as_dict(), indent=2), encoding="utf-8")

    plot_path = DEFAULT_MODEL_PATH.parent / "calibration_curve.png"
    _plot_calibration(model, plot_path)

    m = model.metrics
    log.info(
        "model_trained",
        model_version=model.model_version,
        chosen_method=m.method,
        brier_uncalibrated=round(m.brier_uncalibrated, 4),
        brier_isotonic=round(m.brier_isotonic, 4),
        brier_sigmoid=round(m.brier_sigmoid, 4),
        positive_rate=round(m.positive_rate, 3),
    )
    print(
        f"Saved {model_path.name} (version={model.model_version})\n"
        f"  chosen calibration: {m.method}\n"
        f"  Brier  uncal={m.brier_uncalibrated:.4f}  "
        f"isotonic={m.brier_isotonic:.4f}  sigmoid={m.brier_sigmoid:.4f}\n"
        f"  train/calib/test = {m.n_train}/{m.n_calib}/{m.n_test}  "
        f"pos_rate={m.positive_rate:.3f}"
    )


if __name__ == "__main__":
    main()
