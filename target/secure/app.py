"""Secure twin of the demo target — the SAME endpoints with CodeGuard controls
applied. Running the engine against this tree yields zero true-positives,
demonstrating that the controls close the findings.

Controls applied (CodeGuard rules in ../../rules):
  - codeguard-0-input-validation-injection: parameterized SQL (no string-built queries)
  - codeguard-0-command-injection: argv form, shell=False
  - codeguard-0-authorization-access-control: ownership check before returning an object
  - codeguard-1-hardcoded-credentials: secret read from the environment
  - constant-time token comparison via hmac.compare_digest (the rule-gap class)
"""
import hmac
import os
import subprocess


# --- tiny shims so this module is self-contained -------------------------
class _Req:
    args = {}
    json = {}


request = _Req()


class _User:
    id = "u-self"


current_user = _User()


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
        return {"owner": "u-self"}


db = _DB()


def forbidden():
    return ("forbidden", 403)


# codeguard-1-hardcoded-credentials: no secret in source; read from env.
API_KEY = os.environ.get("API_KEY", "")


@app.route("/export")
def handle_export():
    # codeguard-0-input-validation-injection: parameterized query.
    user_id = request.args.get("user_id")
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchall()


@app.route("/run")
def run_command():
    # codeguard-0-command-injection: argv form, no shell.
    cmd = request.args.get("cmd")
    return subprocess.run(["/bin/echo", cmd], shell=False)


@app.route("/payment")
def get_payment():
    # codeguard-0-authorization-access-control: ownership check before return.
    payment_id = request.json.get("payment_id")
    payment = db.get(payment_id)
    if payment.get("owner") != current_user.id:
        return forbidden()
    return payment


def check_token(provided, expected):
    # Constant-time comparison closes the CWE-208 rule-gap class.
    return hmac.compare_digest(provided, expected)
