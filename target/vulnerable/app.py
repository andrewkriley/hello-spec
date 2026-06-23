"""Deliberately vulnerable demo target for hello-spec.

DO NOT DEPLOY. Every weakness here is intentional: it is the codebase the
Foundry mini-engine scans and the CodeGuard rules detect. The secure twin in
``target/secure/app.py`` implements the same endpoints with the CodeGuard
controls applied, and the engine finds zero true-positives there.

Self-contained shims stand in for Flask/DB so the file parses and imports with
no third-party dependencies (the engine only needs to parse it with `ast`).
"""
import os
import subprocess


# --- tiny shims so this module is self-contained -------------------------
class _Req:
    args = {}
    json = {}


request = _Req()


class _App:
    def route(self, path):
        def deco(fn):
            return fn
        return deco


app = _App()


class _Cursor:
    def execute(self, *a, **k):
        pass

    def fetchall(self):
        return []


cursor = _Cursor()


class _DB:
    def get(self, _id):
        return {}


db = _DB()


# CWE-798: a (fake) hardcoded credential -> secret-scan -> true-positive.
# Deliberately not a real provider key format, so platform secret-scanners do
# not flag this teaching sample; our detector still catches it via the generic
# `api_key = "..."` pattern.
API_KEY = "hs_demo_9f3a2b7c1d5e8004aa17bd33ce41"

# CWE-798: a placeholder default -> secret-scan -> code-quality (not a secret).
DEFAULT_TOKEN = "changeme-please"


@app.route("/export")
def handle_export():
    # CWE-89: user input string-formatted straight into SQL.
    user_id = request.args.get("user_id")
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    return cursor.fetchall()


@app.route("/run")
def run_command():
    # CWE-78: request-controlled command run through a shell.
    cmd = request.args.get("cmd")
    return subprocess.run(cmd, shell=True)


@app.route("/payment")
def get_payment():
    # CWE-639 (IDOR): object fetched by client id with no ownership check.
    payment_id = request.json.get("payment_id")
    return db.get(payment_id)


def check_token(provided, expected):
    # CWE-208: non-constant-time comparison of a secret token. No authored rule
    # covers this class, so the exploratory hunter finds it and a rule-gap is
    # recorded (the rule-gap flywheel).
    return provided == expected


def safe_join(base, untrusted_path):
    # CWE-22 CANDIDATE that is actually SAFE: the containment check after
    # realpath defeats traversal. The Triager investigates and rejects it
    # (false-positive) -- mirrors docs/worked-examples Finding C.
    base_path = os.path.realpath(base)
    candidate = os.path.realpath(os.path.join(base_path, untrusted_path))
    if os.path.commonpath([base_path, candidate]) != base_path:
        raise ValueError("Path traversal attempt")
    return candidate
