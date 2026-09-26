"""Version parity between the adapter package and its bundled skills.

Release automation rewrites ``pyproject.toml`` and ``__init__.py`` but has no
built-in way to patch the YAML frontmatter of a bundled ``SKILL.md``, so a skill
version silently lags behind the adapter that ships it. These tests turn that
drift into a CI failure instead of a release-time surprise.
"""

import re
from pathlib import Path

import pytest
import yaml

from dcc_mcp_marvelous_designer import __version__ as ADAPTER_VERSION

PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src" / "dcc_mcp_marvelous_designer"
SKILLS_ROOT = PACKAGE_ROOT / "skills"

FRONTMATTER_PATTERN = re.compile(r"\A---\r?\n(.*?)\r?\n---[ \t]*\r?\n", re.DOTALL)


def bundled_skill_dirs():
    """Every bundled skill directory that ships a ``SKILL.md``."""
    if not SKILLS_ROOT.is_dir():
        return []
    return sorted(path for path in SKILLS_ROOT.iterdir() if (path / "SKILL.md").is_file())


def read_frontmatter(skill_md):
    """Parse the leading ``---`` fenced YAML block of a skill manifest."""
    text = skill_md.read_text(encoding="utf-8")
    match = FRONTMATTER_PATTERN.match(text)
    assert match, "%s has no YAML frontmatter block" % skill_md
    document = yaml.safe_load(match.group(1))
    assert isinstance(document, dict), "%s frontmatter is not a mapping" % skill_md
    return document


def skill_version(skill_md):
    metadata = read_frontmatter(skill_md).get("metadata") or {}
    dcc_mcp = metadata.get("dcc-mcp") or {}
    return dcc_mcp.get("version")


def test_bundled_skills_are_discovered():
    names = [path.name for path in bundled_skill_dirs()]
    assert names, "no bundled SKILL.md found under %s" % SKILLS_ROOT


@pytest.mark.parametrize("skill_dir", bundled_skill_dirs(), ids=lambda path: path.name)
def test_skill_version_matches_adapter(skill_dir):
    skill_md = skill_dir / "SKILL.md"
    version = skill_version(skill_md)
    assert version, "%s is missing metadata.dcc-mcp.version" % skill_dir.name
    assert isinstance(version, str), (
        "%s declares a non-string version %r; quote it" % (skill_dir.name, version)
    )
    assert version == ADAPTER_VERSION, (
        "%s declares version %r but dcc_mcp_marvelous_designer.__version__ is %r. "
        "Set metadata.dcc-mcp.version to %r in %s."
        % (skill_dir.name, version, ADAPTER_VERSION, ADAPTER_VERSION, skill_md.name)
    )
