"""Discover and explicitly load local runtime coaching skills."""

import re
from pathlib import Path

import frontmatter
from pydantic import ValidationError

from endurance_coach.domain.models import LoadedSkill, SkillMetadata

_SAFE_SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MAX_SKILL_NAME_LENGTH = 64


class SkillFormatError(ValueError):
    """Report an invalid runtime skill without exposing its instructions."""


class SkillLoader:
    """Discover skill metadata and load full instructions only on request."""

    def __init__(self, skills_directory: Path | str) -> None:
        self.skills_directory = Path(skills_directory)

    def discover(self) -> list[SkillMetadata]:
        """Return valid metadata from immediate child skill directories.

        Missing roots produce an empty collection. Invalid skills and paths that
        escape the configured root are excluded so one malformed installation
        cannot prevent the remaining skills from being discovered.

        Returns:
            Valid skill metadata in stable directory-name order.
        """
        root = self._resolved_root()
        if root is None:
            return []

        skills: list[SkillMetadata] = []
        try:
            entries = sorted(root.iterdir(), key=lambda path: path.name)
        except OSError:
            return []

        for entry in entries:
            if not self._is_safe_name(entry.name):
                continue
            try:
                skill_file = self._contained_skill_file(root, entry.name)
                metadata, _ = self._read_skill(skill_file, entry.name)
            except (FileNotFoundError, OSError, SkillFormatError):
                continue
            skills.append(metadata)
        return skills

    def load_skill(self, name: str) -> LoadedSkill:
        """Load one named skill's validated metadata and Markdown instructions.

        Args:
            name: Exact safe name of an immediate child skill directory.

        Returns:
            The selected skill including its instruction body.

        Raises:
            ValueError: If the requested name or skill document is invalid.
            FileNotFoundError: If the root or requested skill does not exist, or
                if its path escapes the configured root.
        """
        if not self._is_safe_name(name):
            raise ValueError(f"unsafe skill name: {name!r}")

        root = self._resolved_root()
        if root is None:
            raise FileNotFoundError(f"skill not found: {name}")
        try:
            skill_file = self._contained_skill_file(root, name)
            metadata, instructions = self._read_skill(skill_file, name)
            return LoadedSkill(**metadata.model_dump(), instructions=instructions)
        except (FileNotFoundError, OSError) as exc:
            raise FileNotFoundError(f"skill not found: {name}") from exc

    def _resolved_root(self) -> Path | None:
        try:
            root = self.skills_directory.resolve(strict=True)
        except (FileNotFoundError, OSError):
            return None
        return root if root.is_dir() else None

    @staticmethod
    def _is_safe_name(name: str) -> bool:
        return (
            len(name) <= _MAX_SKILL_NAME_LENGTH
            and _SAFE_SKILL_NAME.fullmatch(name) is not None
        )

    @staticmethod
    def _contained_skill_file(root: Path, name: str) -> Path:
        candidate = root / name / "SKILL.md"
        try:
            resolved = candidate.resolve(strict=True)
        except (FileNotFoundError, OSError) as exc:
            raise FileNotFoundError(name) from exc
        if not resolved.is_relative_to(root) or not resolved.is_file():
            raise FileNotFoundError(name)
        return resolved

    @staticmethod
    def _read_skill(path: Path, expected_name: str) -> tuple[SkillMetadata, str]:
        try:
            document = frontmatter.load(path)
            metadata = SkillMetadata(
                name=document.metadata.get("name"),
                description=document.metadata.get("description"),
            )
        except (OSError, TypeError, ValidationError) as exc:
            raise SkillFormatError(f"invalid skill document: {expected_name}") from exc
        except Exception as exc:
            # YAML parser failures do not share a stable public exception type.
            raise SkillFormatError(f"invalid skill document: {expected_name}") from exc

        if metadata.name != expected_name:
            raise SkillFormatError(f"skill name does not match directory: {expected_name}")
        instructions = document.content.strip()
        if not instructions:
            raise SkillFormatError(f"skill instructions are empty: {expected_name}")
        return metadata, instructions
