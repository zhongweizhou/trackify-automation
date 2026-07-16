"""Unit tests for device-matrix test distribution."""

from __future__ import annotations

import unittest

from scripts.run_device_matrix import (
    Device,
    build_assignments,
    extract_collected_nodeids,
    normalize_pytest_args,
    split_nodeids,
)


def _device(index: int) -> Device:
    return Device(
        platform="Android" if index % 2 == 0 else "iOS",
        name=f"device-{index}",
        udid=f"udid-{index}",
        os_version="1.0",
        target_type="emulator" if index % 2 == 0 else "simulator",
    )


class DeviceMatrixDistributionTests(unittest.TestCase):
    """Verify deterministic, lossless test sharding."""

    def test_normalize_pytest_args_removes_only_leading_separator(self) -> None:
        self.assertEqual(
            normalize_pytest_args(["--", "-m", "smoke"]),
            ["-m", "smoke"],
        )
        self.assertEqual(normalize_pytest_args(["-q"]), ["-q"])

    def test_extract_collected_nodeids_ignores_warnings_and_summary(self) -> None:
        output = """tests/step_defs/a.py::test_one
tests/step_defs/b.py::test_two

7 tests collected in 0.01s
.venv/site-packages/plugin.py:1: PytestWarning
"""
        self.assertEqual(
            extract_collected_nodeids(output),
            [
                "tests/step_defs/a.py::test_one",
                "tests/step_defs/b.py::test_two",
            ],
        )

    def test_seven_tests_are_balanced_four_and_three(self) -> None:
        nodeids = [f"tests/test_suite.py::test_{index}" for index in range(7)]

        shards = split_nodeids(nodeids, 2)

        self.assertEqual([len(shard) for shard in shards], [4, 3])
        self.assertCountEqual([item for shard in shards for item in shard], nodeids)

    def test_more_devices_than_tests_does_not_create_empty_shards(self) -> None:
        nodeids = ["tests/test_suite.py::test_one", "tests/test_suite.py::test_two"]

        shards = split_nodeids(nodeids, 4)

        self.assertEqual(shards, [[nodeids[0]], [nodeids[1]]])

    def test_split_assignments_are_disjoint_and_deselect_the_rest(self) -> None:
        nodeids = [f"tests/test_suite.py::test_{index}" for index in range(7)]

        assignments = build_assignments(
            [_device(0), _device(1)],
            "split",
            nodeids,
        )

        assigned = [
            nodeid
            for assignment in assignments
            for nodeid in assignment.assigned_nodeids or ()
        ]
        self.assertCountEqual(assigned, nodeids)
        self.assertEqual(len(assigned), len(set(assigned)))
        for assignment in assignments:
            self.assertTrue(
                set(assignment.assigned_nodeids or ()).isdisjoint(
                    assignment.deselected_nodeids
                )
            )
            self.assertCountEqual(
                [
                    *(assignment.assigned_nodeids or ()),
                    *assignment.deselected_nodeids,
                ],
                nodeids,
            )

    def test_replicate_assigns_the_full_suite_to_every_device(self) -> None:
        assignments = build_assignments([_device(0), _device(1)], "replicate")

        self.assertEqual(len(assignments), 2)
        self.assertTrue(
            all(assignment.assigned_nodeids is None for assignment in assignments)
        )
        self.assertTrue(
            all(not assignment.deselected_nodeids for assignment in assignments)
        )


if __name__ == "__main__":
    unittest.main()
