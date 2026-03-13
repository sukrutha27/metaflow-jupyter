"""IPython magic commands for Metaflow."""

def register_magics(ipython):
    """Register all metaflow-jupyter magics with the IPython instance."""
    ipython.register_magic_function(
        _mf_show,
        magic_kind="line",
        magic_name="mf_show",
    )


try:
    import IPython
    from IPython.display import display

    def _render(obj):
        """Display *obj* using the most appropriate renderer available."""

        # Support pandas DataFrame
        try:
            import pandas as pd
            if isinstance(obj, pd.DataFrame):
                display(obj)
                return
        except ImportError:
            pass

        # Support NumPy arrays
        try:
            import numpy as np
            if isinstance(obj, np.ndarray):
                display(obj)
                return
        except ImportError:
            pass

        # Support Matplotlib figures
        try:
            import matplotlib.figure
            if isinstance(obj, matplotlib.figure.Figure):
                display(obj)
                return
        except ImportError:
            pass

        # Fallback renderers
        if hasattr(obj, "plot"):
            obj.plot()
        else:
            display(obj)

    def _mf_show(line):
        """Display a Metaflow artifact inline in the current notebook cell."""
        ip = IPython.get_ipython()
        if ip is None:
            print("mf_show: not running inside IPython")
            return

        line = line.strip()
        if not line:
            print("Usage: %mf_show <expression>")
            return

        try:
            _render(ip.ev(line))
        except Exception as exc:  
            print("mf_show: could not evaluate %r: %s" % (line, exc))

    def load_ipython_extension(ip):
        """Register metaflow Jupyter magics."""
        register_magics(ip)

    # Auto-register when Metaflow is imported inside a running IPython session.
    _ip = IPython.get_ipython()
    if _ip is not None:
        load_ipython_extension(_ip)

except ImportError:
    # IPython not installed → provide stub
    def load_ipython_extension(ip):
        pass