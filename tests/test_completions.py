"""
Tests for Metaflow client tab-completion fixes.

Covers:
  - MetaflowData.__dir__ → artifact discovery
  - Metaflow._ipython_key_completions_ → flow discovery
  - Existing MetaflowObject completions remain intact
"""

import unittest
from unittest.mock import MagicMock

# Helper Builders

def _make_artifact(name, value=None):
    art = MagicMock()
    art.id = name
    art.data = value
    return art

def _make_metaflow_data(*names):
    from metaflow.client.core import MetaflowData
    artifacts = [_make_artifact(n) for n in names]
    return MetaflowData(artifacts)


def _make_flow(flow_id):
    flow = MagicMock()
    flow.id = flow_id
    return flow

# MetaflowData.__dir__

class TestMetaflowDataDir(unittest.TestCase):
    """Tests for task.data.<tab> autocompletion."""

    def test_artifact_names_present(self):
        data = _make_metaflow_data("accuracy", "model", "raw_df")
        names = dir(data)

        for name in ("accuracy", "model", "raw_df"):
            self.assertIn(name, names)

    def test_dir_contains_standard_attributes(self):
        data = _make_metaflow_data("x")
        names = dir(data)

        for attr in ("__class__", "__dict__", "__doc__"):
            self.assertIn(attr, names)

    def test_dir_returns_list(self):
        data = _make_metaflow_data()
        self.assertIsInstance(dir(data), list)

    def test_no_duplicate_entries(self):
        data = _make_metaflow_data("a", "b")
        names = dir(data)
        self.assertEqual(len(names), len(set(names)))

    def test_artifact_names_are_strings(self):
        data = _make_metaflow_data("metric")
        names = dir(data)

        for name in names:
            self.assertIsInstance(name, str)

    def test_dot_access_preserved(self):
        from metaflow.client.core import MetaflowData

        art = _make_artifact("score", 0.99)
        data = MetaflowData([art])

        self.assertEqual(data.score, 0.99)

    def test_contains_operator_preserved(self):
        data = _make_metaflow_data("loss")
        self.assertIn("loss", data)
        self.assertNotIn("missing", data)

# Metaflow._ipython_key_completions_

class TestMetaflowKeyCompletions(unittest.TestCase):
    """Tests for Metaflow()['<tab>] flow completion."""

    def _make_instance(self, flows):
        from metaflow.client.core import Metaflow

        instance = Metaflow.__new__(Metaflow)

        # Safe override of iterator
        def _iter(_self):
            return iter(flows)

        instance.__class__ = type(
            "PatchedMetaflow",
            (Metaflow,),
            {"__iter__": _iter},
        )
        return instance

    def test_returns_flow_ids(self):
        flows = [_make_flow("TrainFlow"), _make_flow("EvalFlow")]
        mf = self._make_instance(flows)

        result = mf._ipython_key_completions_()

        self.assertIn("TrainFlow", result)
        self.assertIn("EvalFlow", result)

    def test_returns_list(self):
        mf = self._make_instance([_make_flow("A")])
        self.assertIsInstance(mf._ipython_key_completions_(), list)

    def test_empty_returns_empty_list(self):
        mf = self._make_instance([])
        self.assertEqual(mf._ipython_key_completions_(), [])

    def test_all_items_are_strings(self):
        flows = [_make_flow("Flow1"), _make_flow("Flow2")]
        mf = self._make_instance(flows)

        for item in mf._ipython_key_completions_():
            self.assertIsInstance(item, str)

    def test_duplicate_ids_handled(self):
        flows = [_make_flow("Same"), _make_flow("Same")]
        mf = self._make_instance(flows)

        result = mf._ipython_key_completions_()

        # Should not crash; duplicates allowed but should be valid strings
        self.assertTrue(all(isinstance(x, str) for x in result))

# Existing functionality

class TestMetaflowObjectKeyCompletions(unittest.TestCase):
    """Ensure existing completion logic is untouched."""

    def test_method_exists(self):
        from metaflow.client.core import MetaflowObject

        self.assertTrue(
            hasattr(MetaflowObject, "_ipython_key_completions_")
        )

    def test_returns_child_ids(self):
        from metaflow.client.core import MetaflowObject

        child1 = MagicMock(id="1")
        child2 = MagicMock(id="2")

        obj = MetaflowObject.__new__(MetaflowObject)

        obj.__class__ = type(
            "PatchedMFObject",
            (MetaflowObject,),
            {
                "_filtered_children": lambda self, tags=None: iter(
                    [child1, child2]
                )
            },
        )

        result = obj._ipython_key_completions_()

        self.assertIn("1", result)
        self.assertIn("2", result)
        self.assertTrue(all(isinstance(x, str) for x in result))

# Run tests

if __name__ == "__main__":
    unittest.main()