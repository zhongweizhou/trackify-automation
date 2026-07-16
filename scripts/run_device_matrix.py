"""Run the Trackify pytest suite concurrently across connected devices."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT_ROOT = ROOT / "report" / "device-matrix"
SAFE_NAME = re.compile(r"[^A-Za-z0-9_.-]+")
UNIT_TEST_IGNORE = "--ignore=tests/unit"


@dataclass(frozen=True)
class Device:
    """One Appium target discovered from adb, simctl, or devicectl."""

    platform: str
    name: str
    udid: str
    os_version: str
    target_type: str

    @property
    def key(self) -> str:
        value = f"{self.platform.lower()}-{self.name}-{self.udid}"
        return SAFE_NAME.sub("-", value).strip("-.")


@dataclass
class TestCaseResult:
    """One pytest scenario outcome parsed from JUnit XML."""

    name: str
    classname: str
    status: str
    duration_seconds: float
    message: str


@dataclass
class DeviceResult:
    """Execution totals and artifact paths for one device."""

    environment: str
    platform: str
    device_name: str
    device_udid: str
    os_version: str
    target_type: str
    status: str
    exit_code: int
    tests: int
    passed: int
    failures: int
    errors: int
    skipped: int
    duration_seconds: float
    log_path: str
    junit_path: str
    allure_results: str
    screenshots: str
    assigned_nodeids: list[str] | None
    cases: list[TestCaseResult]


@dataclass(frozen=True)
class DeviceAssignment:
    """A device and the optional test shard assigned to it."""

    device: Device
    assigned_nodeids: tuple[str, ...] | None
    deselected_nodeids: tuple[str, ...] = ()


@dataclass
class RunningDevice:
    """A live pytest subprocess and its output resources."""

    device: Device
    process: subprocess.Popen[str]
    log_handle: object
    started_at: float
    device_dir: Path
    allure_dir: Path
    screenshot_dir: Path
    junit_path: Path
    assigned_nodeids: tuple[str, ...] | None


def _run(command: list[str], timeout: int = 15) -> str:
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return completed.stdout.strip()


def _adb() -> str:
    if executable := shutil.which("adb"):
        return executable
    sdk_root = os.getenv("ANDROID_HOME") or os.getenv("ANDROID_SDK_ROOT")
    if sdk_root:
        candidate = Path(sdk_root) / "platform-tools" / "adb"
        if candidate.exists():
            return str(candidate)
    candidate = Path.home() / "Library" / "Android" / "sdk" / "platform-tools" / "adb"
    return str(candidate) if candidate.exists() else "adb"


def discover_android_devices() -> list[Device]:
    """Return all adb devices in the ready state."""
    adb = _adb()
    try:
        output = _run([adb, "devices", "-l"])
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"[matrix] Android discovery skipped: {exc}", file=sys.stderr)
        return []

    devices: list[Device] = []
    for line in output.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 2 or fields[1] != "device":
            continue
        udid = fields[0]
        details = dict(
            field.split(":", 1) for field in fields[2:] if ":" in field
        )
        try:
            name = _run([adb, "-s", udid, "shell", "getprop", "ro.product.model"])
            os_version = _run(
                [adb, "-s", udid, "shell", "getprop", "ro.build.version.release"]
            )
        except subprocess.SubprocessError as exc:
            print(f"[matrix] Skipping Android {udid}: {exc}", file=sys.stderr)
            continue
        devices.append(
            Device(
                platform="Android",
                name=name or details.get("model", udid),
                udid=udid,
                os_version=os_version or "unknown",
                target_type="emulator",
            )
        )
    return devices


def discover_ios_simulators() -> list[Device]:
    """Return all booted and available iOS simulators."""
    try:
        payload = json.loads(_run(["xcrun", "simctl", "list", "devices", "booted", "--json"]))
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"[matrix] iOS discovery skipped: {exc}", file=sys.stderr)
        return []

    devices: list[Device] = []
    for runtime, runtime_devices in payload.get("devices", {}).items():
        match = re.search(r"\.iOS-(\d+)-(\d+)(?:-(\d+))?$", runtime)
        version = ".".join(part for part in match.groups() if part) if match else "unknown"
        for item in runtime_devices:
            if item.get("state") != "Booted" or not item.get("isAvailable", True):
                continue
            devices.append(
                Device(
                    platform="iOS",
                    name=item.get("name", "iOS Simulator"),
                    udid=item["udid"],
                    os_version=version,
                    target_type="simulator",
                )
            )
    return devices


def discover_ios_real_devices() -> list[Device]:
    """Return paired physical iOS devices known to CoreDevice."""
    with tempfile.TemporaryDirectory() as temporary_dir:
        output_path = Path(temporary_dir) / "devices.json"
        try:
            _run(
                [
                    "xcrun",
                    "devicectl",
                    "list",
                    "devices",
                    "--json-output",
                    str(output_path),
                ]
            )
            payload = json.loads(output_path.read_text(encoding="utf-8"))
        except (
            OSError,
            subprocess.SubprocessError,
            json.JSONDecodeError,
        ) as exc:
            print(f"[matrix] Physical iOS discovery skipped: {exc}", file=sys.stderr)
            return []

    devices: list[Device] = []
    for item in payload.get("result", {}).get("devices", []):
        properties = item.get("deviceProperties", {})
        hardware = item.get("hardwareProperties", {})
        platform = str(hardware.get("platform", "")).lower()
        reality = str(hardware.get("reality", "physical")).lower()
        pairing = str(properties.get("pairingState", "paired")).lower()
        boot_state = str(properties.get("bootState", "booted")).lower()
        developer_services = properties.get("ddiServicesAvailable", True)
        if (
            not platform.startswith("ios")
            or reality != "physical"
            or pairing != "paired"
            or boot_state != "booted"
            or not developer_services
        ):
            continue
        udid = hardware.get("udid") or item.get("identifier")
        if not udid:
            continue
        devices.append(
            Device(
                platform="iOS",
                name=properties.get("name") or hardware.get("marketingName") or udid,
                udid=udid,
                os_version=str(
                    properties.get("osVersionNumber")
                    or properties.get("osBuildUpdate")
                    or "unknown"
                ),
                target_type="real",
            )
        )
    return devices


def discover_devices(platform: str, selected_udids: set[str]) -> list[Device]:
    devices: list[Device] = []
    if platform in {"all", "android"}:
        devices.extend(discover_android_devices())
    if platform in {"all", "ios"}:
        devices.extend(discover_ios_simulators())
        simulator_udids = {device.udid for device in devices}
        devices.extend(
            device
            for device in discover_ios_real_devices()
            if device.udid not in simulator_udids
        )
    if selected_udids:
        devices = [device for device in devices if device.udid in selected_udids]
    return devices


def normalize_pytest_args(pytest_args: list[str]) -> list[str]:
    """Remove argparse's optional separator before forwarding pytest arguments."""
    normalized = list(pytest_args)
    if normalized and normalized[0] == "--":
        normalized.pop(0)
    return normalized


