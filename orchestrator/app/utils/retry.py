from __future__ import annotations


BAD_REQUEST_PATTERNS = (
    "bad request",
    "400",
    "invalid_request_error",
    '"detail":"bad request"',
    "'detail': 'bad request'",
    "status code: 400",
    "http 400",
)


def looks_like_bad_request(return_code: int, stdout: str, stderr: str) -> bool:
    if return_code == 0:
        return False
    blob = f"{stdout}\n{stderr}".lower()
    return any(pattern in blob for pattern in BAD_REQUEST_PATTERNS)


def retry_delay_seconds(base_delay: float, attempt: int) -> float:
    safe_base = max(0.1, float(base_delay))
    safe_attempt = max(1, int(attempt))
    return safe_base * safe_attempt
