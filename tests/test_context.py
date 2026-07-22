"""The context is wired correctly and installs into Beaker.

These run offline. Nothing here starts a kernel; they check the declarations
Beaker reads at discovery and setup time.
"""

import inspect

import jinja2
import pytest

from accord_beaker.accord_context.agent import AccordAgent
from accord_beaker.accord_context.context import AccordContext

# Procedures the context asks for by name. get_code() raises if one is absent,
# and the calls sit in setup() and generate_preview(), so a rename that misses
# one only shows up when a session starts.
REQUIRED_PROCEDURES = ("setup", "environment")


def test_context_declares_expected_identity():
    assert AccordContext.SLUG == "accord"
    assert AccordContext.AGENT_CLS is AccordAgent
    assert AccordContext.compatible_subkernels == ["python3"]


def test_accord_is_the_context_a_session_opens_on():
    """Installing this package should make `accord` the default context.

    Beaker picks the installed context with the lowest WEIGHT (see
    BeakerKernel.start_default_context) and sorts the dropdown the same way.
    Ties are broken by dict order, so being strictly lower than every other
    installed context is what makes this deterministic.
    """
    from beaker_notebook.lib.context import autodiscover_contexts

    contexts = {
        slug: cls for slug, cls in autodiscover_contexts().items() if cls is not None
    }
    winner = min(contexts.items(), key=lambda item: item[1].WEIGHT)
    assert winner[0] == "accord", (
        f"'{winner[0]}' would load first "
        f"({ {s: c.WEIGHT for s, c in contexts.items()} })"
    )
    others = [c.WEIGHT for s, c in contexts.items() if s != "accord"]
    assert all(AccordContext.WEIGHT < w for w in others), "weight must be strictly lowest"


def test_context_is_discoverable_by_beaker():
    """Beaker finds contexts through entry points written by its build hook.

    This fails when the package is imported but not installed, which is the
    real failure mode: editable installs go stale after the context moves.
    """
    from beaker_notebook.lib.context import autodiscover_contexts

    contexts = autodiscover_contexts()
    assert "accord" in contexts, (
        f"'accord' not registered; found {sorted(contexts)}. "
        "Run `beaker project update` after moving or adding a context."
    )
    assert contexts["accord"] is AccordContext


def test_context_and_agent_carry_prompts():
    """Both docstrings are fed to the LLM, so an empty one is a silent defect."""
    assert AccordContext.__doc__ and AccordContext.__doc__.strip()
    assert AccordAgent.__doc__ and AccordAgent.__doc__.strip()
    for library in ("rosetta", "deepscale"):
        assert library in AccordAgent.__doc__


async def test_system_preamble_is_present_and_specific():
    context = AccordContext.__new__(AccordContext)  # no kernel needed to read it
    preamble = await AccordContext.system_preamble(context)
    assert preamble
    # The shape conventions are the thing the agent most often gets wrong.
    assert "(year, member, lat, lon)" in preamble
    assert "(tercile, lat, lon)" in preamble


@pytest.mark.parametrize("name", REQUIRED_PROCEDURES)
def test_required_procedures_are_registered_for_python3(name):
    """Beaker must actually discover the procedure, not merely have the file.

    get_code() resolves against the discovered set, so a procedure in the wrong
    directory is indistinguishable from a missing one at runtime -- and setup()
    swallows the failure by design.
    """
    procedures = AccordContext.discover_procedures()
    assert name in procedures, f"{name} not discovered; found {sorted(procedures)}"
    assert "python3" in procedures[name]["languages"]


@pytest.mark.parametrize("name", REQUIRED_PROCEDURES)
def test_required_procedures_are_valid_python_and_jinja(context_dir, name):
    """Procedures are Jinja templates rendered before execution.

    A stray brace therefore breaks at session start rather than at import.
    """
    path = context_dir / "procedures" / "python3" / f"{name}.py"
    assert path.is_file(), f"missing procedure: {path}"

    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")
    jinja2.Environment().parse(source)


def test_setup_procedure_tolerates_missing_libraries(context_dir):
    """The preamble must not raise when rosetta or deepscale are absent.

    A forecaster with a partial install should still get a usable notebook.
    Executing it here is the only honest way to check that.
    """
    source = (context_dir / "procedures" / "python3" / "setup.py").read_text(encoding="utf-8")
    namespace: dict = {}
    exec(compile(source, "setup.py", "exec"), namespace)  # noqa: S102 - fixture under test

    assert "xr" in namespace and "np" in namespace
    assert isinstance(namespace["_accord_loaded"], list)
    assert isinstance(namespace["_accord_missing"], dict)
    # Every library is accounted for as either loaded or explained.
    assert set(namespace["_accord_loaded"]) | set(namespace["_accord_missing"]) == {
        "rosetta",
        "deepscale",
    }


def test_environment_procedure_reports_credentials(context_dir):
    """The preview must describe credentials without ever reading them."""
    source = (context_dir / "procedures" / "python3" / "environment.py").read_text(encoding="utf-8")
    namespace: dict = {"_accord_loaded": ["rosetta"], "_accord_missing": {"deepscale": "boom"}}
    exec(compile(source, "environment.py", "exec"), namespace)  # noqa: S102 - fixture under test
    environment = namespace["_accord_environment"]()

    assert set(environment["packages"]) == {"rosetta", "deepscale"}
    assert "~/.cdsapirc" in environment["credentials"]
    for entry in environment["credentials"].values():
        assert set(entry) == {"present", "used_for"}
        assert isinstance(entry["present"], bool)
    assert environment["import_errors"] == {"deepscale": "boom"}
