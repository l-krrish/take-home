#!/bin/bash
set -e
cd /app

# 1. Add bulk_operations view
cat >> hc/api/views.py << 'PYEOF'


@authorize
def bulk_operations(request: ApiRequest) -> HttpResponse:
    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    body = request.json if hasattr(request, "json") and request.json else {}

    # Validate action
    action = body.get("action")
    if action not in ("pause", "resume", "delete"):
        return JsonResponse({"error": "invalid or missing action"}, status=400)

    # Validate checks list
    check_list = body.get("checks")
    if not isinstance(check_list, list) or len(check_list) == 0:
        return JsonResponse({"error": "checks must be a non-empty list"}, status=400)

    # Validate UUIDs
    import uuid as _uuid
    valid_uuids = []
    for item in check_list:
        try:
            valid_uuids.append(str(_uuid.UUID(str(item))))
        except (ValueError, AttributeError):
            return JsonResponse({"error": f"invalid UUID: {item}"}, status=400)

    requested_set = set(valid_uuids)
    found_checks = list(Check.objects.filter(project=request.project, code__in=valid_uuids))
    found_set = {str(c.code) for c in found_checks}
    not_found = list(requested_set - found_set)

    if action == "pause":
        for c in found_checks:
            c.status = "paused"
            c.save(update_fields=["status"])
    elif action == "resume":
        for c in found_checks:
            c.status = "new"
            c.save(update_fields=["status"])
    elif action == "delete":
        for c in found_checks:
            c.delete()

    return JsonResponse({"updated": len(found_checks), "not_found": not_found})
PYEOF

# 2. Add URL route
python3 - << 'PYEOF'
import re
with open("hc/api/urls.py", "r") as f:
    content = f.read()

new_route = '    path("checks/bulk/", views.bulk_operations),\n'
content = re.sub(
    r'(api_urls\s*=\s*\[.*?)(^\])',
    lambda m: m.group(1) + new_route + ']',
    content,
    flags=re.DOTALL | re.MULTILINE,
)
with open("hc/api/urls.py", "w") as f:
    f.write(content)
print("URL route added")
PYEOF

echo "All done."
