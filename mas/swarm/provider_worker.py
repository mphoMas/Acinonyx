"""Private, killable HTTP client subprocess; stdin carries credentials, never argv.

Invoked by absolute filename with Python isolated mode. No legacy gateway import.
"""

import json
import sys
import urllib.error
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not forward an authorization header to a redirected destination."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    stage = "request"
    try:
        job = json.loads(sys.stdin.buffer.read(131073))
        client = urllib.request.build_opener(NoRedirect())
        if job.get("operation") == "models":
            request = urllib.request.Request(job["url"] + "/models", headers={"Authorization": "Bearer " + job["key"]})
            with client.open(request, timeout=job["timeout"]) as response:
                raw = response.read(1048577)
                if len(raw) > 1048576:
                    raise ValueError("Model listing too large")
            result = json.loads(raw)
            models = [item["id"].removeprefix("models/") for item in result["data"]]
            print(json.dumps({"models": models}))
            return 0
        payload = json.dumps(
            {
                "model": job["model"],
                "messages": job["messages"],
                "temperature": 0,
                "max_tokens": job["max_tokens"],
                "response_format": {"type": "json_object"},
            }
        ).encode()
        request = urllib.request.Request(
            job["url"] + "/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + job["key"]},
        )
        # Keep environment proxy and system/session CA trust; never bypass TLS.
        with client.open(request, timeout=job["timeout"]) as response:
            raw = response.read(1048577)
            if len(raw) > 1048576:
                raise ValueError("Upstream response too large")
        stage = "response_json"
        result = json.loads(raw)
        stage = "completion_schema"
        choice = result["choices"][0]
        if choice["finish_reason"] != "stop" or choice["message"].get("tool_calls"):
            stage = "incomplete_completion"
            raise ValueError("Incomplete or tool-calling response")
        print(json.dumps({"content": choice["message"]["content"], "usage": result["usage"]}, allow_nan=False))
        return 0
    except urllib.error.HTTPError as exc:
        print(json.dumps({"error": "http_error", "status": exc.code}))
        return 1
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        # Never return raw HTTP errors, payloads or credentials in diagnostic output.
        print("Provider request failed", file=sys.stderr)
        print(json.dumps({"error": stage}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
