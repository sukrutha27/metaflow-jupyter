"""IPython magic commands for Metaflow."""
import json
import re

# Argument parser

def _parse_line(line):
    """Parse %mf_show magic arguments into (flow_name, run_id, step_name, artifact_name).

    Supported syntax forms:
        %mf_show FlowName/RunID/StepName artifact_name   # full pathspec
        %mf_show FlowName/latest/StepName artifact_name  # latest run
        %mf_show latest step.artifact                    # latest run shorthand
        %mf_show step.artifact                           # minimal shorthand

    Returns:
        (flow_name, run_id, step_name, artifact_name)
        flow_name may be None for shorthand forms (latest flow is used).

    Raises:
        ValueError: if the line cannot be parsed.
    """
    line = line.strip()
    if not line:
        raise ValueError("Empty input.")

    # Form 1: FlowName/RunID/StepName artifact_name
    m = re.match(
        r'^([A-Za-z_]\w*)/([A-Za-z0-9_]+)/([A-Za-z_]\w*)\s+([A-Za-z_]\w*)$',
        line,
    )
    if m:
        flow_name, run_id, step_name, artifact_name = m.groups()
        return flow_name, run_id, step_name, artifact_name

    # latest step.artifact
    m = re.match(r'^latest\s+([A-Za-z_]\w*)\.([A-Za-z_]\w*)$', line)
    if m:
        step_name, artifact_name = m.groups()
        return None, "latest", step_name, artifact_name

    # Form 3: step.artifact  (minimal – latest run of most-recent flow)
    m = re.match(r'^([A-Za-z_]\w*)\.([A-Za-z_]\w*)$', line)
    if m:
        step_name, artifact_name = m.groups()
        return None, "latest", step_name, artifact_name

    raise ValueError(
        f"Cannot parse {line!r}.\n"
        "Expected one of:\n"
        "  %mf_show FlowName/RunID/StepName artifact_name\n"
        "  %mf_show FlowName/latest/StepName artifact_name\n"
        "  %mf_show latest step.artifact\n"
        "  %mf_show step.artifact"
    )

# Metaflow Client API artifact fetcher

def _fetch_artifact(flow_name, run_id, step_name, artifact_name):
    """Fetch *artifact_name* from Metaflow using the Client API.

    Args:
        flow_name:     Metaflow flow class name, or None to use the most-recent flow.
        run_id:        Run ID string, or "latest" to use the latest run.
        step_name:     Step name inside the run.
        artifact_name: Name of the artifact on task.data.

    Returns:
        The deserialized artifact value.

    Raises:
        ImportError:    if metaflow is not installed.
        ValueError:     if no flows or runs are found.
        KeyError:       if the step does not exist in the run.
        AttributeError: if the artifact does not exist on task.data.
    """
    try:
        from metaflow import Flow, Metaflow
    except ImportError:
        raise ImportError("metaflow is not installed. Run: pip install metaflow")

    # Resolve flow
    if flow_name is None:
        flows = list(Metaflow())
        if not flows:
            raise ValueError("No Metaflow flows found in the current namespace.")
        flow_obj = flows[0]
        flow_name = flow_obj.id
    else:
        flow_obj = Flow(flow_name)

    # Resolve run
    if run_id == "latest":
        run = flow_obj.latest_run
        if run is None:
            raise ValueError(f"No runs found for flow '{flow_name}'.")
    else:
        run = flow_obj[run_id]

    # Resolve step → task
    try:
        step = run[step_name]
    except KeyError:
        available = [s.id for s in run]
        raise KeyError(
            f"Step '{step_name}' not found in {flow_name}/{run.id}.\n"
            f"Available steps: {available}"
        )

    task = step.task

    # Resolve artifact
    if not hasattr(task.data, artifact_name):
        available = list(task.data._artifacts.keys())
        raise AttributeError(
            f"Artifact '{artifact_name}' not found on step '{step_name}'.\n"
            f"Available artifacts: {available}"
        )

    return getattr(task.data, artifact_name)

# Type-aware renderer

def _render(obj):
    """Display *obj* using the most appropriate renderer available."""
    from IPython.display import display

    # pandas DataFrame → rich HTML table
    try:
        import pandas as pd
        if isinstance(obj, pd.DataFrame):
            display(obj)
            return
    except ImportError:
        pass

    # matplotlib Figure → inline PNG image
    try:
        from matplotlib.figure import Figure
        if isinstance(obj, Figure):
            display(obj)
            return
    except ImportError:
        pass

    # numpy ndarray → shape/dtype summary + small preview
    try:
        import numpy as np
        if isinstance(obj, np.ndarray):
            print(f"ndarray  shape={obj.shape}  dtype={obj.dtype}")
            if obj.ndim == 1:
                display(obj[:10])
            else:
                display(obj[:5, :5])
            return
    except ImportError:
        pass

    # dict / list → formatted JSON
    if isinstance(obj, (dict, list)):
        print(json.dumps(obj, indent=2, default=str))
        return

    # fallback: generic IPython display 
    display(obj)

# Magic implementation

def _mf_show(line):
    """%mf_show — fetch and render a Metaflow artifact inline.

    Usage
    -----
    %mf_show FlowName/RunID/StepName artifact_name
    %mf_show FlowName/latest/StepName artifact_name
    %mf_show latest step.artifact
    %mf_show step.artifact
    """
    try:
        import IPython
    except ImportError:
        print("mf_show: IPython is not installed.")
        return

    ip = IPython.get_ipython()
    if ip is None:
        print("mf_show: not running inside IPython.")
        return

    line = line.strip()
    if not line:
        print(
            "Usage: %mf_show FlowName/RunID/StepName artifact_name\n"
            "       %mf_show FlowName/latest/StepName artifact_name\n"
            "       %mf_show latest step.artifact\n"
            "       %mf_show step.artifact"
        )
        return

    # parse the arguments
    try:
        flow_name, run_id, step_name, artifact_name = _parse_line(line)
    except ValueError as exc:
        print(f"mf_show: {exc}")
        return

    # fetch from Metaflow Client API
    try:
        obj = _fetch_artifact(flow_name, run_id, step_name, artifact_name)
    except ImportError as exc:
        print(f"mf_show: {exc}")
        return
    except (KeyError, AttributeError, ValueError) as exc:
        print(f"mf_show: {exc}")
        return
    except Exception as exc:
        print(f"mf_show: unexpected error fetching artifact — {exc}")
        return

    # render
    try:
        _render(obj)
    except Exception as exc:
        print(f"mf_show: error rendering artifact — {exc}")

# IPython extension entry points

def register_magics(ipython):
    """Register all metaflow-jupyter magics with the IPython instance."""
    ipython.register_magic_function(
        _mf_show,
        magic_kind="line",
        magic_name="mf_show",
    )

try:
    import IPython

    def load_ipython_extension(ip):
        """Register metaflow Jupyter magics."""
        register_magics(ip)

    # Auto-register when metaflow_jupyter is imported inside a live IPython session.
    _ip = IPython.get_ipython()
    if _ip is not None:
        load_ipython_extension(_ip)

except ImportError:
    # IPython not installed → provide stub so imports don't break
    def load_ipython_extension(ip):  # noqa: F811
        pass