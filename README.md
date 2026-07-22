# accord-beaker

A [Beaker notebook](https://github.com/jataware/beaker-notebook) context for ACCORD seasonal
climate forecasting.

Installing this package adds an **`accord`** context to Beaker. Selecting it gives you a notebook
whose AI agent knows how to drive the two ACCORD libraries:

| Library | Package | Role |
|---|---|---|
| [`rosetta`](https://github.com/accord-research/rosetta) | `accord-rosetta` | Fetch and normalize climate data (NMME, C3S/Copernicus, ERA5, CHIRPS, IMERG, S2S) into canonical xarray Datasets |
| [`deepscale`](https://github.com/accord-research/deepscale) | `accord-deepscale` | Downscale, calibrate, ensemble and verify seasonal forecasts |

The agent learns these libraries from the [Agent Skills](https://agentskills.io/) published in
each library's own repository, loaded over the network at session start. Nothing is duplicated
here — update a skill upstream and every `accord` notebook picks it up on its next session.

## Installation

```bash
pip install accord-beaker
```

Then start Beaker and choose the **accord** context:

```bash
beaker notebook
```

Confirm the context registered:

```bash
beaker context list        # should list 'accord'
```

If this is your first time using Beaker, run `beaker config update` first and set
`LLM_SERVICE_TOKEN` to your provider's API key.

### Installing from a checkout

```bash
git clone https://github.com/accord-research/accord-beaker.git
cd accord-beaker
uv sync --extra dev
```

`rosetta` pulls in `sheerwater`, which hard-pins `zarr==2.18.3` and conflicts with `icechunk`.
This project carries the same `[tool.uv] override-dependencies` rosetta does, so the environment
resolves cleanly under `uv`. Under plain `pip` you may need `pip install 'zarr>=3.1.0'` afterwards.
The pin is stale — sheerwater reads through xarray's zarr backend and works under zarr 3.

## What the context gives you

**Two agent skills.** The agent sees each skill's name and description up front and pulls in the
full instructions only when a task calls for it, so an unrelated session pays almost nothing for
them. Once loaded, it can reach for the skill's reference files — rosetta's product catalog,
deepscale's metric semantics, either library's troubleshooting guide.

**A prepared subkernel.** `xarray as xr`, `numpy as np`, `rosetta` and `deepscale as ds` are
imported when the context starts. Each import is guarded: a partial install degrades to a working
notebook rather than a context that refuses to start.

**An environment preview.** The preview panel shows installed versions, which imports succeeded,
and which of rosetta's three credential files are present — `~/.cdsapirc`, `~/.ecmwfapirc`,
`~/.pycpt_dlauth`. Only presence is reported; contents are never read. A missing credential
otherwise surfaces as a 403 partway through a slow request.

**Shape conventions in the system prompt.** GCM hindcasts are `(year, member, lat, lon)`,
observations `(year, lat, lon)`, tercile forecasts `(tercile, lat, lon)`. These are stated up
front because they are what the agent most often gets wrong.

## How skills are wired

Beaker discovers a context's skills from a `skills.json` sitting next to `context.py`. Ours points
at the upstream repositories:

```json
[
  "https://raw.githubusercontent.com/accord-research/rosetta/main/skills/rosetta/",
  "https://raw.githubusercontent.com/accord-research/deepscale/main/skills/deepscale/"
]
```

Beaker appends `SKILL.md` to each URL and lazily fetches `references/` files off the same base as
the agent asks for them. The trailing slash matters — without it Beaker strips the last path
segment. A skill does **not** need its own repository; a URL pointing into a subdirectory works.

**These URLs track `main` and are not pinned.** That is deliberate: skills stay current without a
release here. The cost is that an upstream change reaches every notebook immediately. To pin,
replace `main` with a tag or commit SHA. The scheduled `skill-health` workflow fetches both skills
daily, so upstream breakage surfaces as a failed run rather than as an agent that quietly stops
mentioning a library.

## Known gaps

**Remote skills do not expose their examples.** Both rosetta and deepscale ship four runnable
example scripts, and the agent currently sees none of them. Beaker's
`SkillIntegrationProvider._discover_examples` is gated on `source_type == "local"`; the code notes
that remote examples "must be declared in the frontmatter (not yet implemented)". Tracked by the
`xfail` in `tests/test_skills.py::test_examples_reach_the_agent`, which flips to XPASS once
upstream support lands. Until then the agent has instructions and reference files but no worked
examples.

**A failed skill fetch is silent.** If GitHub is unreachable, the provider logs at debug level and
returns no skills — the prompt is empty and the agent never learns the libraries exist, with no
user-visible warning. Check the Integrations panel if the agent seems unaware of rosetta or
deepscale.

## Development

```bash
uv run pytest -m "not network"   # offline: wiring, procedures, skills.json
uv run pytest                    # also fetches the live skills
```

After moving or renaming a context, re-run `beaker project update` (or `pip install -e .`) —
Beaker discovers contexts through entry-point metadata written at build time, so an editable
install goes stale when the module moves.

### Layout

```
src/accord_beaker/
└── accord_context/
    ├── context.py            AccordContext: setup, system preamble, environment preview
    ├── agent.py              AccordAgent: the agent's standing instructions
    ├── skills.json           remote skill sources
    └── procedures/python3/
        ├── setup.py          imports run in the subkernel at session start
        └── environment.py    powers the environment preview
```

Procedures are Jinja templates rendered before execution, so the suite checks each one as both
valid Python and valid Jinja.

## License

MIT
