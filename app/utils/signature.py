"""Extract error signatures from pytest/log output for comparison."""

from __future__ import annotations

import re


def extract_error_signature_from_output(text: str) -> str:
    """Best-effort: find a ``TypeError: ...`` or ``Exception: ...`` line.

    Strips pytest's ``E   `` prefix so minimization can match log signatures.
    """
    err_rx = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:Error|Exception):\s*.+")
    for line in text.splitlines():
        s = line.strip()
        s = re.sub(r"^E\s+", "", s)
        if err_rx.match(s):
            return s
    return ""


def signatures_consistent(log_sig: str, output_sig: str) -> bool:
    if not output_sig:
        return False
    lo = output_sig.lower()
    ll = log_sig.lower() if log_sig else ""
    if "typeerror" in lo and "typeerror" in ll:
        if ("offset-naive" in lo or "offset-aware" in lo) and (
            "naive" in ll or "aware" in ll or "offset" in ll
        ):
            return True
        return True
    if not log_sig:
        return False
    return output_sig[:80] in log_sig or log_sig[:80] in output_sig
