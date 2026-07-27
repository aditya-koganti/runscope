import io
import json
from dataclasses import dataclass

import joblib  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split


class IrisClassificationParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n_estimators: int = Field(
        default=100,
        ge=10,
        le=500,
        description="Number of trees in the trusted random-forest classifier.",
    )
    max_depth: int = Field(
        default=6,
        ge=1,
        le=30,
        description="Maximum tree depth.",
    )
    test_size: float = Field(
        default=0.2,
        ge=0.1,
        le=0.5,
        description="Fraction of Iris examples reserved for evaluation.",
    )
    random_state: int = Field(
        default=42,
        ge=0,
        le=2_147_483_647,
        description="Seed for deterministic splitting and model fitting.",
    )


@dataclass(frozen=True)
class GeneratedArtifact:
    name: str
    mime_type: str
    data: bytes


@dataclass(frozen=True)
class TemplateResult:
    metrics: dict[str, float]
    logs: list[tuple[str, str]]
    artifacts: list[GeneratedArtifact]


def metrics_chart_svg(metrics: dict[str, float]) -> bytes:
    width, height = 640, 300
    bar_width = 95
    gap = 45
    bars = []
    labels = []
    for index, (name, value) in enumerate(metrics.items()):
        x = 45 + index * (bar_width + gap)
        bar_height = max(0.0, min(1.0, value)) * 210
        y = 245 - bar_height
        bars.append(
            f'<rect x="{x}" y="{y:.2f}" width="{bar_width}" height="{bar_height:.2f}" '
            'rx="5" fill="#64d7b3"/>'
        )
        labels.append(
            f'<text x="{x + bar_width / 2:.1f}" y="270" text-anchor="middle" '
            f'fill="#d8e2ef" font-size="14">{name}</text>'
        )
        labels.append(
            f'<text x="{x + bar_width / 2:.1f}" y="{max(20, y - 8):.1f}" '
            f'text-anchor="middle" fill="#d8e2ef" font-size="13">{value:.3f}</text>'
        )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="Classification metrics">'
        '<rect width="100%" height="100%" fill="#111a28"/>'
        '<line x1="35" y1="245" x2="610" y2="245" stroke="#42536a"/>'
        + "".join(bars + labels)
        + "</svg>"
    )
    return svg.encode()


def execute_classification(parameters: IrisClassificationParameters) -> TemplateResult:
    dataset = load_iris()
    features_train, features_test, target_train, target_test = train_test_split(
        dataset.data,
        dataset.target,
        test_size=parameters.test_size,
        random_state=parameters.random_state,
        stratify=dataset.target,
    )
    model = RandomForestClassifier(
        n_estimators=parameters.n_estimators,
        max_depth=parameters.max_depth,
        random_state=parameters.random_state,
        n_jobs=1,
    )
    model.fit(features_train, target_train)
    predictions = model.predict(features_test)
    metrics = {
        "accuracy": float(accuracy_score(target_test, predictions)),
        "precision": float(
            precision_score(target_test, predictions, average="weighted", zero_division=0)
        ),
        "recall": float(
            recall_score(target_test, predictions, average="weighted", zero_division=0)
        ),
        "f1": float(f1_score(target_test, predictions, average="weighted", zero_division=0)),
    }
    model_buffer = io.BytesIO()
    joblib.dump(model, model_buffer)
    metrics_json = json.dumps(metrics, indent=2, sort_keys=True).encode()
    return TemplateResult(
        metrics=metrics,
        logs=[
            ("INFO", "Loaded the built-in scikit-learn Iris dataset"),
            (
                "INFO",
                f"Trained random forest on {len(features_train)} examples; "
                f"evaluating {len(features_test)} examples",
            ),
            ("INFO", "Evaluation and artifact generation completed"),
        ],
        artifacts=[
            GeneratedArtifact(
                name="model.joblib",
                mime_type="application/octet-stream",
                data=model_buffer.getvalue(),
            ),
            GeneratedArtifact(
                name="metrics.json",
                mime_type="application/json",
                data=metrics_json,
            ),
            GeneratedArtifact(
                name="metrics-chart.svg",
                mime_type="image/svg+xml",
                data=metrics_chart_svg(metrics),
            ),
        ],
    )
