"""Label taxonomy (Foundry spec.md §7.6 / FR-092-093).

A minimal, fixed set of labels: source-system, verdict, severity, exploited
yes/no, and weakness class. A transient in-progress label exists only while a
finding is being worked and is removed before publication.
"""
from __future__ import annotations

from typing import List

from .models import Finding

IN_PROGRESS = "state:in-progress"


def labels_for(finding: Finding) -> List[str]:
    labels = [f"source:{finding.source_system}"]
    if finding.verdict:
        labels.append(f"verdict:{finding.verdict.value}")
    if finding.severity:
        labels.append(f"severity:{finding.severity.value}")
    labels.append("exploited:yes" if finding.exploited else "exploited:no")
    if finding.weakness_class:
        labels.append(f"weakness:{finding.weakness_class}")
    return labels
