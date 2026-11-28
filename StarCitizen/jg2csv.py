#!/usr/bin/env python3
"""Export Joystick Gobloon or Joystick Gremlin XML profiles to CSV."""

from __future__ import annotations

import argparse
import csv
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable


CONTROL_LABEL_RE = re.compile(
    r"\b([LR]-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\b"
)
MAIN_TRIGGER_LABEL_RE = re.compile(
    r"\bMAIN-TRIG-([LR])\.stage-\d+\b"
)
RAPID_TRIGGER_LABEL_RE = re.compile(
    r"\bRAPID-TRIG-([LR])(?:\.[A-Za-z0-9_.-]+)?\b"
)
TYPE_ORDER = {"axis": 0, "button": 1, "hat": 2}


def element_properties(action: ET.Element) -> dict[str, str | None]:
    return {
        prop.findtext("name"): prop.findtext("value")
        for prop in action.findall("./property")
    }


def child_action_ids(action: ET.Element, container: str) -> list[str]:
    return [
        node.text
        for node in action.findall(f"./{container}/action-id")
        if node.text
    ]


def deduplicate(items: Iterable[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if item and item not in result:
            result.append(item)
    return result


def collect_vjoy_targets(
    action_id: str,
    actions: dict[str, ET.Element],
    seen: set[str] | None = None,
) -> list[tuple[str, str, str]]:
    if seen is None:
        seen = set()
    if action_id in seen:
        return []

    seen = seen.copy()
    seen.add(action_id)
    action = actions.get(action_id)
    if action is None:
        return []

    kind = action.get("type")
    targets: list[tuple[str, str, str]] = []

    if kind == "map-to-vjoy":
        action_props = element_properties(action)
        targets.append(
            (
                action_props.get("vjoy-device-id") or "?",
                action_props.get("vjoy-input-type") or "input",
                action_props.get("vjoy-input-id") or "?",
            )
        )

    if kind == "macro":
        for macro_action in action.findall("./macro-action"):
            if macro_action.get("type") != "vjoy":
                continue
            macro_props = {
                prop.findtext("name"): prop.findtext("value")
                for prop in macro_action.findall("./property")
            }
            targets.append(
                (
                    macro_props.get("vjoy-id") or "?",
                    macro_props.get("input-type") or "input",
                    macro_props.get("input-id") or "?",
                )
            )

    for container in ("actions", "short-actions", "long-actions"):
        for child_id in child_action_ids(action, container):
            targets.extend(collect_vjoy_targets(child_id, actions, seen))

    return deduplicate_targets(targets)


def deduplicate_targets(
    targets: Iterable[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    result: list[tuple[str, str, str]] = []
    for target in targets:
        if target not in result:
            result.append(target)
    return result


def macro_summary(action: ET.Element) -> str:
    summaries: list[str] = []
    for macro_action in action.findall("./macro-action"):
        macro_props = {
            prop.findtext("name"): prop.findtext("value")
            for prop in macro_action.findall("./property")
        }
        kind = macro_action.get("type")

        if kind == "vjoy":
            value = "press" if macro_props.get("value") == "True" else "release"
            summaries.append(
                "vJoy {} {} {} {}".format(
                    macro_props.get("vjoy-id", "?"),
                    macro_props.get("input-type", "input"),
                    macro_props.get("input-id", "?"),
                    value,
                )
            )
        elif kind == "key":
            summaries.append("Key scan-code {}".format(macro_props.get("scan-code", "?")))

    return "Macro: " + ", ".join(summaries) if summaries else "Macro"


def action_label(action: ET.Element) -> str | None:
    return element_properties(action).get("action-label")


def summarize_action(
    action_id: str,
    actions: dict[str, ET.Element],
    seen: set[str] | None = None,
) -> list[str]:
    if seen is None:
        seen = set()
    if action_id in seen:
        return []

    seen = seen.copy()
    seen.add(action_id)
    action = actions.get(action_id)
    if action is None:
        return []

    kind = action.get("type")
    action_props = element_properties(action)

    if kind == "root":
        pieces: list[str] = []
        for child_id in child_action_ids(action, "actions"):
            pieces.extend(summarize_action(child_id, actions, seen))

        label = action_props.get("action-label")
        if (
            label
            and label not in (
                "Root",
                "Response Curve (For Inversion)",
                "Axis to Mouse Axis (3rd Person Freelook)",
            )
            and not pieces
        ):
            pieces.insert(0, label)
        elif label == "Axis to Mouse Axis (3rd Person Freelook)" and pieces:
            pieces.insert(0, label)
        return deduplicate(pieces)

    if kind == "tempo":
        short: list[str] = []
        long: list[str] = []
        for child_id in child_action_ids(action, "short-actions"):
            short.extend(summarize_action(child_id, actions, seen))
        for child_id in child_action_ids(action, "long-actions"):
            long.extend(summarize_action(child_id, actions, seen))

        pieces = []
        if short:
            pieces.append("Tap: " + " / ".join(deduplicate(short)))
        if long:
            pieces.append("Hold: " + " / ".join(deduplicate(long)))
        if not pieces and action_label(action):
            pieces.append(action_label(action))
        return pieces

    if kind == "map-to-vjoy":
        label = action_label(action)
        mapping = "vJoy {} {} {}".format(
            action_props.get("vjoy-device-id", "?"),
            action_props.get("vjoy-input-type", "input"),
            action_props.get("vjoy-input-id", "?"),
        )
        return [f"{label} [{mapping}]"] if label else [mapping]

    if kind == "map-to-mouse":
        label = action_label(action)
        direction = action_props.get("direction")
        mouse_axis = (
            "Mouse X"
            if direction == "0"
            else "Mouse Y"
            if direction == "90"
            else "Mouse"
        )
        return [f"{label} [{mouse_axis}]"] if label else [mouse_axis]

    if kind == "change-mode":
        label = action_label(action)
        target = action.findtext("./target-mode/property[name='name']/value")
        if not target:
            target_property = action.find("./target-mode/property")
            if target_property is not None:
                target = target_property.findtext("value")
        change_type = action_props.get("change-type")
        if target:
            prefix = f"Change mode to {target}"
            if change_type:
                prefix = f"{change_type} mode: {target}"
            return [f"{prefix}"] if not label else [f"{prefix} | {label}"]
        return [label] if label else ["Change mode"]

    if kind == "macro":
        return [macro_summary(action)]

    if kind == "text-to-speech":
        text = action_props.get("text")
        if text:
            return [f"Speak: {text}"]
        return ["Text to speech"]

    if kind == "smart-toggle":
        pieces: list[str] = []
        for child_id in child_action_ids(action, "actions"):
            pieces.extend(summarize_action(child_id, actions, seen))
        return deduplicate(pieces) if pieces else ["Smart toggle"]

    if kind == "map-to-logical-device":
        input_type = action_props.get("logical-input-type", "input")
        input_id = action_props.get("logical-input-id", "?")
        return [f"Logical device {input_type} {input_id}"]

    if kind in ("description", "response-curve"):
        return []

    return [action_label(action)] if action_label(action) else []


def collect_descriptions(
    action_id: str,
    actions: dict[str, ET.Element],
    seen: set[str] | None = None,
) -> list[str]:
    if seen is None:
        seen = set()
    if action_id in seen:
        return []

    seen = seen.copy()
    seen.add(action_id)
    action = actions.get(action_id)
    if action is None:
        return []

    result: list[str] = []
    if action.get("type") == "description":
        description = element_properties(action).get("description")
        if description:
            result.append(description)

    for container in ("actions", "short-actions", "long-actions"):
        for child_id in child_action_ids(action, container):
            result.extend(collect_descriptions(child_id, actions, seen))
    return result


def control_name(control: dict[str, object]) -> str:
    candidates: list[str] = []
    input_id = control["input_id"]
    device = str(control["device"])
    side = "R" if device.endswith(" R") else "L" if device.endswith(" L") else ""

    for mode_actions in control["mode_actions"].values():
        for text in mode_actions:
            candidates.extend(
                f"{label}-{input_id}"
                for label in CONTROL_LABEL_RE.findall(text)
            )
            for side in MAIN_TRIGGER_LABEL_RE.findall(text):
                return f"{side}-MAIN_TRIG-{control['input_id']}"
            for side in RAPID_TRIGGER_LABEL_RE.findall(text):
                return f"{side}-RAPID_TRIG-{control['input_id']}"
    if candidates:
        return deduplicate(candidates)[0]

    input_type = str(control["input_type"]).capitalize()
    prefix = f"{side}-" if side else ""
    return f"{prefix}{input_type.upper()}-{input_id}"


def detect_profile_format(root: ET.Element) -> str:
    app = (root.get("app") or "").strip().lower()
    if app == "gobloon":
        return "Joystick Gobloon"
    if app in ("", "gremlin", "joystick gremlin"):
        return "Joystick Gremlin"
    raise ValueError(f"unsupported profile app: {root.get('app')}")


def export_profile(source: Path, output: Path) -> tuple[int, str]:
    if not source.is_file():
        raise FileNotFoundError(f"Joystick profile not found: {source}")

    root = ET.parse(source).getroot()
    profile_format = detect_profile_format(root)
    mode_nodes = [mode for mode in root.findall("./modes/mode") if mode.text]
    modes = [mode.text for mode in mode_nodes if mode.text]
    parents = {
        mode.text: mode.get("parent")
        for mode in mode_nodes
        if mode.text
    }

    devices = {
        device.findtext("device-id"): " ".join(
            (device.findtext("device-name") or "").split()
        )
        for device in root.findall("./devices/device")
    }
    actions = {
        action.get("id"): action
        for action in root.findall("./library/action")
        if action.get("id")
    }

    controls: dict[tuple[str, str, str], dict[str, object]] = {}
    for input_node in root.findall("./inputs/input"):
        device_id = input_node.findtext("device-id") or ""
        input_type = input_node.findtext("input-type") or ""
        input_id = input_node.findtext("input-id") or ""
        mode = input_node.findtext("mode") or ""
        root_action_id = input_node.findtext("./action-configuration/root-action")
        if not root_action_id:
            continue

        key = (device_id, input_type, input_id)
        if key not in controls:
            controls[key] = {
                "device_id": device_id,
                "device": devices.get(device_id, device_id),
                "input_type": input_type,
                "input_id": input_id,
                "mode_actions": {mode_name: [] for mode_name in modes},
                "mode_notes": {mode_name: [] for mode_name in modes},
                "mode_targets": {mode_name: [] for mode_name in modes},
                "vjoy_targets": [],
            }

        control = controls[key]
        mode_actions = control["mode_actions"]
        mode_notes = control["mode_notes"]
        mode_targets = control["mode_targets"]
        vjoy_targets = control["vjoy_targets"]
        mode_actions.setdefault(mode, [])
        mode_notes.setdefault(mode, [])
        mode_targets.setdefault(mode, [])
        mode_actions[mode].extend(summarize_action(root_action_id, actions))
        mode_notes[mode].extend(
            collect_descriptions(root_action_id, actions)
        )
        for target in collect_vjoy_targets(root_action_id, actions):
            if target not in vjoy_targets:
                vjoy_targets.append(target)
            if target not in mode_targets[mode]:
                mode_targets[mode].append(target)

    ordered_controls = sorted(
        controls.values(),
        key=lambda control: (
            str(control["device_id"]),
            TYPE_ORDER.get(str(control["input_type"]), 99),
            int(str(control["input_id"]))
            if str(control["input_id"]).isdigit()
            else str(control["input_id"]),
        ),
    )

    fieldnames = [
        "Device",
        "Input Name",
        "Control Type",
        "Control ID",
        "Target VJoy Index",
        "Target Button ID",
        *modes,
        "Notes",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for control in ordered_controls:
            row = {
                "Device": control["device"],
                "Input Name": control_name(control),
                "Control Type": str(control["input_type"]).capitalize(),
                "Control ID": control["input_id"],
            }

            target_indices = deduplicate(
                str(index)
                for index, _input_type, _input_id in control["vjoy_targets"]
            )
            button_ids = deduplicate(
                str(input_id)
                for _index, input_type, input_id in control["vjoy_targets"]
                if input_type.lower() == "button"
            )

            def numeric_sort(values: list[str]) -> list[str]:
                return sorted(
                    values,
                    key=lambda value: int(value) if value.isdigit() else 10**9,
                )

            row["Target VJoy Index"] = " | ".join(numeric_sort(target_indices))
            row["Target Button ID"] = " | ".join(numeric_sort(button_ids))

            def effective_action_text(
                mode_name: str,
                seen_modes: set[str] | None = None,
            ) -> str:
                if seen_modes is None:
                    seen_modes = set()
                if mode_name in seen_modes:
                    return ""

                seen_modes = seen_modes.copy()
                seen_modes.add(mode_name)
                direct_actions = deduplicate(control["mode_actions"][mode_name])
                if direct_actions:
                    return " | ".join(direct_actions)

                parent = parents.get(mode_name)
                if parent:
                    return effective_action_text(parent, seen_modes)
                return ""

            def effective_vjoy_targets(
                mode_name: str,
                seen_modes: set[str] | None = None,
            ) -> list[tuple[str, str, str]]:
                if seen_modes is None:
                    seen_modes = set()
                if mode_name in seen_modes:
                    return []

                seen_modes = seen_modes.copy()
                seen_modes.add(mode_name)
                direct_targets = deduplicate_targets(
                    control["mode_targets"][mode_name]
                )
                if direct_targets:
                    return direct_targets

                parent = parents.get(mode_name)
                if parent:
                    return effective_vjoy_targets(parent, seen_modes)
                return []

            for mode_name in modes:
                direct_actions = deduplicate(control["mode_actions"][mode_name])
                direct_text = " | ".join(direct_actions)

                if direct_text:
                    parent = parents.get(mode_name)
                    direct_targets = deduplicate_targets(
                        control["mode_targets"][mode_name]
                    )
                    parent_targets = (
                        effective_vjoy_targets(parent) if parent else []
                    )
                    same_target = (
                        bool(direct_targets)
                        and set(direct_targets) == set(parent_targets)
                    )
                    same_action_text = (
                        bool(parent)
                        and effective_action_text(parent) == direct_text
                    )
                    if same_target or same_action_text:
                        row[mode_name] = "inherit"
                    else:
                        row[mode_name] = direct_text
                    continue

                parent = parents.get(mode_name)
                if parent and effective_action_text(parent):
                    row[mode_name] = "inherit"
                else:
                    row[mode_name] = "unassigned"

            notes: list[str] = []
            for mode_name in modes:
                for note in deduplicate(control["mode_notes"][mode_name]):
                    notes.append(f"{mode_name}: {note}")
            row["Notes"] = " || ".join(deduplicate(notes))
            writer.writerow(row)

    return len(ordered_controls), profile_format


def default_output_path(source: Path) -> Path:
    return source.with_name(f"{source.stem}_bindings.csv")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auto-detect and export Joystick Gobloon or Gremlin XML bindings."
    )
    parser.add_argument("profile", type=Path, help="Joystick Gobloon or Gremlin XML profile")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output CSV path (default: <profile>_bindings.csv)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output = args.output or default_output_path(args.profile)
    try:
        control_count, profile_format = export_profile(args.profile, output)
    except (ET.ParseError, OSError, ValueError) as error:
        print(f"jg2csv: error: {error}", file=sys.stderr)
        return 1

    print(f"Detected {profile_format}; exported {control_count} controls to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
