# Add Project Status Summary Endpoint

## Background

Healthchecks (at `/app`) is an open-source cron job monitoring service. Currently
there is no way to get aggregate statistics about a project's checks in a single API
call. Your task is to add a read-only summary endpoint that returns counts by status.

## What You Need to Build

```
GET /api/v1/summary/
```

### Response (200)

```json
{
  "total": 5,
  "up": 2,
  "down": 1,
  "grace": 0,
  "paused": 1,
  "new": 1
}
```

- `total`: total number of checks in the project
- `up`, `down`, `grace`, `paused`, `new`: count of checks in each display status

The status values must come from `check.get_status()` (not the raw `check.status`
field), so `"grace"` (late) checks are counted correctly.

### Auth

Use the existing `@authorize_read` decorator so both read-only and read-write API
keys can access this endpoint.

### No query parameters required.

## Files to Modify

1. `hc/api/views.py` — add `project_summary` view
2. `hc/api/urls.py` — add route to `api_urls`

## Codebase Hints

- `@authorize_read` is already imported and used on `get_checks()` — follow the same pattern
- `Check.objects.filter(project=request.project)` to get all checks
- `check.get_status()` returns one of: `"up"`, `"down"`, `"grace"`, `"paused"`, `"new"`
- Look at `get_checks()` in `hc/api/views.py` for how to query and iterate checks
- Add the route to `api_urls` in `hc/api/urls.py`
