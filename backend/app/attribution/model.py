"""Calibrated attribution classifier.

XGBoost + CalibratedClassifierCV. Both isotonic and sigmoid calibrators are
fitted on a held-out split and the one with the lower Brier score on a separate
test split is kept (isotonic overfits at small N, so we do not hard-commit to it).
Raw XGBoost margins are not calibrated, and we display probabilities to users, so
calibration is required, not optional.

Per-prediction feature contributions come from XGBoost's built-in TreeSHAP
(`pred_contribs`) — exact, and with no extra dependency — and drive the `weight`
on each Evidence object.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import train_test_split
from xgboost import DMatrix, XGBClassifier

from app.signals import FEATURE_NAMES

DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parents[2] / "models" / "attribution_model.joblib"
)


@dataclass
class ModelMetrics:
    method: str
    brier_uncalibrated: float
    brier_isotonic: float
    brier_sigmoid: float
    chosen_brier: float
    positive_rate: float
    n_train: int
    n_calib: int
    n_test: int
    calibration_curve: dict[str, list[float]] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class AttributionModel:
    def __init__(
        self,
        xgb: XGBClassifier,
        calibrator: CalibratedClassifierCV,
        method: str,
        feature_names: list[str],
        threshold: float,
        metrics: ModelMetrics,
        model_version: str,
    ) -> None:
        self._xgb = xgb
        self._calibrator = calibrator
        self.method = method
        self.feature_names = feature_names
        self.threshold = threshold
        self.metrics = metrics
        self.model_version = model_version

    # -- inference -------------------------------------------------------
    def predict_proba(self, features: Sequence[float]) -> float:
        x: Any = np.asarray([features], dtype=float)
        return float(self._calibrator.predict_proba(x)[0, 1])

    def contributions(self, features: Sequence[float]) -> dict[str, float]:
        """Exact per-feature TreeSHAP contributions (log-odds) for this input."""
        dm = DMatrix(np.asarray([features], dtype=float))
        contribs = self._xgb.get_booster().predict(dm, pred_contribs=True)[0]
        # Last column is the bias term; the rest align with feature order.
        return {name: float(c) for name, c in zip(self.feature_names, contribs[:-1], strict=False)}

    # -- training --------------------------------------------------------
    @classmethod
    def train(
        cls,
        X: np.ndarray,
        y: np.ndarray,
        *,
        seed: int = 42,
        threshold: float = 0.55,
    ) -> AttributionModel:
        X_train, X_tmp, y_train, y_tmp = train_test_split(
            X, y, test_size=0.4, random_state=seed, stratify=y
        )
        X_calib, X_test, y_calib, y_test = train_test_split(
            X_tmp, y_tmp, test_size=0.5, random_state=seed, stratify=y_tmp
        )

        xgb = XGBClassifier(
            n_estimators=200,
            max_depth=3,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            reg_lambda=1.0,
            random_state=seed,
            n_jobs=1,
            tree_method="hist",
            eval_metric="logloss",
        )
        xgb.fit(X_train, y_train)

        brier_uncal = brier_score_loss(y_test, xgb.predict_proba(X_test)[:, 1])

        calibrators: dict[str, CalibratedClassifierCV] = {}
        briers: dict[str, float] = {}
        for method in ("isotonic", "sigmoid"):
            # FrozenEstimator: calibrate the already-fitted XGB without refitting it
            # (sklearn 1.6+ replacement for the old cv="prefit").
            cal = CalibratedClassifierCV(FrozenEstimator(xgb), method=method)
            cal.fit(X_calib, y_calib)
            calibrators[method] = cal
            briers[method] = float(
                brier_score_loss(y_test, cal.predict_proba(X_test)[:, 1])
            )

        best_method = min(briers, key=lambda m: briers[m])
        calibrator = calibrators[best_method]

        prob_true, prob_pred = calibration_curve(
            y_test, calibrator.predict_proba(X_test)[:, 1], n_bins=10, strategy="quantile"
        )
        metrics = ModelMetrics(
            method=best_method,
            brier_uncalibrated=float(brier_uncal),
            brier_isotonic=briers["isotonic"],
            brier_sigmoid=briers["sigmoid"],
            chosen_brier=briers[best_method],
            positive_rate=float(np.mean(y)),
            n_train=int(len(y_train)),
            n_calib=int(len(y_calib)),
            n_test=int(len(y_test)),
            calibration_curve={
                "prob_pred": [float(v) for v in prob_pred],
                "prob_true": [float(v) for v in prob_true],
            },
        )
        version = f"phase4-xgb-{best_method}-{len(FEATURE_NAMES)}f"
        return cls(
            xgb, calibrator, best_method, list(FEATURE_NAMES), threshold, metrics, version
        )

    # -- persistence -----------------------------------------------------
    def save(self, path: Path = DEFAULT_MODEL_PATH) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "xgb": self._xgb,
                "calibrator": self._calibrator,
                "method": self.method,
                "feature_names": self.feature_names,
                "threshold": self.threshold,
                "metrics": self.metrics,
                "model_version": self.model_version,
            },
            path,
        )
        return path

    @classmethod
    def load(cls, path: Path = DEFAULT_MODEL_PATH) -> AttributionModel:
        blob = joblib.load(path)
        return cls(
            xgb=blob["xgb"],
            calibrator=blob["calibrator"],
            method=blob["method"],
            feature_names=blob["feature_names"],
            threshold=blob["threshold"],
            metrics=blob["metrics"],
            model_version=blob["model_version"],
        )
