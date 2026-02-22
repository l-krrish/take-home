#!/bin/bash
set -e
cd /app

# 1. Add notes field to model, CheckDict, and to_dict()
python3 - << 'PYEOF'
with open("hc/api/models.py", "r") as f:
    content = f.read()

# Add notes to CheckDict (after desc)
content = content.replace(
    "    desc: str\n",
    "    desc: str\n    notes: str\n"
)

# Add notes model field after desc field
content = content.replace(
    "    desc = models.TextField(blank=True)\n",
    "    desc = models.TextField(blank=True)\n    notes = models.TextField(blank=True, default=\"\")\n"
)

with open("hc/api/models.py", "w") as f:
    f.write(content)
print("Step 1a done: field + CheckDict added")
PYEOF

# 2. Add notes to to_dict() inside the else (not readonly) block
python3 - << 'PYEOF'
with open("hc/api/models.py", "r") as f:
    content = f.read()

# Insert notes after channels_str() line inside the else block
content = content.replace(
    '            result["channels"] = self.channels_str()\n',
    '            result["channels"] = self.channels_str()\n            result["notes"] = self.notes\n'
)

with open("hc/api/models.py", "w") as f:
    f.write(content)
print("Step 2 done: to_dict() notes added in else block")
PYEOF

# 3. Add notes to Spec and to the _update() key loop
python3 - << 'PYEOF'
with open("hc/api/views.py", "r") as f:
    content = f.read()

# Add notes to Spec after desc field (must be Optional like other fields in the key loop)
content = content.replace(
    '    desc: str | None = None\n',
    '    desc: str | None = None\n    notes: str | None = None\n'
)

# Add notes to the generic key loop in _update()
content = content.replace(
    '        "desc",\n',
    '        "desc",\n        "notes",\n'
)

with open("hc/api/views.py", "w") as f:
    f.write(content)
print("Step 3 done: Spec and _update() key loop updated")
PYEOF

# 4. Add the check_notes view
cat >> hc/api/views.py << 'PYEOF'


@authorize
def check_notes(request: ApiRequest, code: UUID) -> HttpResponse:
    try:
        check = Check.objects.get(code=code, project=request.project)
    except Check.DoesNotExist:
        return HttpResponseNotFound()

    if request.method == "GET":
        return JsonResponse({"notes": check.notes})

    if request.method == "POST":
        body = request.json if hasattr(request, "json") and request.json else {}
        if "notes" not in body:
            return JsonResponse({"error": "notes field is required"}, status=400)
        if not isinstance(body["notes"], str):
            return JsonResponse({"error": "notes must be a string"}, status=400)
        check.notes = body["notes"]
        check.save(update_fields=["notes"])
        return JsonResponse({"notes": check.notes})

    return JsonResponse({"error": "method not allowed"}, status=405)
PYEOF

# 5. Add URL route
python3 - << 'PYEOF'
import re
with open("hc/api/urls.py", "r") as f:
    content = f.read()

new_route = '    path("checks/<uuid:code>/notes/", views.check_notes),\n'
content = re.sub(
    r'(api_urls\s*=\s*\[.*?)(^\])',
    lambda m: m.group(1) + new_route + ']',
    content,
    flags=re.DOTALL | re.MULTILINE,
)
with open("hc/api/urls.py", "w") as f:
    f.write(content)
print("Step 5 done: URL route added")
PYEOF

# 6. Migration
python manage.py makemigrations api --name="add_check_notes" > /dev/null 2>&1
python manage.py migrate > /dev/null 2>&1
echo "All done."
