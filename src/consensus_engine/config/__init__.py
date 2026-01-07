# Copyright 2025 John Brosnihan
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Config package for consensus engine."""

from consensus_engine.config.personas import (
    APPROVE_THRESHOLD,
    PERSONA_TEMPERATURE,
    PERSONAS,
    REVISE_THRESHOLD,
    PersonaConfig,
    get_all_personas,
    get_persona,
    get_persona_weights,
    validate_persona_weights,
)
from consensus_engine.config.settings import Environment, Settings, get_settings

__all__ = [
    "Settings",
    "Environment",
    "get_settings",
    "PersonaConfig",
    "PERSONAS",
    "PERSONA_TEMPERATURE",
    "APPROVE_THRESHOLD",
    "REVISE_THRESHOLD",
    "validate_persona_weights",
    "get_persona",
    "get_all_personas",
    "get_persona_weights",
]
