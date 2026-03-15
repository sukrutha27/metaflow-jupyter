"""
pytest configuration: stub Unix-only C modules so that metaflow.client.core
can be imported on Windows (where fcntl, grp, etc. are not available).
"""

import sys
import types


def _stub_unix_modules():
    unix_only = ["fcntl", "grp", "pwd", "resource", "termios", "tty", "pty"]
    for name in unix_only:
        if name not in sys.modules:
            sys.modules[name] = types.ModuleType(name)

    # metaflow.sidecar.sidecar_subprocess uses fcntl at module level; stub the
    # whole submodule so that the sidecar package can be imported cleanly.
    _sidecar_sub = types.ModuleType("metaflow.sidecar.sidecar_subprocess")

    class _SidecarSubProcess:
        pass

    _sidecar_sub.SidecarSubProcess = _SidecarSubProcess
    sys.modules.setdefault(
        "metaflow.sidecar.sidecar_subprocess", _sidecar_sub
    )


_stub_unix_modules()
