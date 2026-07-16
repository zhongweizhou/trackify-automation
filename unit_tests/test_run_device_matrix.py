"""Unit tests for device-matrix test distribution."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from scripts.run_device_matrix import (
    Device,
    DeviceResult,
    TestCaseResult,
    UNIT_TEST_IGNORE,
    build_assignments,
    extract_collected_nodeids,
    load_change_manifest,
    normalize_pytest_args,
    split_nodeids,
    write_summary,
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

    def test_mobile_matrix_excludes_pytest_unit_directory(self) -> None:
        self.assertEqual(UNIT_TEST_IGNORE, "--ignore=tests/unit")

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

    def test_replicate_records_selected_subset_on_every_device(self) -> None:
        nodeids = ["tests/test_suite.py::test_one", "tests/test_suite.py::test_two"]

        assignments = build_assignments(
            [_device(0), _device(1)],
            "replicate",
            nodeids,
        )

        self.assertEqual(len(assignments), 2)
        self.assertTrue(
            all(
                assignment.assigned_nodeids == tuple(nodeids)
                for assignment in assignments
            )
        )
        self.assertTrue(
            all(not assignment.deselected_nodeids for assignment in assignments)
        )

    def test_load_change_manifest_validates_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "changes.json"
            path.write_text(
                json.dumps({"schema_version": 1, "runnable": []}),
                encoding="utf-8",
            )

            self.assertEqual(load_change_manifest(path), {
                "schema_version": 1,
                "runnable": [],
            })

            path.write_text(
                json.dumps({"schema_version": 2, "runnable": []}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "unsupported change manifest"):
                load_change_manifest(path)

            path.write_text(
                json.dumps({"schema_version": 1, "runnable": [{}]}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "invalid runnable cases"):
                load_change_manifest(path)

    def test_summary_contains_changed_case_health_by_device(self) -> None:
        nodeid = "tests/step_defs/example.py::test_changed_case"
        results = []
        for index, status in enumerate(("PASSED", "FAILED")):
            device = _device(index)
            results.append(
                DeviceResult(
                    environment="preprod",
                    platform=device.platform,
                    device_name=device.name,
                    device_udid=device.udid,
                    os_version=device.os_version,
                    target_type=device.target_type,
                    status=status,
                    exit_code=0 if status == "PASSED" else 1,
                    tests=1,
                    passed=1 if status == "PASSED" else 0,
                    failures=0 if status == "PASSED" else 1,
                    errors=0,
                    skipped=0,
                    duration_seconds=1.0,
                    log_path="pytest.log",
                    junit_path="junit.xml",
                    allure_results="allure-results",
                    screenshots="screenshots",
                    assigned_nodeids=[nodeid],
                    cases=[
                        TestCaseResult(
                            name="test_changed_case",
                            classname="tests.step_defs.example",
                            status=status,
                            duration_seconds=1.0,
                            message="",
                        )
                    ],
                )
            )

        manifest = {
            "schema_version": 1,
            "runnable": [
                {
                    "kind": "modified",
                    "test_case_id": "TC_EXAMPLE_001",
                    "title": "Changed case",
                    "nodeid": nodeid,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            run_root = Path(directory)

            write_summary(
                run_root,
                datetime.now().astimezone(),
                results,
                None,
                "replicate",
                manifest,
            )

            markdown = (run_root / "summary.md").read_text(encoding="utf-8")
            payload = json.loads(
                (run_root / "summary.json").read_text(encoding="utf-8")
            )
            self.assertIn("## Changed Case Health", markdown)
            self.assertIn("TC_EXAMPLE_001", markdown)
            self.assertIn("| PASSED | FAILED |", markdown)
            self.assertEqual(
                payload["changed_cases"][0]["test_case_id"],
                "TC_EXAMPLE_001",
            )


if __name__ == "__main__":
    unittest.main()
