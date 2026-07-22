"""Run the Trackify pytest suite concurrently across connected devices."""

from __future__ import annotations

import argparse
import atexit
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.environment_profile import SUPPORTED_ENVIRONMENTS
from scripts.sync_engine import SyncError, changed_nodeids, parse_workbook

DEFAULT_REPORT_ROOT = ROOT / "report" / "device-matrix"
SAFE_NAME = re.compile(r"[^A-Za-z0-9_.-]+")
UNIT_TEST_IGNORE = "--ignore=tests/unit"
DEVICE_BOOT_TIMEOUT_SECONDS = 120
DEVICE_POLL_INTERVAL_SECONDS = 2
APPIUM_STARTUP_TIMEOUT_SECONDS = 30
APPIUM_POLL_INTERVAL_SECONDS = 1


class ShardConfigError(ValueError):
    """Raised when an explicit case-to-device mapping is invalid."""


class DevicePreparationError(RuntimeError):
    """Raised when a requested simulator cannot be prepared for execution."""


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


@dataclass(frozen=True)
class ShardConfig:
    """Validated explicit device shard selectors, preserving file order."""

    assignments: tuple[tuple[str, tuple[str, ...]], ...]


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
    app_version: str
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


@dataclass(frozen=True)
class ManagedAppium:
    """An Appium server process started and owned by this matrix invocation."""

    process: subprocess.Popen[str]
    log_path: Path


@dataclass
class LifecycleState:
    """Resources owned by one matrix process and finalized at interpreter exit."""

    shutdown_after: int
    devices: list[Device]
    manage_devices: bool = False
    managed_appium: ManagedAppium | None = None
    tests_started: bool = False
    finalized: bool = False


def finalize_lifecycle(state: LifecycleState) -> None:
    """Release owned resources once, waiting only after test execution."""
    if state.finalized:
        return
    state.finalized = True
    if state.tests_started:
        shutdown_managed_lifecycle(
            state.devices if state.manage_devices else [],
            state.managed_appium,
            state.shutdown_after,
        )
        return
    if state.manage_devices:
        stop_virtual_devices(state.devices)
    if state.managed_appium is not None:
        stop_managed_appium(state.managed_appium)


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


def _android_emulator() -> str:
    if executable := shutil.which("emulator"):
        return executable
    sdk_root = os.getenv("ANDROID_HOME") or os.getenv("ANDROID_SDK_ROOT")
    if sdk_root:
        candidate = Path(sdk_root) / "emulator" / "emulator"
        if candidate.exists():
            return str(candidate)
    candidate = Path.home() / "Library" / "Android" / "sdk" / "emulator" / "emulator"
    return str(candidate) if candidate.exists() else "emulator"


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
                target_type="emulator" if udid.startswith("emulator-") else "real",
            )
        )
    return devices


def _running_android_avds() -> dict[str, str]:
    """Return ready Android AVD names keyed to their emulator serials."""
    running: dict[str, str] = {}
    adb = _adb()
    for device in discover_android_devices():
        if device.target_type != "emulator":
            continue
        try:
            output = _run([adb, "-s", device.udid, "emu", "avd", "name"])
        except (OSError, subprocess.SubprocessError):
            continue
        name = next(
            (line.strip() for line in output.splitlines() if line.strip() != "OK"),
            "",
        )
        if name:
            running[name] = device.udid
    return running


def list_android_avds() -> list[str]:
    """Return installed local Android AVD names."""
    try:
        output = _run([_android_emulator(), "-list-avds"])
    except (OSError, subprocess.SubprocessError) as exc:
        raise DevicePreparationError(f"cannot list Android AVDs: {exc}") from exc
    return sorted({line.strip() for line in output.splitlines() if line.strip()})


