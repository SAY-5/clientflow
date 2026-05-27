"""REST API for the rules engine."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import db, service
from .models import RuleSet
from .validation import ValidationError


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        db.init_db()
    except Exception:
        # The API can still serve validation and evaluation of supplied
        # rule sets without a database connection.
        pass
    yield


app = FastAPI(title="ClientFlow", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class EvaluateRequest(BaseModel):
    rule_set: RuleSet
    payload: dict[str, Any]


class ActivateRequest(BaseModel):
    version: int


class DryRunRequest(BaseModel):
    version: int
    payload: dict[str, Any]


class RunRequest(BaseModel):
    payload: dict[str, Any]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/evaluate")
def evaluate_endpoint(req: EvaluateRequest) -> dict[str, Any]:
    """Validate and evaluate a rule set in one call without storing it."""
    from .evaluator import evaluate as run_eval

    try:
        from .validation import validate_rule_set

        validate_rule_set(req.rule_set)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return run_eval(req.rule_set, req.payload)


@app.post("/rule-sets")
def create_rule_set(rule_set: RuleSet) -> dict[str, Any]:
    try:
        version = service.save_rule_set(rule_set)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"name": rule_set.name, "version": version}


@app.get("/rule-sets/{name}/versions")
def list_versions(name: str) -> dict[str, Any]:
    return {"name": name, "versions": db.list_versions(name)}


@app.get("/rule-sets/{name}/active")
def get_active(name: str) -> dict[str, Any]:
    rule_set = service.get_active_rule_set(name)
    if rule_set is None:
        raise HTTPException(status_code=404, detail="no active version")
    return {
        "name": name,
        "version": db.active_version_number(name),
        "rule_set": rule_set.model_dump(),
    }


@app.post("/rule-sets/{name}/activate")
def activate(name: str, req: ActivateRequest) -> dict[str, Any]:
    try:
        service.activate(name, req.version)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"name": name, "active_version": req.version}


@app.post("/rule-sets/{name}/run")
def run(name: str, req: RunRequest) -> dict[str, Any]:
    try:
        return service.run_active(name, req.payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/rule-sets/{name}/dry-run")
def dry_run(name: str, req: DryRunRequest) -> dict[str, Any]:
    try:
        return service.dry_run(name, req.version, req.payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
