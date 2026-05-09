# tests/test_skills.py
import pytest
from pathlib import Path
from micro_harness.skills.loader import SkillLoader


def test_skill_loader_load_file(tmp_path):
    """测试加载单个 skill 文件"""
    skill_dir = tmp_path / "skills"
    skill_dir.mkdir()

    skill_file = skill_dir / "test-skill.md"
    skill_file.write_text("""---
name: test-skill
description: A test skill
trigger: when user asks for test
---

You are a test assistant.
Focus on testing.
""")

    loader = SkillLoader([str(skill_dir)])
    loader.load_all()

    assert "test-skill" in loader.skills
    assert "test assistant" in loader.skills["test-skill"]["content"]


def test_skill_loader_get_skill(tmp_path):
    """测试获取 skill 内容"""
    skill_dir = tmp_path / "skills"
    skill_dir.mkdir()

    skill_file = skill_dir / "code-review.md"
    skill_file.write_text("""---
name: code-review
description: Review code
---

You are a code reviewer.
""")

    loader = SkillLoader([str(skill_dir)])
    loader.load_all()

    content = loader.get_skill("code-review")
    assert "code reviewer" in content


def test_skill_loader_multiple_paths(tmp_path):
    """测试多路径加载（项目覆盖全局）"""
    global_dir = tmp_path / "global"
    global_dir.mkdir()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # 全局 skill
    global_skill = global_dir / "common.md"
    global_skill.write_text("""---
name: common
---
Global version
""")

    # 项目 skill（同名，应覆盖）
    project_skill = project_dir / "common.md"
    project_skill.write_text("""---
name: common
---
Project version
""")

    loader = SkillLoader([str(global_dir), str(project_dir)])
    loader.load_all()

    # 项目版本应该覆盖全局版本
    content = loader.get_skill("common")
    assert "Project version" in content


def test_skill_loader_get_all_prompt(tmp_path):
    """测试拼接所有 skills"""
    skill_dir = tmp_path / "skills"
    skill_dir.mkdir()

    (skill_dir / "skill1.md").write_text("""---
name: skill1
---
Content 1
""")
    (skill_dir / "skill2.md").write_text("""---
name: skill2
---
Content 2
""")

    loader = SkillLoader([str(skill_dir)])
    loader.load_all()

    prompt = loader.get_all_skills_prompt()
    assert "Content 1" in prompt
    assert "Content 2" in prompt


def test_skill_loader_missing_skill(tmp_path):
    """测试获取不存在的 skill"""
    loader = SkillLoader([str(tmp_path)])
    loader.load_all()

    content = loader.get_skill("nonexistent")
    assert content == ""
