import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

from beaker_notebook.lib import BeakerContext

from .agent import AccordAgent

if TYPE_CHECKING:
    from beaker_notebook.kernel import BeakerKernel

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

    compatible_subkernels = ["python3"]

    def __init__(self, beaker_kernel: "BeakerKernel", config: Optional[Dict[str, Any]] = None):
        super().__init__(beaker_kernel, config=config)

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
