# src/zero_agent/skills/loader.py
"""Skills loader for loading skill definitions from filesystem."""

import json
import os
import re
from pathlib import Path
from typing import Any


class SkillLoader:
    """Load Skills from filesystem.

    Skills are Markdown files with frontmatter and content.
    Later paths have higher priority (project overrides global).
    """

    def __init__(self, skill_paths: list[str]):
        self.skill_paths = skill_paths
        self.skills: dict[str, dict[str, Any]] = {}

    def load_all(self) -> None:
        """Load skills from all configured paths."""
        for path in self.skill_paths:
            expanded = Path(os.path.expanduser(path))
            if expanded.exists() and expanded.is_dir():
                self._load_from_dir(expanded)

    def _load_from_dir(self, directory: Path) -> None:
        """Load all .md files from directory."""
        for file in directory.glob("*.md"):
            self._load_file(file)

    def _load_file(self, file: Path) -> None:
        """Load single skill file."""
        try:
            content = file.read_text()
            parsed = self._parse_skill(content)
            if parsed:
                name = parsed.get("name", file.stem)
                self.skills[name] = parsed
        except Exception as e:
            print(f"Warning: Failed to load skill {file}: {e}")

    def _parse_skill(self, content: str) -> dict[str, Any] | None:
        """Parse skill file content.

        Format:
        ---
        name: skill-name
        description: ...
        trigger:
          keywords: [keyword1, keyword2]
          patterns: ["pattern1", "pattern2"]
        ---
        Skill content...
        """
        # Extract frontmatter
        match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
        if not match:
            return None

        frontmatter = match.group(1)
        body = match.group(2).strip()

        # Parse YAML frontmatter
        metadata = {}
        trigger = {"keywords": [], "patterns": []}

        lines = frontmatter.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                # Handle trigger section
                if key == "trigger":
                    # Parse trigger block
                    i += 1
                    while i < len(lines) and lines[i].startswith("  "):
                        trigger_line = lines[i].strip()
                        if trigger_line.startswith("keywords:"):
                            # Parse keywords list
                            kw_match = re.search(r"\[(.*?)\]", trigger_line)
                            if kw_match:
                                keywords_str = kw_match.group(1)
                                trigger["keywords"] = [
                                    k.strip().strip('"').strip("'")
                                    for k in keywords_str.split(",")
                                    if k.strip()
                                ]
                        elif trigger_line.startswith("patterns:"):
                            # Parse patterns list
                            pt_match = re.search(r"\[(.*?)\]", trigger_line)
                            if pt_match:
                                patterns_str = pt_match.group(1)
                                trigger["patterns"] = [
                                    p.strip().strip('"').strip("'")
                                    for p in patterns_str.split(",")
                                    if p.strip()
                                ]
                        i += 1
                    metadata["trigger"] = trigger
                    continue
                else:
                    metadata[key] = value
            i += 1

        # Set default trigger if not parsed
        if "trigger" not in metadata:
            metadata["trigger"] = trigger

        return {
            "name": metadata.get("name", ""),
            "description": metadata.get("description", ""),
            "trigger": metadata.get("trigger", {"keywords": [], "patterns": []}),
            "content": body,
        }

    def get_skill(self, name: str) -> str:
        """Get specific skill content."""
        skill = self.skills.get(name)
        return skill["content"] if skill else ""

    def get_skill_metadata(self, name: str) -> dict[str, Any] | None:
        """Get skill metadata including trigger."""
        return self.skills.get(name)

    def get_all_skills_prompt(self) -> str:
        """Combine all skills into a prompt."""
        if not self.skills:
            return ""

        parts = []
        for name, skill in self.skills.items():
            parts.append(f"## Skill: {name}\n\n{skill['content']}\n")

        return "\n".join(parts)

    def get_skill_names(self) -> list[str]:
        """Get all loaded skill names."""
        return list(self.skills.keys())

    def get_skills_with_triggers(self) -> list[dict[str, Any]]:
        """Get all skills that have trigger definitions."""
        result = []
        for name, skill in self.skills.items():
            trigger = skill.get("trigger", {})
            if trigger.get("keywords") or trigger.get("patterns"):
                result.append({
                    "name": name,
                    "description": skill.get("description", ""),
                    "trigger": trigger,
                    "content": skill.get("content", ""),
                })
        return result
