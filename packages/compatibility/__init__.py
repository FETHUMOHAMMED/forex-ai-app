"""Compatibility boundaries used during the incremental refactor."""

from .legacy_v3_shadow import (
    ShadowBrokerAdapter,
    ShadowDecisionAdapter,
    ShadowEnvironment,
    ShadowExecutionAdapter,
    ShadowModeViolation,
    ShadowPersistenceAdapter,
    ShadowPositionManagementAdapter,
    ShadowRiskAdapter,
    ShadowSignalAdapter,
    ShadowSignalSerializationAdapter,
)

__all__ = [
    "ShadowBrokerAdapter",
    "ShadowDecisionAdapter",
    "ShadowEnvironment",
    "ShadowExecutionAdapter",
    "ShadowModeViolation",
    "ShadowPersistenceAdapter",
    "ShadowPositionManagementAdapter",
    "ShadowRiskAdapter",
    "ShadowSignalAdapter",
    "ShadowSignalSerializationAdapter",
]