def extract_collected_nodeids(output: str) -> list[str]:
    """Extract ordered pytest node IDs from quiet collection output."""
    nodeids: list[str] = []
    for line in output.splitlines():
        candidate = line.strip()
        if candidate.startswith("tests/") and "::" in candidate:
            nodeids.append(candidate)
    return nodeids


def collect_test_nodeids(args: argparse.Namespace) -> list[str]:
    """Collect the selected pytest tests without creating an Appium session."""
    command = [
        str(args.python),
        "-m",
        "pytest",
        UNIT_TEST_IGNORE,
        *normalize_pytest_args(args.pytest_args),
        "--collect-only",
        "-q",
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"pytest collection failed: {detail}")
    nodeids = extract_collected_nodeids(completed.stdout)
    if not nodeids:
        raise ValueError("pytest collection selected zero tests; nothing can be split.")
    return nodeids


def split_nodeids(nodeids: list[str], shard_count: int) -> list[list[str]]:
    """Distribute node IDs round-robin without creating empty shards."""
    if shard_count < 1:
        raise ValueError("shard_count must be at least 1.")
    if not nodeids:
        raise ValueError("At least one pytest node ID is required.")
    shards = [[] for _ in range(min(shard_count, len(nodeids)))]
    for index, nodeid in enumerate(nodeids):
        shards[index % len(shards)].append(nodeid)
    return shards


