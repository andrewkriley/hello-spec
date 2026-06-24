"""Secure twin of the record parser: validates input before using it, so
malformed input is rejected gracefully instead of crashing. The Deep-Tester
finds zero crashes here."""


def parse_record(raw):
    parts = raw.split("=", 1)
    if len(parts) != 2 or not parts[1].isdigit():
        return None                       # validated: no crash on malformed input
    return {parts[0]: int(parts[1])}
