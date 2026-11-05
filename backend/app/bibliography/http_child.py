"""Bounded, fixed-host metadata transport; parent enforces a total wall-clock deadline."""

import base64
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def main():
    try:
        data = json.loads(sys.stdin.buffer.read(8193))
        url = data["url"]
        parsed = urllib.parse.urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in {"api.crossref.org", "api.openalex.org"}
            or parsed.port not in {None, 443}
            or parsed.username
            or parsed.password
            or not parsed.path.startswith("/works/")
        ):
            raise ValueError("Unapproved destination")
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "AcademicIntegrityAI/0.1 (bibliographic metadata verification)",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.build_opener(NoRedirect()).open(req, timeout=3) as response:
                result = {
                    "status": response.status,
                    "retry_after": response.headers.get("Retry-After", "")[:128],
                    "body": base64.b64encode(response.read(262145)).decode("ascii"),
                }
        except urllib.error.HTTPError as error:
            # Never return error bodies or redirect locations, which may echo credentials.
            result = {"status": error.code, "retry_after": error.headers.get("Retry-After", "")[:128], "body": ""}
    except Exception:
        result = {"network_error": True}
    sys.stdout.write(json.dumps(result))


if __name__ == "__main__":
    main()