def build_assignments(
    devices: list[Device],
    distribution: str,
    nodeids: list[str] | None = None,
) -> list[DeviceAssignment]:
    """Build full-suite or split-suite assignments for the discovered devices."""
    if distribution == "replicate":
        return [DeviceAssignment(device=device, assigned_nodeids=None) for device in devices]
    if nodeids is None:
        raise ValueError("Split distribution requires collected pytest node IDs.")

    shards = split_nodeids(nodeids, len(devices))
    assignments: list[DeviceAssignment] = []
    for device, shard in zip(devices[: len(shards)], shards, strict=True):
        assigned = tuple(shard)
        assigned_set = set(assigned)
        assignments.append(
            DeviceAssignment(
                device=device,
                assigned_nodeids=assigned,
                deselected_nodeids=tuple(
                    nodeid for nodeid in nodeids if nodeid not in assigned_set
                ),
            )
        )
    return assignments


def check_appium(server_url: str) -> None:
    status_url = f"{server_url.rstrip('/')}/status"
    try:
        with urllib.request.urlopen(status_url, timeout=3) as response:
            payload = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Appium is not reachable at {status_url}: {exc}") from exc
    if not payload.get("value", {}).get("ready"):
        raise RuntimeError(f"Appium is not ready at {status_url}: {payload!r}")


def build_environment(
    device: Device,
    args: argparse.Namespace,
    index: int,
    allure_dir: Path,
    screenshot_dir: Path,
) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "PLATFORM": device.platform.lower(),
            "DEVICE_NAME": device.name,
            "DEVICE_UDID": device.udid,
            "OS_VERSION": device.os_version,
            "TEST_ENV": args.environment,
            "APPIUM_SERVER_URL": args.appium_url,
            "ALLURE_RESULTS_DIR": str(allure_dir),
            "SCREENSHOT_DIR": str(screenshot_dir),
            "PYTHONUNBUFFERED": "1",
        }
    )
    if device.platform == "Android":
        environment["APP_PATH"] = str(args.android_app)
        environment["SYSTEM_PORT"] = str(args.android_system_port_base + index)
    else:
        ios_app = args.ios_real_app if device.target_type == "real" else args.ios_app
        environment["APP_PATH"] = str(ios_app)
        environment["IOS_REAL_DEVICE"] = str(device.target_type == "real").lower()
        environment["WDA_LOCAL_PORT"] = str(args.ios_wda_port_base + index)
        environment["MJPEG_SERVER_PORT"] = str(args.ios_mjpeg_port_base + index)
        environment["WDA_DERIVED_DATA_PATH"] = str(
            allure_dir.parent / "wda-derived-data"
        )
    return environment


