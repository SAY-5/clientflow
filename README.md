# ClientFlow

A runtime-configurable rules and workflow engine. Business rules are stored
as data in Postgres, not as code, so non-technical users can change the logic
through a web UI without a redeploy.

A rule is a set of conditions over the fields of an input payload mapped to
actions. ClientFlow evaluates a payload against the active rule set and returns
which rules fired, the actions applied and the resulting payload.

## Parts

- `backend/` Python REST API (FastAPI) with the typed rule model, the
  evaluator, validation and Postgres storage.
- `web/` React and TypeScript rule builder (Vite). Compose conditions and
  actions, see the active rule set and run a test input.

## How it works

A rule set is a JSON document:

```json
{
  "name": "orders",
  "input_schema": {
    "fields": [
      { "name": "amount", "type": "number" },
      { "name": "country", "type": "string" }
    ]
  },
  "rules": [
    {
      "id": "high_value_order",
      "condition": {
        "kind": "group",
        "op": "and",
        "nodes": [
          { "kind": "comparison", "field": "amount", "op": "gte", "value": 1000 },
          { "kind": "comparison", "field": "country", "op": "in", "value": ["US", "CA"] }
        ]
      },
      "actions": [{ "type": "flag", "target": "review", "value": true }]
    }
  ]
}
```

The condition is a typed tree of comparisons and AND/OR groups. The evaluator
walks the tree node by node. It never calls `eval` or `exec` on rule content,
and any field access or comparison that cannot be performed safely returns
false for that node, so no input can crash evaluation.

## Safety and correctness

- The evaluator interprets a typed condition tree. There is no execution of
  user supplied strings as code.
- A rule set is validated before it can go active: conditions are type checked
  against the declared input schema, malformed rules are rejected with a clear
  message, and cycles in rule chaining are detected so a self triggering set
  cannot loop forever.
- Postgres access uses parameterized queries only.

## Versioning and dry-run

Every save creates a new version. Old versions are retained and an active
pointer records which version is live. Activation switches the pointer
atomically; the previous version stays retrievable. A dry-run evaluates a
stored candidate version against sample inputs without changing the active
version.

## Run locally

```bash
docker compose up --build
```

The UI is served on `http://localhost:5173` and the API on
`http://localhost:8000`. To run the parts directly:

```bash
# backend
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload

# web
cd web
npm install
npm run dev
```

## Tests

```bash
cd backend && pytest            # unit, property and storage tests
cd web && npm run test          # component and builder tests
```

## How this differs

ClientFlow is a runtime-configurable no-code rules engine: the rules are data
authored and edited at runtime by non-technical users, evaluated by a safe
typed interpreter, with versioning and dry-run. This is distinct from a fixed
intake or risk pipeline such as `govgate`, where the stages are defined in
code and changing the logic means changing the program. Here the logic lives
in the database and can change without touching the codebase.

## License

MIT, see [LICENSE](LICENSE).
