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
"""Pydantic schemas for request/response models."""

from consensus_engine.schemas.proposal import ExpandedProposal, IdeaInput
from consensus_engine.schemas.registry import (
    SchemaNotFoundError,
    SchemaRegistry,
    SchemaVersion,
    SchemaVersionNotFoundError,
    get_current_schema,
    get_registry,
    get_schema_version,
    list_all_schemas,
    list_schema_versions,
)
from consensus_engine.schemas.review import (
    BlockingIssue,
    Concern,
    DecisionAggregation,
    DecisionEnum,
    DetailedScoreBreakdown,
    MinorityReport,
    PersonaReview,
    PersonaScoreBreakdown,
)

__all__ = [
    "ExpandedProposal",
    "IdeaInput",
    "Concern",
    "BlockingIssue",
    "PersonaReview",
    "DecisionAggregation",
    "DecisionEnum",
    "MinorityReport",
    "PersonaScoreBreakdown",
    "DetailedScoreBreakdown",
    # Schema registry exports
    "SchemaRegistry",
    "SchemaVersion",
    "SchemaNotFoundError",
    "SchemaVersionNotFoundError",
    "get_registry",
    "get_current_schema",
    "get_schema_version",
    "list_all_schemas",
    "list_schema_versions",
]
