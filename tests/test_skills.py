"""The rosetta and deepscale skills reach the agent.

The skills are loaded remotely at runtime, straight from the source repos, so
these split into two groups:

* offline checks on skills.json itself, which run everywhere; and
* `network` checks that fetch the live skills, which prove the agent will
  actually get what it needs. CI runs those on a schedule so upstream drift
  surfaces as a notification rather than as an agent that quietly forgets a
  library exists.
"""

import json
from urllib.parse import urlparse

import pytest

from beaker_notebook.lib.integrations.skill import parse_skill_md
from beaker_notebook.lib.integrations.types import SkillExampleResource, SkillFileResource

EXPECTED_SKILLS = {"rosetta", "deepscale"}


# --------------------------------------------------------------------------
# Offline
# --------------------------------------------------------------------------


def test_skills_file_is_a_list_of_https_urls(skill_sources):
    assert isinstance(skill_sources, list)
    assert len(skill_sources) == len(EXPECTED_SKILLS)
    for source in skill_sources:
        assert isinstance(source, str), "2.0.9 supports only the bare-string entry form"
        parsed = urlparse(source)
        assert parsed.scheme == "https", f"{source} must be https"
        # Beaker appends "SKILL.md" to a directory URL; without the trailing
        # slash it strips the last path segment instead.
        assert source.endswith("/") or source.endswith("SKILL.md"), (
            f"{source} must end in '/' or 'SKILL.md'"
        )


def test_skills_file_covers_both_libraries(skill_sources):
    """Each dependency the context installs should have its skill wired up."""
    for name in EXPECTED_SKILLS:
        assert any(f"/skills/{name}/" in source for source in skill_sources), (
            f"no skills.json entry for {name}"
        )


def test_skills_file_is_formatted(context_dir):
    """Keeps diffs meaningful when a skill is added or a ref is pinned."""
    raw = (context_dir / "skills.json").read_text(encoding="utf-8")
    assert raw == json.dumps(json.loads(raw), indent=2) + "\n"


# --------------------------------------------------------------------------
# Network
# --------------------------------------------------------------------------


@pytest.mark.network
def test_both_skills_load(skill_provider):
    """A skill that fails to fetch is dropped silently, so assert on presence."""
    assert {skill.slug for skill in skill_provider._skills} == EXPECTED_SKILLS


@pytest.mark.network
def test_prompt_advertises_both_skills(skill_provider):
    """What the agent sees is the prompt; an empty one means no skills at all."""
    prompt = skill_provider.prompt
    assert prompt
    for name in EXPECTED_SKILLS:
        assert name in prompt


@pytest.mark.network
@pytest.mark.parametrize("slug", sorted(EXPECTED_SKILLS))
def test_skill_instructions_are_retrievable(skill_provider, slug):
    skill = skill_provider._find_skill_by_slug(slug)
    frontmatter, body = parse_skill_md(
        skill_provider._fetch_file_content(skill, "SKILL.md")
    )
    assert frontmatter["name"] == slug
    assert frontmatter["description"].strip()
    assert body.strip()


@pytest.mark.network
@pytest.mark.parametrize("slug", sorted(EXPECTED_SKILLS))
def test_every_advertised_resource_resolves(skill_provider, slug):
    """Beaker offers the agent every path it finds in SKILL.md.

    A path that does not resolve is not a harmless dead link: the agent sees it
    in `available_resources`, calls `load_skill_resource`, and gets a 404 back.
    """
    skill = skill_provider._find_skill_by_slug(slug)
    advertised = [
        resource.relative_path
        for resource in skill.resources.values()
        if isinstance(resource, SkillFileResource)
    ]
    assert advertised, f"{slug} advertises no reference files"

    unresolvable = []
    for relative_path in advertised:
        try:
            skill_provider._fetch_file_content(skill, relative_path)
        except Exception as exc:  # noqa: BLE001 - collect all failures, not the first
            unresolvable.append(f"{relative_path} ({type(exc).__name__})")
    assert not unresolvable, f"{slug} advertises unreachable resources: {unresolvable}"


@pytest.mark.network
def test_context_exposes_only_its_own_skills():
    """The user's globally-installed skills must not leak into this context.

    Beaker offers every context the skills in ~/.beaker/skills and friends. On a
    machine with a large personal skill library that is both a large permanent
    prompt cost and a retrieval problem -- the agent has to find rosetta and
    deepscale among everything else.
    """
    from accord_beaker.accord_context.context import AccordContext

    context = AccordContext.__new__(AccordContext)  # the property needs no kernel
    exposed = {
        skill.slug
        for provider in context.default_integration_providers
        for skill in getattr(provider, "_skills", [])
    }
    assert exposed == EXPECTED_SKILLS


@pytest.mark.network
def test_global_skills_remain_opt_in(monkeypatch):
    """Suppression is a default, not a hard-coded refusal."""
    from accord_beaker.accord_context.context import AccordContext

    monkeypatch.setattr(AccordContext, "INCLUDE_GLOBAL_SKILLS", True)
    context = AccordContext.__new__(AccordContext)
    exposed = {
        skill.slug
        for provider in context.default_integration_providers
        for skill in getattr(provider, "_skills", [])
    }
    assert EXPECTED_SKILLS <= exposed


@pytest.mark.network
@pytest.mark.xfail(
    strict=False,
    reason=(
        "beaker-notebook 2.0.9 discovers skill examples only for local skills "
        "(SkillIntegrationProvider._discover_examples is gated on source_type). "
        "Reports XPASS once remote example support lands; drop this marker then."
    ),
)
@pytest.mark.parametrize("slug", sorted(EXPECTED_SKILLS))
def test_examples_reach_the_agent(skill_provider, slug):
    """Both skills ship runnable examples; remote loading should surface them."""
    skill = skill_provider._find_skill_by_slug(slug)
    examples = [
        resource
        for resource in skill.resources.values()
        if isinstance(resource, SkillExampleResource)
    ]
    assert examples, f"{slug} exposes no examples to the agent"
