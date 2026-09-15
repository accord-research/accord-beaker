# ACCORD Beaker demo script

A short, paste-in-order walkthrough of the `accord` context. Roughly 10 minutes at
full speed with a warm data cache; the first ERA5 fetch can add several minutes if
the Copernicus queue is slow.

## Launch

```bash
cd ~/repos/bmgf/accord-beaker
BEAKER_DEFAULT_CONTEXT=accord .venv/bin/beaker notebook
```

Open <http://localhost:8888>. The **Environment** preview at the top of the page
shows the acmadDL and africas2s versions and which credential files are present.
`~/.cdsapirc` is present on this machine, so ERA5 and every `c3s/*` product work;
ECMWF S2S and IRI products do not.

Call `.venv/bin/beaker` directly rather than `uv run beaker` so uv does not re-sync
the environment under you.

## Prompts

Paste each one into the box at the bottom, wait for the **Agent Running** badge to
clear, then paste the next.

**1. Orientation.** Shows the agent reads its skills and the credential preview
instead of guessing.

```
Which data-provider credentials do I have, and which acmaddl forecast products
can I fetch right now without any more setup? Keep it short.
```

Expect a small table: `~/.cdsapirc` present, the other two missing, and a list
of NMME, CHIRPS and C3S products grouped by what is reachable.

**2. Fetch the predictor.** CFSv2 is an NMME product and needs no credentials.

```
Fetch CFSv2 precipitation hindcasts for MAM over the Horn of Africa
(lat -5 to 15, lon 33 to 48), initialized in February, 1993 to 2016,
shaped for africas2s. Show me the dims and a quick-look map of the
ensemble-mean climatology. Render the figure inline in the notebook cell.
Do not save it to a file and do not try to read the image back.
```

Expect a `(year, member, lat, lon)` DataArray with 24 years, and one inline
map. The agent should use `year_index=True`. If it hands back
`(init_time, lead_time, ...)` instead, ask it to reshape for africas2s.

**3. Fetch the predictand.** ERA5 through CDS. Swap in `obs/chirps-v3-monthly`
if you want a no-credential run; the rest of the script is unchanged.

```
Now fetch the matching ERA5 MAM seasonal-mean precipitation observations
for the same region and years, on a 1 degree grid, as a (year, lat, lon)
array. Confirm the year coordinates line up with the CFSv2 hindcast.
```

Expect a `(year, lat, lon)` array and an explicit statement that the 24 years
match.

**4. Downscale and compare methods.** The core africas2s call.

```
Downscale the CFSv2 hindcast against the ERA5 observations with both BCSD
and CCA under leave-one-year-out cross-validation, and tell me which one
verifies better on RPSS. Use the honest train/predict loop, not to_tercile
on the CV hindcasts.
```

Expect the agent to call `ds.optimize(..., methods=["bcsd", "cca"], cv="loyo")`
or an equivalent manual loop, then report one RPSS per method and name a
winner. This is the longest step, typically two to five minutes.

**5. Produce the forecast and score it.**

```
Using the better method, produce the tercile probability forecast, plot it
inline, and give me the cross-validated RPSS, ROC area for above-normal,
and a one-line reliability summary. Render figures inline; do not save
them and do not read images back.
```

Expect a `(tercile, lat, lon)` forecast, a three-panel or single tercile map,
and a short table of scores. The agent should use `to_tercile_cv` for the
scored hindcasts and `to_tercile` only for the final forecast.

**6. Optional closer.** Shows the agent can carry results out of the notebook.

```
Write the tercile forecast to forecast_mam.nc with a descriptive title,
and the skill report to skill_mam.pdf.
```

## If something looks off

- **Model provider dialog pops up.** The resolved key is empty or wrong. Global
  config is `~/.config/beaker.conf`; its top-level `model_name` and
  `llm_service_token` lines win over any `.env`.
- **Agent seems unaware of acmaddl or africas2s.** The skills are fetched from
  GitHub at session start and a fetch failure is silent. Reload the page once
  you are online, or check `GET /beaker/integrations/<session_id>` returns two
  entries.
- **Figure step fails with `no endpoints support image input`.** The configured
  model has no vision. Keep the "do not read the image back" sentence in the
  plotting prompts, or switch to a vision-capable model.
- **Step 4 is slow or the agent loses the thread.** The README recommends a
  large frontier model. The machine's current default is
  `deepseek/deepseek-v4-flash`; `z-ai/glm-5.2` is set as the OpenRouter
  fallback, and the Anthropic provider entry works too. Change it in the gear
  icon at the bottom left or in `~/.config/beaker.conf`.
