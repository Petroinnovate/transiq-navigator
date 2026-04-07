"""
Model Versioning
================
Semantic version parsing, comparison, and auto-incrementing for model lifecycle.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class SemanticVersion:
    """Parsed semantic version: major.minor.patch[-prerelease]."""
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None

    @classmethod
    def parse(cls, version_str: str) -> "SemanticVersion":
        """Parse a version string like '1.2.3' or '1.2.3-rc1'."""
        match = re.match(
            r"^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$", version_str.strip()
        )
        if not match:
            raise ValueError(f"Invalid version: {version_str}")
        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
            prerelease=match.group(4),
        )

    def bump_patch(self) -> "SemanticVersion":
        return SemanticVersion(self.major, self.minor, self.patch + 1)

    def bump_minor(self) -> "SemanticVersion":
        return SemanticVersion(self.major, self.minor + 1, 0)

    def bump_major(self) -> "SemanticVersion":
        return SemanticVersion(self.major + 1, 0, 0)

    def _sort_key(self) -> Tuple[int, int, int, str]:
        # Pre-release versions sort before release
        return (self.major, self.minor, self.patch, self.prerelease or "~")

    def __lt__(self, other: "SemanticVersion") -> bool:
        return self._sort_key() < other._sort_key()

    def __le__(self, other: "SemanticVersion") -> bool:
        return self._sort_key() <= other._sort_key()

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        return f"{base}-{self.prerelease}" if self.prerelease else base


def next_version(current: str, bump: str = "patch") -> str:
    """Compute next version string from current.

    Args:
        current: Current version string (e.g. '1.2.3')
        bump: One of 'patch', 'minor', 'major'
    """
    sv = SemanticVersion.parse(current)
    if bump == "major":
        return str(sv.bump_major())
    elif bump == "minor":
        return str(sv.bump_minor())
    return str(sv.bump_patch())
