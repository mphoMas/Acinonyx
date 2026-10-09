"""Trusted bounded witness transport worker. Never prints credentials or errors."""
import json
import ssl
import sys
import urllib.request

from mas.audit_anchor import strict_json


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


def main():
    try:
        payload = strict_json(sys.stdin.read(16385))
        context = ssl.create_default_context()  # Honors configured CA roots.
        opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=context))
        request = urllib.request.Request(
            payload["url"] + "/v1/checkpoints/" + payload["namespace"],
            data=json.dumps(payload["request"], allow_nan=False).encode(),
            headers={"Authorization": "Bearer " + payload["token"], "Content-Type": "application/json", "Cache-Control": "no-store, no-cache"},
            method="POST",
        )
        with opener.open(request, timeout=payload["timeout"]) as response:
            if response.status != 200:
                raise ValueError("Witness unavailable")
            raw = response.read(4097)
            if len(raw) > 4096:
                raise ValueError("Witness reply too large")
            result = strict_json(raw)
        print(json.dumps(result, allow_nan=False))
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
