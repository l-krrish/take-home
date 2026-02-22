# Add Bulk Operations API

## Background

Healthchecks (at `/app`) is an open-source cron job monitoring service. The existing
API lets users pause, resume, or delete checks one at a time. Your task is to add a
bulk operations endpoint that acts on multiple checks in a single API call.

## What You Need to Build

```
POST /api/v1/checks/bulk/
```

### Request Body

```json
{
  "checks": ["<uuid1>", "<uuid2>"],
  "action": "pause"
}
```

- `checks`: list of check code UUID strings
- `action`: one of `"pause"`, `"resume"`, or `"delete"`

### Response (200)

```json
{
  "updated": 2,
  "not_found": ["<uuid3>"]
}
```

- `updated`: count of checks successfully acted on
- `not_found`: UUIDs that don't exist OR belong to a different project

### Validation Errors (400)

Return `{"error": "<message>"}` for:
- `action` missing or not one of the three valid values
- `checks` missing, not a list, or empty
- Any UUID in `checks` is not a valid UUID format

### Action Semantics

- `pause`: set `check.status = "paused"`, save
- `resume`: set `check.status = "new"`, save
- `delete`: delete the check from the database

Checks from other projects must appear in `not_found` — never act on them.
Partial success is fine: act on found checks, report missing ones.

### Auth

Use the existing `@authorize` decorator. Only POST is allowed (return 405 otherwise).

## Files to Modify

1. `hc/api/views.py` — add `bulk_operations` view
2. `hc/api/urls.py` — add route inside `api_urls`

## Codebase Hints

- Study existing views like `pause()` and `delete_check()` in `hc/api/views.py`
- The `@authorize` decorator populates `request.project` and `request.json`
- `Check.objects.filter(project=request.project, code__in=[...])` for bulk fetch
- Add the URL to `api_urls` list in `hc/api/urls.py`
