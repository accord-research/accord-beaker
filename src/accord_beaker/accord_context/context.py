import inspect
import logging
from pathlib import Path
from typing import Any, ClassVar, Dict, Optional, TYPE_CHECKING

from beaker_notebook.lib import BeakerContext

from .agent import AccordAgent

if TYPE_CHECKING:
    from beaker_notebook.kernel import BeakerKernel
    from beaker_notebook.lib.integrations.base import BaseIntegrationProvider

logger = logging.getLogger(__name__)


class AccordContext(BeakerContext):
    """
    ACCORD seasonal climate forecasting.

    Pairs the rosetta data-acquisition library with the deepscale downscaling,
    calibration and verification library, and gives the agent the Agent Skills
    published alongside both. Use it to fetch GCM hindcasts and observations,
    build calibrated tercile forecasts, and score them under cross-validation.
    """

    AGENT_CLS = AccordAgent
    SLUG = "accord"

    #: Beaker starts whichever installed context has the lowest weight, and
    #: sorts the context dropdown by it. The built-in DefaultContext is 10, so
    #: anything below that makes this the one a session opens on -- which is the
    #: point of installing this package. Set BEAKER_DEFAULT_CONTEXT=default to
    #: override for a single run without uninstalling.
    WEIGHT = 5

    compatible_subkernels = ["python3"]

    #: Whether to also offer the skills installed in the user's global skill
    #: directories (``~/.beaker/skills``, ``~/.agents/skills``, and the
    #: equivalents beside the notebook). Off by default -- see
    #: :meth:`default_integration_providers`. Flip to True to opt back in.
    INCLUDE_GLOBAL_SKILLS: ClassVar[bool] = False

    def __init__(self, beaker_kernel: "BeakerKernel", config: Optional[Dict[str, Any]] = None):
        super().__init__(beaker_kernel, config=config)

    @property
    def default_integration_providers(self) -> "list[BaseIntegrationProvider]":
        """Drop the globally-installed skills unless explicitly opted in.

        Beaker offers every context the skills it finds in the user's global
        directories, on top of the context's own. For a general-purpose context
        that is the right default. For a focused one it is actively harmful: a
        developer with a large personal skill library hands this agent a hundred
        or more unrelated skills, and every one of their descriptions is
        injected into the system prompt on every session -- measured at ~24k
        tokens on one real machine. The cost is not only the tokens. The agent
        has to pick rosetta and deepscale out of that field, and skills whose
        descriptions overlap on words like "data" or "forecast" are a genuine
        source of wrong turns.

        Builds the provider outright rather than filtering Beaker's list. There
        is no reliable way to tell the two apart in 2.0.9: both get a random
        ``id``, and ``display_name`` is written to the *class* by
        ``BaseIntegrationProvider.__init__`` (``self.__class__.display_name =
        display_name``), so every instance reports whichever name was set last.
        """
        if self.INCLUDE_GLOBAL_SKILLS:
            return list(super().default_integration_providers)

        from beaker_notebook.lib.integrations.skill import SkillIntegrationProvider

        skills_file = Path(inspect.getabsfile(self.__class__)).parent / "skills.json"
        if not skills_file.is_file():
            logger.warning("No skills.json beside %s; the agent will have no skills.", __name__)
            return []
        return [SkillIntegrationProvider("ACCORD Skills", skill_paths=[str(skills_file)])]

    async def setup(self, context_info=None, parent_header=None):
        """Import the ACCORD stack into the subkernel so it is ready to use.

        Failure here is not fatal: the imports are a convenience, and a user
        without cartopy (or without deepscale at all) should still get a working
        notebook rather than a context that refuses to start. The agent can
        always import what it needs itself.
        """
        await super().setup()
        try:
            await self.execute(self.get_code("setup"), parent_header=parent_header or {})
        except Exception:
            logger.warning("ACCORD subkernel preamble failed to run; continuing without it.", exc_info=True)

    async def system_preamble(self) -> Optional[str]:
        """Domain framing cached for the lifetime of the session.

        Deliberately short. The substance lives in the rosetta and deepscale
        skills, which the agent loads on demand -- restating it here would
        occupy context whether or not the session ever touches those libraries.
        """
        return (
            "This notebook is set up for ACCORD seasonal climate forecasting. The subkernel has "
            "already imported `xarray as xr`, `numpy as np`, `rosetta`, and `deepscale as ds` where "
            "each is installed; check the Environment preview for what actually loaded before "
            "assuming a name is bound.\n\n"
            "Canonical array shapes across the two libraries: GCM hindcasts are "
            "`(year, member, lat, lon)`, observations are `(year, lat, lon)`, and tercile forecasts "
            "are `(tercile, lat, lon)` with terciles ordered below/normal/above. `rosetta.fetch(..., "
            "year_index=True)` and `rosetta.assemble(...)` produce exactly the shapes deepscale "
            "consumes.\n\n"
            "Consult the rosetta and deepscale skills before writing code against either library."
        )

    async def generate_preview(self):
        """Show which parts of the ACCORD stack and which credentials are live.

        Missing or misconfigured credentials are the most common reason a
        rosetta fetch fails, and the failure surfaces late -- after a long
        request -- so it is worth showing up front.
        """
        try:
            result = await self.evaluate(self.get_code("environment"))
            environment = result.get("return") or {}
        except Exception:
            logger.warning("Could not generate ACCORD environment preview.", exc_info=True)
            return {}

        return {
            "Environment": {
                "state": {
                    "application/json": environment,
                }
            },
        }
