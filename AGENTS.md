# Working in accord-beaker

This repo is a Beaker **context package**: a thin Python package whose job is to configure an AI
agent, not to implement climate science. The science lives in `accord-rosetta` and
`accord-deepscale`. Keep it that way — if you find yourself writing forecasting logic here, it
belongs upstream.

## What matters here

**The docstrings are the product.** `AccordAgent.__doc__` and `AccordContext.system_preamble()`
are fed verbatim to the LLM on every session. Edit them as prompts, not as documentation: state
what the agent should do, name the traps it will otherwise fall into, and keep them short —
everything here occupies context whether or not the session needs it. Detail belongs in the
upstream skills, which load on demand.

**Skills are loaded remotely, from `main`.** `skills.json` points at raw GitHub URLs in the
rosetta and deepscale repos. There is no vendored copy. Consequences worth remembering:

- Editing a skill means opening a PR on rosetta or deepscale, not on this repo.
- A skill change is live in every notebook on the next session, with no release here.
- A fetch failure is silent — Beaker logs at debug and returns zero skills. If the agent seems
  unaware of a library, suspect the fetch before suspecting the prompt.
- The trailing `/` on each URL is load-bearing. Without it Beaker strips the last path segment.

**Beaker 2.0.9 is the floor.** The released version is meaningfully behind `dev`. In particular
`SkillIntegrationProvider.from_context` does not exist in 2.0.9 — the equivalent logic is inlined
in `BeakerContext.default_integration_providers`. Check behavior against the installed version, not
against a checkout of `dev`, before concluding something works.

## After changing the context

Beaker finds contexts through entry-point metadata written by its build hook at install time, so
moving or renaming a context silently breaks discovery until you reinstall:

```bash
beaker project update      # or: pip install -e .
beaker context list        # 'accord' must appear
```

`tests/test_context.py::test_context_is_discoverable_by_beaker` catches this.

## Procedures

Files under `procedures/python3/` are Jinja templates rendered before being executed in the
subkernel. Two rules:

- `{{`, `{%` and `{#` are Jinja syntax. Ordinary f-strings are fine; doubled braces are not.
- `setup.py` runs at session start and must never raise. A forecaster with a partial install
  should get a working notebook, not a context that fails to start. Guard every import.

The suite compiles each procedure as Python and parses it as Jinja, and executes `setup.py` to
confirm it tolerates missing libraries.

## Tests

```bash
uv run pytest -m "not network"   # what CI runs on every push
uv run pytest                    # adds live skill fetches
```

Network tests fetch the real skills from GitHub. They run on a daily schedule
(`.github/workflows/skill-health.yml`), which also re-resolves dependencies at their latest
versions, so upstream drift surfaces as a notification rather than as a silently degraded agent. One test is an expected failure — see "Known gaps" in the README.

## Releasing

Nothing is published. This package is consumed from a checkout. If that changes, mirror the
`publish.yml` workflow the sibling repos use, which stamps `0.1.<run number>` and relies on PyPI
Trusted Publishing.
