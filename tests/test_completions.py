"""
Tests for Metaflow client tab-completion fixes.

Verifies the acceptance criteria from Issue #4:
  - task.data.<tab> shows artifact names  (MetaflowData.__dir__)
  - Metaflow()["<tab> shows flow names    (Metaflow._ipython_key_completions_)
  - Existing autocomplete still works     (MetaflowObject._ipython_key_completions_)

These tests use pure unit mocks — no live Metaflow backend is required.
"""
import sys
import types
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

# Helpers to build lightweight fakes without touching the real Metaflow store

def _make_artifact(name, value=None):
    """Return a minimal DataArtifact-like mock."""
    art = MagicMock()
    art.id = name
    art.data = value
    return art

def _make_metaflow_data(*names):
    """Return a real MetaflowData instance populated with fake artifacts."""
    from metaflow.client.core import MetaflowData

    artifacts = [_make_artifact(n) for n in names]
    return MetaflowData(artifacts)

def _make_flow(flow_id):
    """Return a minimal Flow-like mock."""
    flow = MagicMock()
    flow.id = flow_id
    return flow

# MetaflowData.__dir__  —  task.data.<tab>

class TestMetaflowDataDir(unittest.TestCase):
    """task.data.<tab> must list artifact names (Issue #4, gap 1)."""

    def test_artifact_names_appear_in_dir(self):
        data = _make_metaflow_data("accuracy", "model", "raw_df")
        names = dir(data)
        self.assertIn("accuracy", names)
        self.assertIn("model", names)
        self.assertIn("raw_df", names)

    def test_standard_object_attrs_still_present(self):
        """Standard dunder attributes must not be dropped."""
        data = _make_metaflow_data("x")
        names = dir(data)
        # dir() always includes at least these on any object
        for attr in ("__class__", "__dict__", "__doc__"):
            self.assertIn(attr, names, f"{attr!r} missing from dir()")

    def test_empty_data_dir_is_valid(self):
        data = _make_metaflow_data()
        self.assertIsInstance(dir(data), list)

    def test_no_duplicates(self):
        data = _make_metaflow_data("a", "b")
        names = dir(data)
        self.assertEqual(len(names), len(set(names)))

    def test_dot_access_still_works(self):
        """Attribute access via dot notation must still be functional."""
        from metaflow.client.core import MetaflowData

        art = _make_artifact("score", 0.99)
        data = MetaflowData([art])
        self.assertEqual(data.score, 0.99)

    def test_contains_still_works(self):
        data = _make_metaflow_data("loss")
        self.assertIn("loss", data)
        self.assertNotIn("nonexistent", data)

# Metaflow._ipython_key_completions_  —  Metaflow()["<tab>

class TestMetaflowKeyCompletions(unittest.TestCase):
    """Metaflow()['<tab> must list visible flow names (Issue #4, gap 2)."""

    def _metaflow_instance_with_flows(self, *flow_ids):
        """
        Build a Metaflow() instance whose __iter__ yields fake flows,
        without touching any metadata backend.
        """
        from metaflow.client.core import Metaflow

        flows = [_make_flow(fid) for fid in flow_ids]
        instance = Metaflow.__new__(Metaflow)
        # Patch __iter__ on the instance's class copy to avoid global side-effects
        instance.__class__ = type(
            "PatchedMetaflow",
            (Metaflow,),
            {"__iter__": lambda self: iter(flows)},
        )
        return instance

    def test_flow_names_returned(self):
        mf = self._metaflow_instance_with_flows("TrainFlow", "EvalFlow")
        completions = mf._ipython_key_completions_()
        self.assertIn("TrainFlow", completions)
        self.assertIn("EvalFlow", completions)

    def test_returns_list(self):
        mf = self._metaflow_instance_with_flows("MyFlow")
        result = mf._ipython_key_completions_()
        self.assertIsInstance(result, list)

    def test_empty_namespace_returns_empty_list(self):
        mf = self._metaflow_instance_with_flows()
        self.assertEqual(mf._ipython_key_completions_(), [])

    def test_only_flow_ids_returned(self):
        """Completions must be strings (flow IDs), not Flow objects."""
        mf = self._metaflow_instance_with_flows("FlowA", "FlowB")
        for item in mf._ipython_key_completions_():
            self.assertIsInstance(item, str)

# MetaflowObject._ipython_key_completions_  —  existing completions (PR #1348)

class TestMetaflowObjectKeyCompletions(unittest.TestCase):
    """
    Existing bracket-completion on Flow/Run/Step/Task must still work.
    Verifies that the MetaflowObject base already has _ipython_key_completions_.
    """

    def test_metaflow_object_has_method(self):
        from metaflow.client.core import MetaflowObject
        self.assertTrue(
            hasattr(MetaflowObject, "_ipython_key_completions_"),
            "MetaflowObject must have _ipython_key_completions_",
        )

    def test_method_returns_child_ids(self):
        from metaflow.client.core import MetaflowObject

        child_a, child_b = MagicMock(id="1"), MagicMock(id="2")

        obj = MetaflowObject.__new__(MetaflowObject)
        obj.__class__ = type(
            "PatchedMFObj",
            (MetaflowObject,),
            {"_filtered_children": lambda self, tags=None: iter([child_a, child_b])},
        )
        result = obj._ipython_key_completions_()
        self.assertIn("1", result)
        self.assertIn("2", result)


if __name__ == "__main__":
    unittest.main()

