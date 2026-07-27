import io

import joblib  # type: ignore[import-untyped]
from runscope_api.templates.classification import (
    IrisClassificationParameters,
    execute_classification,
)


def test_iris_template_trains_real_model_and_generates_artifacts() -> None:
    result = execute_classification(
        IrisClassificationParameters(
            n_estimators=20,
            max_depth=4,
            test_size=0.2,
            random_state=7,
        )
    )

    assert set(result.metrics) == {"accuracy", "precision", "recall", "f1"}
    assert all(0 <= value <= 1 for value in result.metrics.values())
    artifacts = {artifact.name: artifact for artifact in result.artifacts}
    assert set(artifacts) == {"model.joblib", "metrics.json", "metrics-chart.svg"}
    assert all(artifact.data for artifact in artifacts.values())
    assert joblib.load(io.BytesIO(artifacts["model.joblib"].data)).__class__.__name__ == (
        "RandomForestClassifier"
    )