def _version_numbers(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", value))


def choose_android_avd(
    available_avds: list[str],
    running_avds: dict[str, str],
) -> str:
    """Choose one deterministic AVD, preferring an already-running target."""
    available = set(available_avds)
    running = available.intersection(running_avds)
    candidates = running or available
    if not candidates:
        raise DevicePreparationError(
            "no Android AVD is installed; create one in Android Studio first"
        )
    return max(candidates, key=lambda name: (_version_numbers(name), name.lower()))


def _android_boot_completed(udid: str) -> bool:
    try:
        return _run(
            [_adb(), "-s", udid, "shell", "getprop", "sys.boot_completed"],
            timeout=5,
        ) == "1"
    except (OSError, subprocess.SubprocessError):
        return False


def ensure_android_avds(
    avd_names: list[str],
    *,
    timeout: int = DEVICE_BOOT_TIMEOUT_SECONDS,
) -> set[str]:
    """Start requested local AVDs when needed and wait for Android readiness."""
    if not avd_names:
        return set()
    emulator = _android_emulator()
    available = set(list_android_avds())
    unknown = sorted(set(avd_names) - available)
    if unknown:
        raise DevicePreparationError(
            "unknown Android AVD(s): " + ", ".join(unknown)
        )

    running = _running_android_avds()
    for avd_name in dict.fromkeys(avd_names):
        if avd_name in running:
            continue
        print(f"[matrix] Starting Android AVD {avd_name!r}...")
        try:
            subprocess.Popen(
                [emulator, "-avd", avd_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as exc:
            raise DevicePreparationError(
                f"cannot start Android AVD {avd_name!r}: {exc}"
            ) from exc

    deadline = time.monotonic() + timeout
    desired = set(avd_names)
    while time.monotonic() < deadline:
        running = _running_android_avds()
        if desired.issubset(running) and all(
            _android_boot_completed(running[name]) for name in desired
        ):
            return {running[name] for name in desired}
        time.sleep(DEVICE_POLL_INTERVAL_SECONDS)
    waiting_for = sorted(desired - set(running))
    detail = ", ".join(waiting_for or desired)
    raise DevicePreparationError(
        f"Android AVD boot timed out after {timeout}s: {detail}"
    )


def discover_ios_simulators() -> list[Device]:
    """Return all booted and available iOS simulators."""
    try:
        payload = json.loads(_run(["xcrun", "simctl", "list", "devices", "booted", "--json"]))
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"[matrix] iOS discovery skipped: {exc}", file=sys.stderr)
        return []

    return parse_ios_simulator_inventory(payload, booted_only=True)


def parse_ios_simulator_inventory(
    payload: dict[str, object],
    *,
    booted_only: bool = False,
) -> list[Device]:
    """Convert ``simctl list --json`` output into available simulator targets."""
    devices: list[Device] = []
    raw_devices = payload.get("devices", {})
    if not isinstance(raw_devices, dict):
        return devices
    for runtime, runtime_devices in raw_devices.items():
        match = re.search(r"\.iOS-(\d+)-(\d+)(?:-(\d+))?$", str(runtime))
        version = ".".join(part for part in match.groups() if part) if match else "unknown"
        if not isinstance(runtime_devices, list):
            continue
        for item in runtime_devices:
            if not isinstance(item, dict):
                continue
            if booted_only and item.get("state") != "Booted":
                continue
            if not item.get("isAvailable", True):
                continue
            if not item.get("udid"):
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


def select_prepared_devices(
    devices: list[Device],
    *,
    prepared_udids: set[str],
    explicitly_selected_udids: set[str],
) -> list[Device]:
    """Limit discovered devices to prepared targets, then honor ``--device``."""
    selected = devices
    if prepared_udids:
        selected = [device for device in selected if device.udid in prepared_udids]
    if explicitly_selected_udids:
        selected = [
            device for device in selected if device.udid in explicitly_selected_udids
        ]
    return selected


def choose_ios_simulator(
    devices: list[Device],
    states: dict[str, str],
) -> Device:
    """Choose one deterministic iOS simulator, preferring a booted iPhone."""
    if not devices:
        raise DevicePreparationError(
            "no iOS Simulator is installed; add one in Xcode first"
        )
    iphones = [device for device in devices if device.name.startswith("iPhone")]
    candidates = iphones or devices
    booted = [device for device in candidates if states.get(device.udid) == "Booted"]
    candidates = booted or candidates
    return max(
        candidates,
        key=lambda device: (
            _version_numbers(device.os_version),
            -len(device.name),
            device.name.lower(),
        ),
    )


def format_available_devices(
    *,
    platform: str,
    android_avds: list[str],
    running_android_avds: dict[str, str],
    ios_simulators: list[Device],
    ios_states: dict[str, str],
) -> str:
    """Render local virtual-device inventory and deterministic auto-selection."""
    lines: list[str] = []
    android_choice: str | None = None
    ios_choice: Device | None = None
    if platform in {"all", "android"}:
        lines.append("Android:")
        for name in sorted(
            android_avds,
            key=lambda value: (_version_numbers(value), value.lower()),
            reverse=True,
        ):
            udid = running_android_avds.get(name)
            status = f"running  {udid}" if udid else "stopped"
            lines.append(f"  {name:<24} {status}")
        if not android_avds:
            lines.append("  (no installed AVDs)")
        else:
            android_choice = choose_android_avd(
                android_avds,
                running_android_avds,
            )
    if platform in {"all", "ios"}:
        if lines:
            lines.append("")
        lines.append("iOS:")
        for device in sorted(
            ios_simulators,
            key=lambda item: (
                _version_numbers(item.os_version),
                item.name.lower(),
            ),
            reverse=True,
        ):
            state = ios_states.get(device.udid, "unknown").lower()
            lines.append(
                f"  {device.name:<24} {state:<8} iOS {device.os_version} "
                f"{device.udid}"
            )
        if not ios_simulators:
            lines.append("  (no installed simulators)")
        else:
            ios_choice = choose_ios_simulator(ios_simulators, ios_states)

    lines.extend(["", "Automatic selection:"])
    if platform in {"all", "android"}:
        lines.append(f"  Android: {android_choice or 'unavailable'}")
    if platform in {"all", "ios"}:
        ios_value = (
            f"{ios_choice.name} ({ios_choice.udid})" if ios_choice else "unavailable"
        )
        lines.append(f"  iOS: {ios_value}")
    return "\n".join(lines)


def android_install_command(adb: str, udid: str, app_path: Path) -> list[str]:
    """Build an idempotent APK replacement command for one Android target."""
    return [adb, "-s", udid, "install", "-r", "-t", str(app_path)]


def ios_install_command(udid: str, app_path: Path) -> list[str]:
    """Build a simulator app replacement command for one iOS target."""
    return ["xcrun", "simctl", "install", udid, str(app_path)]


def _ios_simulator_inventory() -> tuple[list[Device], dict[str, str]]:
    try:
        payload = json.loads(
            _run(["xcrun", "simctl", "list", "devices", "available", "--json"])
        )
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        raise DevicePreparationError(f"cannot list iOS simulators: {exc}") from exc
    devices = parse_ios_simulator_inventory(payload)
    states: dict[str, str] = {}
    raw_devices = payload.get("devices", {})
    if isinstance(raw_devices, dict):
        for runtime_devices in raw_devices.values():
            if not isinstance(runtime_devices, list):
                continue
            for item in runtime_devices:
                if isinstance(item, dict) and item.get("udid"):
                    states[str(item["udid"])] = str(item.get("state", "unknown"))
    return devices, states


def ensure_ios_simulators(
    selectors: list[str],
    *,
    timeout: int = DEVICE_BOOT_TIMEOUT_SECONDS,
) -> set[str]:
    """Boot requested local iOS simulators by exact name or UDID."""
    if not selectors:
        return set()
    inventory, states = _ios_simulator_inventory()
    selected: list[Device] = []
    for selector in dict.fromkeys(selectors):
        matches = [
            device
            for device in inventory
            if device.udid == selector or device.name == selector
        ]
        if not matches:
            raise DevicePreparationError(
                f"unknown iOS Simulator name or UDID: {selector!r}"
            )
        if len(matches) > 1 and all(device.udid != selector for device in matches):
            candidates = ", ".join(device.udid for device in matches)
            raise DevicePreparationError(
                f"iOS Simulator name {selector!r} is ambiguous; use one UDID: "
                f"{candidates}"
            )
        selected.append(matches[0])

    for device in selected:
        if states.get(device.udid) == "Booted":
            continue
        print(f"[matrix] Starting iOS Simulator {device.name!r} ({device.udid})...")
        try:
            _run(["xcrun", "simctl", "boot", device.udid], timeout=30)
            _run(
                ["xcrun", "simctl", "bootstatus", device.udid, "-b"],
                timeout=timeout,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise DevicePreparationError(
                f"cannot boot iOS Simulator {device.udid}: {exc}"
            ) from exc
    return {device.udid for device in selected}


def install_apps_on_devices(
    devices: list[Device],
    *,
    android_app: Path,
    ios_app: Path,
) -> None:
    """Replace the app build on every selected emulator or simulator."""
    for device in devices:
        if device.platform == "Android":
            command = android_install_command(_adb(), device.udid, android_app)
        elif device.target_type == "simulator":
            command = ios_install_command(device.udid, ios_app)
        else:
            print(
                f"[matrix] Physical iOS {device.udid}: Appium will install the "
                "signed --ios-real-app build."
            )
            continue
        print(
            f"[matrix] Installing {device.platform} app on "
            f"{device.name} ({device.udid})..."
        )
        try:
            _run(command, timeout=180)
        except (OSError, subprocess.SubprocessError) as exc:
            raise DevicePreparationError(
                f"app installation failed on {device.udid}: {exc}"
            ) from exc


def stop_virtual_devices(devices: list[Device]) -> None:
    """Stop selected virtual targets immediately without touching real devices."""
    for device in devices:
        if device.target_type not in {"emulator", "simulator"}:
            continue
        try:
            if device.platform == "Android":
                _run([_adb(), "-s", device.udid, "emu", "kill"], timeout=15)
            else:
                _run(["xcrun", "simctl", "shutdown", device.udid], timeout=15)
            print(f"[matrix] Stopped {device.platform} {device.name} ({device.udid}).")
        except (OSError, subprocess.SubprocessError) as exc:
            print(
                f"[matrix] WARNING: failed to stop {device.udid}: {exc}",
                file=sys.stderr,
            )


def shutdown_devices(devices: list[Device], delay_seconds: int) -> None:
    """Wait, then stop selected virtual targets without touching real devices."""
    virtual_devices = [
        device
        for device in devices
        if device.target_type in {"emulator", "simulator"}
    ]
    if not virtual_devices or delay_seconds <= 0:
        return
    print(
        f"[matrix] Tests finished; shutting down {len(virtual_devices)} virtual "
        f"device(s) in {delay_seconds}s."
    )
    time.sleep(delay_seconds)
    stop_virtual_devices(virtual_devices)


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


def load_shard_config(path: Path) -> ShardConfig:
    """Load and strictly validate an explicit case-to-device YAML mapping."""
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ShardConfigError(f"cannot read shard config {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ShardConfigError(f"invalid YAML in shard config {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ShardConfigError("shard config must be a YAML mapping")
    if payload.get("schema_version") != 1:
        raise ShardConfigError("shard config schema_version must be 1")
    raw_assignments = payload.get("assignments")
    if not isinstance(raw_assignments, list) or not raw_assignments:
        raise ShardConfigError("shard config assignments must be a non-empty list")

    assignments: list[tuple[str, tuple[str, ...]]] = []
    seen_devices: set[str] = set()
    for index, raw_assignment in enumerate(raw_assignments, start=1):
        if not isinstance(raw_assignment, dict):
            raise ShardConfigError(f"assignment {index} must be a mapping")
        if set(raw_assignment) != {"device", "cases"}:
            raise ShardConfigError(
                f"assignment {index} must contain only device and cases"
            )
        device = raw_assignment.get("device")
        cases = raw_assignment.get("cases")
        if not isinstance(device, str) or not device.strip():
            raise ShardConfigError(
                f"assignment {index} device must be a non-empty string"
            )
        device = device.strip()
        if device in seen_devices:
            raise ShardConfigError(f"device {device!r} is assigned more than once")
        if not isinstance(cases, list) or not cases:
            raise ShardConfigError(f"assignment {index} cases must be a non-empty list")
        if any(not isinstance(case, str) or not case.strip() for case in cases):
            raise ShardConfigError(f"assignment {index} cases must contain strings")
        seen_devices.add(device)
        assignments.append((device, tuple(case.strip() for case in cases)))
    return ShardConfig(assignments=tuple(assignments))


def resolve_shard_nodeids(
    config: ShardConfig,
    case_id_to_nodeid: dict[str, str],
) -> dict[str, tuple[str, ...]]:
    """Resolve stable scenario IDs while accepting exact pytest node IDs."""
    resolved: dict[str, tuple[str, ...]] = {}
    for device, selectors in config.assignments:
        nodeids: list[str] = []
        for selector in selectors:
            nodeid = case_id_to_nodeid.get(
                selector,
                selector if "::" in selector else None,
            )
            if nodeid is None:
                raise ShardConfigError(
                    f"case {selector!r} is neither a known scenario ID "
                    "nor a pytest node ID"
                )
            nodeids.append(nodeid)
        resolved[device] = tuple(nodeids)
    return resolved


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


def build_mapped_assignments(
    devices: list[Device],
    mapped_nodeids: dict[str, tuple[str, ...]],
    nodeids: list[str],
) -> list[DeviceAssignment]:
    """Build explicit assignments and require every collected case exactly once."""
    devices_by_udid = {device.udid: device for device in devices}
    for udid in mapped_nodeids:
        if udid not in devices_by_udid:
            raise ShardConfigError(f"device {udid!r} is not discovered")

    collected = set(nodeids)
    assigned_to: dict[str, str] = {}
    for udid, assigned_nodeids in mapped_nodeids.items():
        for nodeid in assigned_nodeids:
            previous = assigned_to.get(nodeid)
            if previous is not None:
                raise ShardConfigError(
                    f"case {nodeid!r} is assigned more than once "
                    f"({previous} and {udid})"
                )
            assigned_to[nodeid] = udid

    unknown = sorted(set(assigned_to) - collected)
    if unknown:
        raise ShardConfigError(
            "shard config contains cases that are not selected by pytest: "
            + ", ".join(unknown)
        )
    missing = sorted(collected - set(assigned_to))
    if missing:
        raise ShardConfigError(
            "selected cases are not assigned in shard config: " + ", ".join(missing)
        )

    return [
        DeviceAssignment(
            device=devices_by_udid[udid],
            assigned_nodeids=tuple(assigned_nodeids),
        )
        for udid, assigned_nodeids in mapped_nodeids.items()
    ]


def build_assignments(
    devices: list[Device],
    distribution: str,
    nodeids: list[str] | None = None,
) -> list[DeviceAssignment]:
    """Build full-suite or split-suite assignments for the discovered devices."""
    if distribution == "replicate":
        selected = tuple(nodeids) if nodeids is not None else None
        return [
            DeviceAssignment(device=device, assigned_nodeids=selected)
            for device in devices
        ]
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


def _is_loopback_url(server_url: str) -> bool:
    host = urllib.parse.urlsplit(server_url).hostname
    return host in {"127.0.0.1", "localhost", "::1"}


def check_appium(server_url: str) -> None:
    status_url = f"{server_url.rstrip('/')}/status"
    try:
        if _is_loopback_url(server_url):
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            response_context = opener.open(status_url, timeout=3)
        else:
            response_context = urllib.request.urlopen(status_url, timeout=3)
        with response_context as response:
            payload = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Appium is not reachable at {status_url}: {exc}") from exc
    if not payload.get("value", {}).get("ready"):
        raise RuntimeError(f"Appium is not ready at {status_url}: {payload!r}")


def appium_start_command(executable: str, server_url: str) -> list[str]:
    """Build a local Appium server command matching the configured URL."""
    parsed = urllib.parse.urlsplit(server_url)
    if parsed.scheme != "http" or not _is_loopback_url(server_url):
        raise RuntimeError(
            "Appium can only be auto-started for a local http URL; "
            f"start the remote server manually: {server_url}"
        )
    if parsed.query or parsed.fragment:
        raise RuntimeError(f"Appium URL cannot contain a query or fragment: {server_url}")
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 4723
    command = [executable, "--address", host, "--port", str(port)]
    base_path = parsed.path.rstrip("/")
    if base_path:
        command.extend(["--base-path", base_path])
    return command


def _appium_log_tail(path: Path, limit: int = 20) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(lines[-limit:])


def ensure_appium(
    server_url: str,
    *,
    timeout: int = APPIUM_STARTUP_TIMEOUT_SECONDS,
    log_path: Path | None = None,
) -> ManagedAppium | None:
    """Reuse a ready Appium server or start and own a missing local server."""
    try:
        check_appium(server_url)
    except RuntimeError as initial_error:
        appium = os.getenv("APPIUM_BIN") or shutil.which("appium")
        if not appium:
            raise RuntimeError(
                f"{initial_error}. Appium CLI was not found; install it with "
                "'npm install -g appium'."
            ) from initial_error
        command = appium_start_command(appium, server_url)
        resolved_log = log_path or ROOT / "report" / "appium" / "appium.log"
        resolved_log.parent.mkdir(parents=True, exist_ok=True)
        print(f"[matrix] Appium is not ready; starting: {' '.join(command)}")
        try:
            with resolved_log.open("a", encoding="utf-8") as log_handle:
                process = subprocess.Popen(
                    command,
                    cwd=ROOT,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    text=True,
                    start_new_session=True,
                )
        except OSError as exc:
            raise RuntimeError(f"Cannot start Appium: {exc}") from exc

        deadline = time.monotonic() + timeout
        last_error: RuntimeError = initial_error
        while time.monotonic() < deadline:
            exit_code = process.poll()
            if exit_code is not None:
                tail = _appium_log_tail(resolved_log)
                detail = f"\n{tail}" if tail else ""
                raise RuntimeError(
                    f"Appium exited with code {exit_code}; log: {resolved_log}{detail}"
                )
            try:
                check_appium(server_url)
            except RuntimeError as exc:
                last_error = exc
                time.sleep(APPIUM_POLL_INTERVAL_SECONDS)
                continue
            print(
                f"[matrix] Appium is ready at {server_url} "
                f"(PID {process.pid}, log {resolved_log})."
            )
            return ManagedAppium(process=process, log_path=resolved_log)

        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        raise RuntimeError(
            f"Appium did not become ready within {timeout}s: {last_error}; "
            f"log: {resolved_log}"
        ) from last_error

    print(f"[matrix] Reusing ready Appium server at {server_url}.")
    return None


def stop_managed_appium(managed: ManagedAppium) -> None:
    """Stop only an Appium process started by this matrix invocation."""
    process = managed.process
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
    print(f"[matrix] Stopped managed Appium PID {process.pid}.")


def shutdown_managed_lifecycle(
    devices: list[Device],
    managed_appium: ManagedAppium | None,
    delay_seconds: int,
) -> None:
    """Wait once, then stop owned virtual devices and the owned Appium process."""
    virtual_devices = [
        device
        for device in devices
        if device.target_type in {"emulator", "simulator"}
    ]
    if delay_seconds <= 0 or (not virtual_devices and managed_appium is None):
        return
    targets = []
    if virtual_devices:
        targets.append(f"{len(virtual_devices)} virtual device(s)")
    if managed_appium is not None:
        targets.append(f"Appium PID {managed_appium.process.pid}")
    print(
        f"[matrix] Tests finished; shutting down {' and '.join(targets)} "
        f"in {delay_seconds}s."
    )
    time.sleep(delay_seconds)
    stop_virtual_devices(virtual_devices)
    if managed_appium is not None:
        stop_managed_appium(managed_appium)


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
    worker_properties = read_environment_properties(
        running.allure_dir / "environment.properties"
    )
    app_version = worker_properties.get("App.Version")
    if not app_version and exit_code == 0:
        raise RuntimeError(
            f"Successful worker {running.device.udid} did not report App.Version"
        )
    result = DeviceResult(
        environment=environment,
        app_version=app_version or "unresolved",
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


def read_environment_properties(path: Path) -> dict[str, str]:
    """Read one worker's simple Allure environment properties file."""
    if not path.is_file():
        return {}
    properties: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key:
            properties[key] = value
    return properties


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
        f"{result.target_type} ({result.device_udid}), app {result.app_version}"
        for result in results
    )
    properties = [
        f"Test.Environment={results[0].environment}",
        f"Test.Distribution={distribution}",
        f"Devices.Count={len(results)}",
        f"Devices={devices}",
    ]
    for index, result in enumerate(results, start=1):
        properties.extend(
            [
                f"Device.{index}.UDID={result.device_udid}",
                f"Device.{index}.App.Version={result.app_version}",
            ]
        )
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


def load_change_manifest(path: Path | None) -> dict[str, object] | None:
    """Load and minimally validate a sync-engine changed-case manifest."""
    if path is None:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid change manifest {path}: {exc}") from exc
    runnable = payload.get("runnable")
    if payload.get("schema_version") != 1 or not isinstance(runnable, list):
        raise ValueError(f"unsupported change manifest schema: {path}")
    required_fields = ("kind", "test_case_id", "title", "nodeid")
    if any(
        not isinstance(item, dict)
        or any(not isinstance(item.get(field), str) for field in required_fields)
        for item in runnable
    ):
        raise ValueError(f"invalid runnable cases in change manifest: {path}")
    return payload


def _markdown(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_summary(
    run_root: Path,
    started_at: datetime,
    results: list[DeviceResult],
    allure_report: Path | None,
    distribution: str,
    change_manifest: dict[str, object] | None = None,
) -> None:
    completed_at = datetime.now().astimezone()
    payload = {
        "environment": results[0].environment,
        "distribution": distribution,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "status": "PASSED" if all(item.status == "PASSED" for item in results) else "FAILED",
        "allure_report": str(allure_report) if allure_report else None,
        "changed_cases": (
            change_manifest.get("runnable", []) if change_manifest else []
        ),
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
        "| Platform | Type | Device | OS | App Version | UDID | Assigned | Passed | Failed | Errors | "
        "Skipped | Duration | Status |",
        "|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for result in results:
        lines.append(
            f"| {result.platform} | {result.target_type} | {result.device_name} | "
            f"{result.os_version} | {result.app_version} | `{result.device_udid}` | "
            f"{'all' if result.assigned_nodeids is None else len(result.assigned_nodeids)} | "
            f"{result.passed} | "
            f"{result.failures} | "
            f"{result.errors} | {result.skipped} | {result.duration_seconds:.1f}s | "
            f"{result.status} |"
        )
    mapped_results = [
        result for result in results if result.assigned_nodeids is not None
    ]
    if distribution == "mapped" and mapped_results:
        lines.extend(["", "## Explicit Case Assignments", ""])
        for result in mapped_results:
            lines.append(
                f"- `{result.device_udid}` ({result.device_name}): "
                + ", ".join(f"`{nodeid}`" for nodeid in result.assigned_nodeids or ())
            )

    changed_cases = payload["changed_cases"]
    if changed_cases:
        device_headers = [
            f"{result.platform} {result.device_name}" for result in results
        ]
        lines.extend(
            [
                "",
                "## Changed Case Health",
                "",
                "| Change | Test Case ID | Scenario | "
                + " | ".join(_markdown(header) for header in device_headers)
                + " |",
                "|---|---|---|" + "---|" * len(results),
            ]
        )
        for changed_case in changed_cases:
            nodeid = str(changed_case["nodeid"])
            pytest_name = nodeid.rsplit("::", 1)[-1]
            statuses = []
            for result in results:
                case = next(
                    (item for item in result.cases if item.name == pytest_name),
                    None,
                )
                statuses.append(case.status if case else "NOT_RUN")
            lines.append(
                f"| {_markdown(changed_case['kind'])} | "
                f"`{_markdown(changed_case['test_case_id'])}` | "
                f"{_markdown(changed_case['title'])} | "
                + " | ".join(statuses)
                + " |"
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
    parser.add_argument(
        "--env",
        dest="environment",
        choices=SUPPORTED_ENVIRONMENTS,
        default="preprod",
    )
    parser.add_argument("--platform", choices=("all", "android", "ios"), default="all")
    parser.add_argument(
        "--distribution",
        choices=("replicate", "split", "mapped"),
        default="replicate",
        help=(
            "Run on every device, automatically split across devices, or use "
            "an explicit case-to-device mapping"
        ),
    )
    parser.add_argument("--device", action="append", default=[], help="Only run a UDID")
    parser.add_argument(
        "--shard-config",
        type=Path,
        help="YAML case-to-device mapping used with --distribution mapped",
    )
    parser.add_argument(
        "--case-registry",
        type=Path,
        default=ROOT / "data" / "test_cases.xlsx",
        help="Excel registry used to resolve stable TC_* IDs in a shard config",
    )
    parser.add_argument(
        "--prepare-devices",
        action="store_true",
        help="Boot requested virtual devices, replace the app, then run tests",
    )
    parser.add_argument(
        "--android-avd",
        action="append",
        default=[],
        help="Android AVD name to ensure is running; repeat for multiple AVDs",
    )
    parser.add_argument(
        "--ios-simulator",
        action="append",
        default=[],
        help="iOS Simulator name or UDID to boot; repeat for multiple simulators",
    )
    parser.add_argument(
        "--device-boot-timeout",
        type=int,
        default=DEVICE_BOOT_TIMEOUT_SECONDS,
        help="Seconds to wait for each requested virtual target to become ready",
    )
    parser.add_argument(
        "--shutdown-after",
        type=int,
        default=60,
        help="Seconds to wait after the run before stopping virtual targets; 0 keeps them",
    )
    parser.add_argument(
        "--list-available-devices",
        action="store_true",
        help="List installed virtual targets and show automatic choices",
    )
    parser.add_argument("--list", action="store_true", help="List targets without running")
    parser.add_argument("--appium-url", default="http://127.0.0.1:4723")
    parser.add_argument(
        "--auto-start-appium",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Start a missing local Appium server before execution and stop an "
            "owned server after --shutdown-after seconds"
        ),
    )
    parser.add_argument("--android-app", type=Path, default=ROOT / "app" / "app-release.apk")
    parser.add_argument("--ios-app", type=Path, default=ROOT / "app" / "Runner.app")
    parser.add_argument(
        "--ios-real-app",
        type=Path,
        help="Signed .ipa or .app for physical iOS devices",
    )
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument(
        "--change-manifest",
        type=Path,
        help="Sync-engine JSON manifest to embed in the matrix health report",
    )
    parser.add_argument("--android-system-port-base", type=int, default=8200)
    parser.add_argument("--ios-wda-port-base", type=int, default=8100)
    parser.add_argument("--ios-mjpeg-port-base", type=int, default=9100)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    lifecycle = LifecycleState(
        shutdown_after=args.shutdown_after,
        devices=[],
        manage_devices=args.prepare_devices,
    )
    atexit.register(finalize_lifecycle, lifecycle)
    if args.distribution == "mapped" and args.shard_config is None:
        raise ValueError("--distribution mapped requires --shard-config")
    if args.distribution != "mapped" and args.shard_config is not None:
        raise ValueError("--shard-config can only be used with --distribution mapped")
    if (args.android_avd or args.ios_simulator) and not args.prepare_devices:
        raise ValueError(
            "--android-avd and --ios-simulator require --prepare-devices"
        )
    if args.platform == "ios" and args.android_avd:
        raise ValueError("--android-avd cannot be used with --platform ios")
    if args.platform == "android" and args.ios_simulator:
        raise ValueError("--ios-simulator cannot be used with --platform android")
    if args.prepare_devices and args.list:
        raise ValueError("--prepare-devices cannot be combined with --list")
    if args.list_available_devices and (args.prepare_devices or args.list):
        raise ValueError(
            "--list-available-devices cannot be combined with --prepare-devices or --list"
        )
    if args.device_boot_timeout < 1:
        raise ValueError("--device-boot-timeout must be at least 1")
    if args.shutdown_after < 0:
        raise ValueError("--shutdown-after must be zero or greater")
    if args.android_avd and not args.android_app.exists():
        raise FileNotFoundError(f"Android app not found: {args.android_app}")
    if args.ios_simulator and not args.ios_app.exists():
        raise FileNotFoundError(f"iOS app not found: {args.ios_app}")
    if args.list_available_devices:
        android_avds: list[str] = []
        running_android_avds: dict[str, str] = {}
        ios_simulators: list[Device] = []
        ios_states: dict[str, str] = {}
        if args.platform in {"all", "android"}:
            android_avds = list_android_avds()
            running_android_avds = _running_android_avds()
        if args.platform in {"all", "ios"}:
            ios_simulators, ios_states = _ios_simulator_inventory()
        print(
            format_available_devices(
                platform=args.platform,
                android_avds=android_avds,
                running_android_avds=running_android_avds,
                ios_simulators=ios_simulators,
                ios_states=ios_states,
            )
        )
        return 0
    if not args.list:
        if args.prepare_devices or args.auto_start_appium:
            lifecycle.managed_appium = ensure_appium(args.appium_url)
        else:
            check_appium(args.appium_url)

    change_manifest = load_change_manifest(args.change_manifest)
    prepared_udids: set[str] = set()
    if args.prepare_devices:
        if args.platform in {"all", "android"}:
            android_avds = list(args.android_avd)
            if not android_avds:
                android_avds = [
                    choose_android_avd(
                        list_android_avds(),
                        _running_android_avds(),
                    )
                ]
                print(f"[matrix] Auto-selected Android AVD {android_avds[0]!r}.")
            prepared_udids.update(
                ensure_android_avds(
                    android_avds,
                    timeout=args.device_boot_timeout,
                )
            )
        if args.platform in {"all", "ios"}:
            ios_selectors = list(args.ios_simulator)
            if not ios_selectors:
                ios_inventory, ios_states = _ios_simulator_inventory()
                selected_ios = choose_ios_simulator(ios_inventory, ios_states)
                ios_selectors = [selected_ios.udid]
                print(
                    f"[matrix] Auto-selected iOS Simulator "
                    f"{selected_ios.name!r} ({selected_ios.udid})."
                )
            prepared_udids.update(
                ensure_ios_simulators(
                    ios_selectors,
                    timeout=args.device_boot_timeout,
                )
            )
    devices = select_prepared_devices(
        discover_devices(args.platform, set()),
        prepared_udids=prepared_udids,
        explicitly_selected_udids=set(args.device),
    )
    if not devices:
        detail = (
            " No --android-avd or --ios-simulator target was provided."
            if args.prepare_devices and not prepared_udids
            else ""
        )
        print(
            f"[matrix] No matching ready devices were discovered.{detail}",
            file=sys.stderr,
        )
        return 2
    lifecycle.devices = devices

    print(f"[matrix] Discovered {len(devices)} device(s):")
    for device in devices:
        print(
            f"  - {device.platform}: {device.name}, OS {device.os_version}, "
            f"{device.target_type}, UDID {device.udid}"
        )
    normalized_pytest_args = normalize_pytest_args(args.pytest_args)
    collected_nodeids = (
        collect_test_nodeids(args)
        if args.distribution in {"split", "mapped"} or normalized_pytest_args
        else None
    )
    if args.distribution == "mapped":
        config = load_shard_config(args.shard_config)
        try:
            rows = parse_workbook(args.case_registry)
        except (OSError, SyncError, ValueError) as exc:
            raise ShardConfigError(
                f"cannot resolve stable case IDs from {args.case_registry}: {exc}"
            ) from exc
        case_id_to_nodeid = {
            row.scenario_id: nodeid
            for row, nodeid in zip(rows, changed_nodeids(rows), strict=True)
        }
        mapped_nodeids = resolve_shard_nodeids(config, case_id_to_nodeid)
        assignments = build_mapped_assignments(
            devices,
            mapped_nodeids,
            collected_nodeids or [],
        )
    else:
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
    elif args.distribution == "mapped":
        print(
            f"[matrix] Using explicit case-to-device mapping for "
            f"{len(collected_nodeids or [])} test(s):"
        )
        for assignment in assignments:
            print(
                f"  - {assignment.device.platform} {assignment.device.name} "
                f"({assignment.device.udid}):"
            )
            for nodeid in assignment.assigned_nodeids or ():
                print(f"      {nodeid}")
    elif collected_nodeids is not None:
        print(
            f"[matrix] Replicating {len(collected_nodeids)} selected test(s) "
            f"across {len(assignments)} device(s)."
        )
    if args.list:
        return 0

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

    if args.prepare_devices:
        install_apps_on_devices(
            active_devices,
            android_app=args.android_app.resolve(),
            ios_app=args.ios_app.resolve(),
        )

    started_at = datetime.now().astimezone()
    timestamp = started_at.strftime("%Y%m%d-%H%M%S")
    run_root = args.report_root.resolve() / args.environment / timestamp
    run_root.mkdir(parents=True, exist_ok=True)

    lifecycle.tests_started = True
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
        change_manifest,
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
