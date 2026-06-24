"""A tiny, RUNNABLE record parser — the target the Deep-Tester fuzzes.

DELIBERATELY missing input validation: it assumes every input is well-formed
`key=number`, so malformed input crashes it with an unhandled exception
(robustness / improper-input-validation bug, CWE-20 / CWE-248). The secure twin
validates first and never crashes. DO NOT deploy.
"""


def parse_record(raw):
    parts = raw.split("=")
    key = parts[0]
    value = parts[1]          # IndexError when there is no "="
    return {key: int(value)}  # ValueError when the value is not an integer
