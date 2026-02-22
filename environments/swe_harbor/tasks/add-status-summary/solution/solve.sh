#!/bin/bash
set -e
cd /app

# 1. Add project_summary view
cat >> hc/api/views.py << 'PYEOF'


@authorize_read
def project_summary(request: ApiRequest) -> JsonResponse:
    counts = {"up": 0, "down": 0, "grace": 0, "paused": 0, "new": 0}
    checks = Check.objects.filter(project=request.project)
    for check in checks:
        status = check.get_status()
        if status in counts:
            counts[status] += 1
    return JsonResponse({"total": sum(counts.values()), **counts})
PYEOF

# 2. Add URL route
python3 - << 'PYEOF'
import re
with open("hc/api/urls.py", "r") as f:
    content = f.read()

new_route = '    path("summary/", views.project_summary),\n'
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
