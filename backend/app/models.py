"""Typed rule model.

A rule set is data, not code. Each rule has a condition tree (an
expression over input fields) and a list of actions to apply when the
condition matches. The structures here are plain Pydantic models so a
rule set can be stored in and loaded from Postgres as JSON.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field


class Comparator(StrEnum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    BETWEEN = "between"


class FieldType(StrEnum):
    NUMBER = "number"
    STRING = "string"
    BOOLEAN = "boolean"


class FieldSpec(BaseModel):
    """One input field the rules may reference."""

    name: str
    type: FieldType


class InputSchema(BaseModel):
    """Declares which fields an input payload may contain."""

    fields: list[FieldSpec]

    def field_map(self) -> dict[str, FieldType]:
        return {f.name: f.type for f in self.fields}


class Comparison(BaseModel):
    kind: Literal["comparison"] = "comparison"
    field: str
    op: Comparator
    value: Any = None


class Group(BaseModel):
    kind: Literal["group"] = "group"
    op: Literal["and", "or"]
    nodes: list[Condition]


Condition = Annotated[
    Union[Comparison, "Group"],
    Field(discriminator="kind"),
]

Group.model_rebuild()


class ActionType(StrEnum):
    SET = "set"
    ROUTE = "route"
    FLAG = "flag"


class Action(BaseModel):
    type: ActionType
    target: str
    value: Any = None


class Rule(BaseModel):
    id: str
    description: str = ""
    condition: Condition
    actions: list[Action]
    # Optional fields this rule writes that later rules may read. Used by
    # cycle detection so chained rules cannot loop forever.
    triggers: list[str] = Field(default_factory=list)


class RuleSet(BaseModel):
    name: str
    input_schema: InputSchema
    rules: list[Rule]
