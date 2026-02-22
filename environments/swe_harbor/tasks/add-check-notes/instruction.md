# Add Private Notes to Checks

## Background

Healthchecks (at `/app`) is an open-source cron job monitoring service. The `Check`
model has a `desc` field for a public description. Your task is to add a separate
private `notes` field for internal team notes, wire it into the API, and add a
dedicated endpoint to get and set it.

## What You Need to Build

### 1. New `notes` field on the `Check` model

In `hc/api/models.py`:
- Field name: `notes`
- Type: `TextField`, `blank=True`, `default=""`
- Add it after the existing `desc` field

Generate and run the migration.

### 2. Include `notes` in `CheckDict` and `to_dict()`

- Add `notes: str` to the `CheckDict` TypedDict
- In `to_dict()`, include `"notes": self.notes` — but ONLY when `readonly=False`
  (never expose notes to read-only API key holders)

### 3. Accept `notes` in the create/update API

The `Spec` pydantic model defines what fields the API accepts. The `_update()`
function applies a `Spec` to a `Check`.

- Add `notes: str = ""` to `Spec`
- In `_update()`, set `check.notes = spec.notes`

### 4. New dedicated endpoint

```
GET  /api/v1/checks/<uuid>/notes/   — return the notes for a check
POST /api/v1/checks/<uuid>/notes/   — replace the notes for a check
```

**GET response (200):**
```json
{"notes": "some internal note text"}
```

**POST request body:**
```json
{"notes": "updated note text"}
```

**POST response (200):**
```json
{"notes": "updated note text"}
```

POST errors:
- Missing `notes` key -> 400 `{"error": "notes field is required"}`
- `notes` is not a string -> 400 `{"error": "notes must be a string"}`
- Unknown check UUID or wrong project -> 404

Both endpoints require the existing `@authorize` decorator.

## Files to Modify

1. `hc/api/models.py` — add field, update `CheckDict`, update `to_dict()`
2. `hc/api/migrations/` — run `python manage.py makemigrations api`
3. `hc/api/views.py` — add `notes` to `Spec`, update `_update()`, add new view
4. `hc/api/urls.py` — add URL route

## Codebase Hints

- `CheckDict` TypedDict is near the top of `hc/api/models.py`
- `to_dict()` on the `Check` model — find where `desc` is serialized and how
  `readonly` is used to gate certain fields
- `Spec` pydantic model is near the top of `hc/api/views.py`
- Look at how `pause` and `resume` are wired in `hc/api/urls.py` for the URL pattern