def start_device(
    assignment: DeviceAssignment,
    args: argparse.Namespace,
    index: int,
    run_root: Path,
) -> RunningDevice:
    device = assignment.device
    device_dir = run_root / device.key
    allure_dir = device_dir / "allure-results"
    screenshot_dir = device_dir / "screenshots"
    junit_path = device_dir / "junit.xml"
    log_path = device_dir / "pytest.log"
    allure_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    pytest_args = normalize_pytest_args(args.pytest_args)
    deselect_args = [
        f"--deselect={nodeid}" for nodeid in assignment.deselected_nodeids
    ]
    command = [
        str(args.python),
        "-m",
        "pytest",
        "-q",
        UNIT_TEST_IGNORE,
        f"--alluredir={allure_dir}",
        f"--junitxml={junit_path}",
        *pytest_args,
        *deselect_args,
    ]
    environment = build_environment(
        device, args, index, allure_dir, screenshot_dir
    )
    log_handle = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env=environment,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    print(
        f"[matrix] START {device.platform} {device.name} "
        f"({device.os_version}, {device.udid}) "
        "tests="
        f"{'all' if assignment.assigned_nodeids is None else len(assignment.assigned_nodeids)} "
        f"pid={process.pid}"
    )
    return RunningDevice(
        device=device,
        process=process,
        log_handle=log_handle,
        started_at=time.monotonic(),
        device_dir=device_dir,
        allure_dir=allure_dir,
        screenshot_dir=screenshot_dir,
        junit_path=junit_path,
        assigned_nodeids=assignment.assigned_nodeids,
    )


def parse_junit(path: Path) -> tuple[dict[str, int | float], list[TestCaseResult]]:
    totals: dict[str, int | float] = {
        "tests": 0,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "time": 0.0,
    }
    if not path.exists():
        return totals, []
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    for suite in suites:
        for key in ("tests", "failures", "errors", "skipped"):
            totals[key] += int(suite.attrib.get(key, 0))
        totals["time"] += float(suite.attrib.get("time", 0.0))

    cases: list[TestCaseResult] = []
    for testcase in root.iter("testcase"):
        outcome = next(
            (
                testcase.find(tag)
                for tag in ("failure", "error", "skipped")
                if testcase.find(tag) is not None
            ),
            None,
        )
        status = outcome.tag.upper() if outcome is not None else "PASSED"
        message = outcome.attrib.get("message", "") if outcome is not None else ""
        cases.append(
            TestCaseResult(
                name=testcase.attrib.get("name", "unknown"),
                classname=testcase.attrib.get("classname", ""),
                status=status,
                duration_seconds=round(float(testcase.attrib.get("time", 0.0)), 3),
                message=" ".join(message.split()),
            )
        )
    return totals, cases


def finish_device(running: RunningDevice, environment: str) -> DeviceResult:
    exit_code = running.process.wait()
    running.log_handle.close()
    elapsed = time.monotonic() - running.started_at
    totals, cases = parse_junit(running.junit_path)
    tests = int(totals["tests"])
    failures = int(totals["failures"])
    errors = int(totals["errors"])
    skipped = int(totals["skipped"])
    passed = max(0, tests - failures - errors - skipped)
    status = "PASSED" if exit_code == 0 else "FAILED"
    result = DeviceResult(
        environment=environment,
        platform=running.device.platform,
        device_name=running.device.name,
        device_udid=running.device.udid,
        os_version=running.device.os_version,
        target_type=running.device.target_type,
        status=status,
        exit_code=exit_code,
        tests=tests,
        passed=passed,
        failures=failures,
        errors=errors,
        skipped=skipped,
        duration_seconds=round(float(totals["time"]) or elapsed, 2),
        log_path=str(running.device_dir / "pytest.log"),
        junit_path=str(running.junit_path),
        allure_results=str(running.allure_dir),
        screenshots=str(running.screenshot_dir),
        assigned_nodeids=(
            list(running.assigned_nodeids)
            if running.assigned_nodeids is not None
            else None
        ),
        cases=cases,
    )
    print(
        f"[matrix] {status} {result.platform} {result.device_name}: "
        f"{passed} passed, {failures} failed, {errors} errors, "
        f"{skipped} skipped in {elapsed:.1f}s"
    )
    return result


