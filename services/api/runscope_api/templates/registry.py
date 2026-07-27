from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from runscope_api.templates.classification import (
    IrisClassificationParameters,
    TemplateResult,
    execute_classification,
)
from runscope_api.templates.slow_demo import SlowDemoParameters


@dataclass(frozen=True)
class TemplateDefinition:
    key: str
    name: str
    description: str
    version: str
    parameter_model: type[BaseModel]
    execute: Callable[[Any], TemplateResult] | None

    @property
    def parameter_schema(self) -> dict[str, Any]:
        return self.parameter_model.model_json_schema()

    def validate_parameters(self, values: dict[str, Any]) -> BaseModel:
        return self.parameter_model.model_validate(values)


class TemplateRegistry:
    def __init__(self, definitions: list[TemplateDefinition]) -> None:
        self._definitions = {(item.key, item.version): item for item in definitions}

    def get(self, key: str, version: str) -> TemplateDefinition:
        try:
            return self._definitions[(key, version)]
        except KeyError as exc:
            raise KeyError(f"Unregistered template {key}:{version}") from exc

    def all(self) -> tuple[TemplateDefinition, ...]:
        return tuple(self._definitions.values())


registry = TemplateRegistry(
    [
        TemplateDefinition(
            key="sklearn-iris-classification",
            name="Iris random-forest classification",
            description=(
                "Loads scikit-learn's built-in Iris dataset, performs a stratified "
                "train/test split, trains a trusted random forest, and reports "
                "accuracy, precision, recall, and F1."
            ),
            version="1.0.0",
            parameter_model=IrisClassificationParameters,
            execute=execute_classification,
        ),
        TemplateDefinition(
            key="slow-demonstration",
            name="Slow progress demonstration",
            description=(
                "Runs a bounded, trusted timer workload that records honest progress, "
                "checks for cancellation, and can fail intentionally. It does not "
                "claim to train a model."
            ),
            version="1.0.0",
            parameter_model=SlowDemoParameters,
            execute=None,
        ),
    ]
)
