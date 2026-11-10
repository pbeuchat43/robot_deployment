"""Operator help for the deployment adapter; runtime retains its own grammar."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import argparse


DETAILS = {
    "install": ("Build and select a verified release without starting applications.",
        "install --site /absolute/site.yaml --release-id release-a --stage-only",
        "Needs the admitted host, installed prerequisites, free disk space and access to exact sources. "
        "Omit --stage-only to select after validation. Existing workloads must be stopped for selection. "
        "A failed/partial stage is retained: inspect its log and use a new release ID. --no-shell skips shell setup."),
    "upgrade": ("Stage an explicit new selection and switch only with stopped ownership.",
        "upgrade --site /absolute/site.yaml --release-id release-b --stage-only",
        "Use a new bootstrap for the intended source selection. Stop applications before selecting. "
        "No apt, firmware or base-image change is implicit. A failed build leaves the selected release intact."),
    "rollback": ("Select a retained, verified compatible application release.",
        "rollback --release-id release-a",
        "Without --release-id use the recorded predecessor. Stop applications first. Exact host packages, "
        "artifacts and runtime state must remain compatible. This does not undo apt, firmware or student edits."),
    "config": ("Inspect, validate or render the declared configuration.", "config validate --site /absolute/site.yaml",
        "Reads trusted definitions and permitted student requests. Credential references are shown; contents are never read."),
    "config validate": ("Validate startup inputs without opening hardware or contacting runtime.",
        "config validate --site /absolute/site.yaml", "Unknown keys, invalid bounds and unsupported selections fail. Correct the named input and retry."),
    "config show": ("Show validated settings and admitted student parameter requests.",
        "config show --site /absolute/site.yaml --json", "Shows credential paths only. Request edits take effect on the next explicit start or restart."),
    "config render": ("Write a runtime profile for a declared installed release.",
        "config render --site /absolute/site.yaml --release /absolute/release --output /absolute/runtime.json",
        "Requires installed component/model paths. Rendering does not select the profile or restart workloads. "
        "Structural changes require a new release and stopped maintenance."),
    "host": ("Write reviewable privileged host preparation plans.", "host plan --site /absolute/site.yaml --output /absolute/packages.json",
        "These commands write new files and never invoke sudo. Inspect generated scripts before applying them explicitly."),
    "host plan": ("Resolve exact prerequisites and simulate the missing-package transaction.",
        "host plan --site /absolute/site.yaml --output /absolute/packages.json",
        "Needs apt metadata for the selected platform. Writes JSON and a sibling .sh; neither is applied. "
        "Package removals/BSP changes fail. Refresh repositories or correct the platform before replanning."),
    "host repositories": ("Write the pinned ROS repository bootstrap script.",
        "host repositories --output /absolute/ros-repositories.sh",
        "Use on the selected base image when its ROS repository is absent. Output must not exist. This does not replace NVIDIA or Ubuntu repositories."),
    "host setup": ("Write account, storage and compatible-camera USB permission setup.",
        "host setup --site /absolute/site.yaml --output /absolute/host-setup.sh",
        "The generated script refuses conflicting files and unowned nonempty storage. It does not start services. Replug cameras after applying USB rules."),
    "info": ("Inspect host or declared installation/firmware metadata.", "info installation",
        "No camera is opened and no firmware is flashed. Host inspection reads system identity; other routes need local site context."),
    "info host": ("Read architecture, module/carrier, operating system and package identity.", "info host --json",
        "Requires local Linux host metadata; it does not install packages or claim hardware qualification."),
    "info installation": ("Read the selected release and its recorded provenance.", "info installation --json",
        "Requires local site context. Recorded installation success does not establish camera readiness. Use doctor to verify current artifact integrity."),
    "info mcu": ("Show the explicitly selected firmware recipe and tool versions.", "info mcu bno08x",
        "No USB discovery occurs. The default composition has no firmware: declare a supported exact recipe before installation/build."),
    "doctor": ("Verify installed artifacts and report fresh runtime ownership.", "doctor --json",
        "Needs a selected release. A stopped/unreachable manager is reported separately from artifact integrity. "
        "It never opens cameras or repairs state; inspect reported failures before maintenance."),
    "build": ("Build a selected ROS workspace or MCU firmware explicitly.", "build ros student",
        "Needs a completed installation and the relevant source/toolchain. Builds run in the foreground; no dependency installation, flashing or runtime restart is implicit."),
    "build ros": ("Build pinned system sources or the bound student workspace.", "build ros student --clean",
        "Student sources live under the declared workspace/src. Outputs use owned separate directories. "
        "--clean removes only generated build/install/log output and preserves sources. Use it after changing the underlay."),
    "build mcu": ("Build the selected board's component-owned firmware bundle.", "build mcu bno08x",
        "Needs the declared firmware recipe and installed Pico tools. Output includes a manifest for an explicit later flash; no device is accessed."),
    "flash": ("Invoke one component-owned firmware operation for an explicit target.",
        "flash mcu bno08x --device-id TARGET --manifest /absolute/bundle.manifest.json",
        "Requires an installed selected firmware recipe, a matching manifest and the actual USB target. Component identity checks and confirmation prompts remain in force."),
    "flash mcu": ("Flash one explicitly identified MCU using its owning tool.",
        "flash mcu bno08x --device-id TARGET --manifest /absolute/bundle.manifest.json",
        "This changes device firmware. RC Car needs physical BOOTSEL and --actuators-isolated. BNO and RC Car support --report. Traxxas reports to stdout. "
        "An incompatible board/manifest is rejected: select or rebuild the correct bundle, never force it."),
    "pico": ("Inspect Pico USB inventory or access an unowned RC Car Pico.",
        "pico list --json", "The list command reads kernel metadata without opening a serial device."),
    "pico rc-car": ("Read RCPv1 status or request Manual or Hold on an unowned Pico.",
        "pico rc-car mode manual", "Direct access opens an exclusive session. When the interface is running, use the declared runtime ROS capabilities. "
        "Managed mode changes require stopped maintenance. Use --standalone and --client for an independent bench."),
    "shell": ("Manage owned Bash command exposure, completion and optional alias.", "shell install --alias",
        "Requires a selected installation. Preserves unrelated startup content and refuses edited/unowned managed files."),
    "shell install": ("Install the full command and completion, optionally the lucid alias.", "shell install --alias",
        "The alias is opt-in; conflicts leave it uninstalled. Load the reported snippet or open a new Bash session. "
        "No component rebuild or runtime change occurs."),
    "shell remove": ("Remove only this installation's unmodified Bash integration.", "shell remove",
        "Leaves components and runtime state intact. Open a new Bash session to clear already loaded aliases and completion."),
}


def describe(parser):
    # argparse retains the root program followed by canonical subcommands. Match
    # the longest known suffix so custom program names and module entry points work.
    words = parser.prog.split()
    key = next((" ".join(words[-size:]) for size in (2, 1)
                if " ".join(words[-size:]) in DETAILS), None)
    runtime = "runtime" in words[1:]
    if key and not runtime:
        purpose, example, detail = DETAILS[key]
        parser.description = purpose
        parser.epilog = detail + "\n\nExample: lucid_conduct " + example
    elif runtime:
        parser.epilog = ("Uses the standalone robot_runtime parser and lifecycle policy. Start/restart acceptance "
            "is asynchronous; inspect the returned request ID with runtime operation. Invalid preparation "
            "keeps the old run. Use runtime catalog for local units/modes and runtime status --fresh for ownership.\n\n"
            "Example: lucid_conduct runtime catalog\nExample: lucid_conduct runtime start perception --mode d455-both")
    else:
        parser.epilog = "Example: lucid_conduct install --site /absolute/site.yaml --stage-only\nExample: lucid_conduct runtime catalog"
    parser.epilog += ("\n\nDeployment output uses readable fields; --json selects structured output. Runtime preserves its "
        "standalone JSON. Success exits 0; validation errors exit 2 with a JSON error on stderr; "
        "foreground tool failure/signal status is propagated. --show-call explains immediate dispatch without execution. "
        "Without --site, use ROBOT_DEPLOYMENT_SITE or recorded local installation context. "
        "See docs/operations.md for installation and recovery procedures.")
    parser.formatter_class = argparse.RawDescriptionHelpFormatter