def combine_allure_results(
    run_root: Path,
    results: list[DeviceResult],
    distribution: str,
) -> Path:
    combined_dir = run_root / "allure-results"
    combined_dir.mkdir(parents=True, exist_ok=True)
    for result in results:
        source = Path(result.allure_results)
        for artifact in source.iterdir() if source.exists() else ():
            if artifact.name == "environment.properties" or not artifact.is_file():
                continue
            target = combined_dir / artifact.name
            if target.exists():
                target = combined_dir / f"{result.device_udid}-{artifact.name}"
            shutil.copy2(artifact, target)

    devices = "; ".join(
        f"{result.platform} {result.device_name} {result.os_version} "
        f"{result.target_type} ({result.device_udid})"
        for result in results
    )
    properties = [
        f"Test.Environment={results[0].environment}",
        f"Test.Distribution={distribution}",
        f"Devices.Count={len(results)}",
        f"Devices={devices}",
    ]
    (combined_dir / "environment.properties").write_text(
        "\n".join(properties) + "\n", encoding="utf-8"
    )
    return combined_dir


def generate_allure_report(run_root: Path, combined_dir: Path) -> Path | None:
    allure = shutil.which("allure")
    if not allure:
        print("[matrix] Allure CLI not found; raw results are still available.")
        return None
    report_dir = run_root / "allure-report"
    completed = subprocess.run(
        [allure, "generate", str(combined_dir), "--clean", "-o", str(report_dir)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        print(f"[matrix] Allure report generation failed: {completed.stderr.strip()}")
        return None
    return report_dir


def write_summary(
    run_root: Path,
    started_at: datetime,
    results: list[DeviceResult],
    allure_report: Path | None,
    distribution: str,
) -> None:
    completed_at = datetime.now().astimezone()
    payload = {
        "environment": results[0].environment,
        "distribution": distribution,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "status": "PASSED" if all(item.status == "PASSED" for item in results) else "FAILED",
        "allure_report": str(allure_report) if allure_report else None,
        "devices": [asdict(result) for result in results],
    }
    (run_root / "summary.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )

    lines = [
        "# Device Matrix Test Summary",
        "",
        f"- Environment: `{payload['environment']}`",
        f"- Distribution: `{payload['distribution']}`",
        f"- Status: **{payload['status']}**",
        f"- Started: `{payload['started_at']}`",
        f"- Completed: `{payload['completed_at']}`",
        f"- Devices: `{len(results)}`",
        "",
        "| Platform | Type | Device | OS | UDID | Assigned | Passed | Failed | Errors | "
        "Skipped | Duration | Status |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for result in results:
        lines.append(
            f"| {result.platform} | {result.target_type} | {result.device_name} | "
            f"{result.os_version} | `{result.device_udid}` | "
            f"{'all' if result.assigned_nodeids is None else len(result.assigned_nodeids)} | "
            f"{result.passed} | "
            f"{result.failures} | "
            f"{result.errors} | {result.skipped} | {result.duration_seconds:.1f}s | "
            f"{result.status} |"
        )
    lines.extend(["", "## Artifacts", ""])
    for result in results:
        lines.extend(
            [
                f"### {result.platform} - {result.device_name}",
                "",
                f"- Pytest log: `{result.log_path}`",
                f"- JUnit XML: `{result.junit_path}`",
                f"- Allure results: `{result.allure_results}`",
                f"- Failure screenshots: `{result.screenshots}`",
                "",
                "| Test case | Result | Duration | Message |",
                "|---|---|---:|---|",
            ]
        )
        for case in result.cases:
            message = case.message.replace("|", "\\|")
            lines.append(
                f"| {case.name} | {case.status} | "
                f"{case.duration_seconds:.3f}s | {message} |"
            )
        lines.append("")
    if allure_report:
        lines.extend([f"- Combined Allure report: `{allure_report / 'index.html'}`", ""])
    (run_root / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run pytest concurrently across connected Android and iOS devices."
    )
    parser.add_argument("--env", dest="environment", default="preprod")
    parser.add_argument("--platform", choices=("all", "android", "ios"), default="all")
    parser.add_argument(
        "--distribution",
        choices=("replicate", "split"),
        default="replicate",
        help="Run the selected suite on every device or split it across devices",
    )
    parser.add_argument("--device", action="append", default=[], help="Only run a UDID")
    parser.add_argument("--list", action="store_true", help="List targets without running")
    parser.add_argument("--appium-url", default="http://127.0.0.1:4723")
    parser.add_argument("--android-app", type=Path, default=ROOT / "app" / "app-release.apk")
    parser.add_argument("--ios-app", type=Path, default=ROOT / "app" / "Runner.app")
    parser.add_argument(
        "--ios-real-app",
        type=Path,
        help="Signed .ipa or .app for physical iOS devices",
    )
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument("--android-system-port-base", type=int, default=8200)
    parser.add_argument("--ios-wda-port-base", type=int, default=8100)
    parser.add_argument("--ios-mjpeg-port-base", type=int, default=9100)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    devices = discover_devices(args.platform, set(args.device))
    if not devices:
        print("[matrix] No matching ready devices were discovered.", file=sys.stderr)
        return 2

    print(f"[matrix] Discovered {len(devices)} device(s):")
    for device in devices:
        print(
            f"  - {device.platform}: {device.name}, OS {device.os_version}, "
            f"{device.target_type}, UDID {device.udid}"
        )
    collected_nodeids = (
        collect_test_nodeids(args) if args.distribution == "split" else None
    )
    assignments = build_assignments(
        devices,
        args.distribution,
        collected_nodeids,
    )
    active_devices = [assignment.device for assignment in assignments]
    if args.distribution == "split":
        print(
            f"[matrix] Split {len(collected_nodeids or [])} test(s) across "
            f"{len(assignments)} device(s):"
        )
        for assignment in assignments:
            print(
                f"  - {assignment.device.platform} {assignment.device.name}: "
                f"{len(assignment.assigned_nodeids or ())} test(s)"
            )
            for nodeid in assignment.assigned_nodeids or ():
                print(f"      {nodeid}")
        for device in devices[len(assignments):]:
            print(
                f"  - {device.platform} {device.name}: idle "
                "(more devices than selected tests)"
            )
    if args.list:
        return 0

    check_appium(args.appium_url)
    if (
        any(device.platform == "Android" for device in active_devices)
        and not args.android_app.exists()
    ):
        raise FileNotFoundError(f"Android app not found: {args.android_app}")
    simulators = [device for device in active_devices if device.target_type == "simulator"]
    if simulators and not args.ios_app.exists():
        raise FileNotFoundError(f"iOS app not found: {args.ios_app}")
    real_ios_devices = [device for device in active_devices if device.target_type == "real"]
    if real_ios_devices and args.ios_real_app is None:
        raise FileNotFoundError(
            "Physical iOS devices were discovered; provide --ios-real-app with a "
            "signed .ipa or device .app bundle."
        )
    if args.ios_real_app is not None and not args.ios_real_app.exists():
        raise FileNotFoundError(f"Physical iOS app not found: {args.ios_real_app}")

    started_at = datetime.now().astimezone()
    timestamp = started_at.strftime("%Y%m%d-%H%M%S")
    run_root = args.report_root.resolve() / args.environment / timestamp
    run_root.mkdir(parents=True, exist_ok=True)

    running = [
        start_device(assignment, args, index, run_root)
        for index, assignment in enumerate(assignments)
    ]
    results = [finish_device(item, args.environment) for item in running]
    combined_dir = combine_allure_results(run_root, results, args.distribution)
    allure_report = generate_allure_report(run_root, combined_dir)
    write_summary(
        run_root,
        started_at,
        results,
        allure_report,
        args.distribution,
    )

    print(f"[matrix] Summary: {run_root / 'summary.md'}")
    if allure_report:
        print(f"[matrix] Allure:  {allure_report / 'index.html'}")
    return 0 if all(result.status == "PASSED" for result in results) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"[matrix] ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
