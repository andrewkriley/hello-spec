"""A legacy sample module. The evaluation config marks ``samples/`` as
out-of-scope, so the Triager records findings here as not-applicable
(FR-051) -- demonstrating scope handling, not a missed bug."""


def legacy_lookup(request, cursor):
    # Would be CWE-89, but this path is out of scope -> not-applicable.
    name = request.args.get("name")
    cursor.execute(f"SELECT * FROM t WHERE n = {name}")
    return cursor.fetchall()
