"""Shared operator entry point; routes retain their component owners."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import argparse
import importlib
import json
from pathlib import Path
import sys

from . import __version__


def build_parser(prog=None):
    parser = argparse.ArgumentParser(prog=prog, description="Install, configure and operate a selected robot deployment")
    parser.add_argument("--version", action="version", version=__version__)
    families = parser.add_subparsers(dest="family", required=True)
    for name in ("install", "upgrade"):
        command = families.add_parser(name, help="Stage verified sources/artifacts and select a complete release; starts no application workloads")
        command.add_argument("--deployment-wheel", type=Path, help="Bootstrap or selected deployment wheel")
        command.add_argument("--source-cache", type=Path, help="Explicit directory of exact local repositories or NAME.bundle files")
        command.add_argument("--release-id", help="New release identity, or retry an unchanged completed stage")
        command.add_argument("--stage-only", action="store_true", help="Build and validate without selecting or changing management")
        command.add_argument("--no-shell", action="store_true", help="Leave command exposure and interactive shell setup alone")
    config = families.add_parser("config", help="Validate private choices and delegated startup requests")
    configs = config.add_subparsers(dest="config_action", required=True)
    configs.add_parser("validate", help="Validate inputs without IPC, network or hardware")
    configs.add_parser("show", help="Show validated non-secret settings and credential references")
    render = configs.add_parser("render", help="Write a new runtime profile for an installed release")
    render.add_argument("--release", type=Path, required=True)
    render.add_argument("--output", type=Path, required=True)
    host = families.add_parser("host", help="Inspect or prepare declared privileged host prerequisites")
    hosts = host.add_subparsers(dest="host_action", required=True)
    prerequisites = hosts.add_parser("plan", help="Resolve exact package versions and write the reviewed root script")
    prerequisites.add_argument("--output", type=Path, required=True)
    repositories = hosts.add_parser("repositories", help="Write the pinned fresh-host ROS repository setup script")
    repositories.add_argument("--output", type=Path, required=True)
    setup = hosts.add_parser("setup", help="Write account, storage and compatible-device permissions script")
    setup.add_argument("--output", type=Path, required=True)
    info = families.add_parser("info", help="Inspect local installation metadata or host identity")
    infos = info.add_subparsers(dest="info_action", required=True)
    infos.add_parser("installation")
    infos.add_parser("host")
    mcu_info = infos.add_parser("mcu")
    mcu_info.add_argument("target", choices=("bno08x", "traxxas", "rc-car"))
    families.add_parser("doctor", help="Check configuration, installed integrity and runtime ownership; never opens cameras")
    build = families.add_parser("build", help="Explicit foreground component/workspace build; no automatic restart")
    builds = build.add_subparsers(dest="build_kind", required=True)
    ros = builds.add_parser("ros")
    ros.add_argument("workspace", choices=("system", "student"))
    ros.add_argument("--clean", action="store_true", help="Clean only this build's owned generated outputs")
    mcu = builds.add_parser("mcu")
    mcu.add_argument("target", choices=("bno08x", "traxxas", "rc-car"))
    flash = families.add_parser("flash", help="Explicit single-target firmware operation using component-owned checks")
    flashes = flash.add_subparsers(dest="flash_kind", required=True)
    mcu_flash = flashes.add_parser("mcu")
    mcu_flash.add_argument("target", choices=("bno08x", "traxxas", "rc-car"))
    mcu_flash.add_argument("--device-id", required=True)
    mcu_flash.add_argument("--manifest", required=True, type=Path)
    mcu_flash.add_argument("--report", type=Path)
    mcu_flash.add_argument("--usb-port", help="Physical USB path from pico list (RC Car only)")
    mcu_flash.add_argument("--actuators-isolated", action="store_true", help="Confirm actuator isolation before RC Car flash")
    pico = families.add_parser("pico", help="List Picos and operate an unowned RC Car USB port")
    picos = pico.add_subparsers(dest="pico_target", required=True)
    picos.add_parser("list", help="Read kernel USB inventory without opening a serial port")
    car = picos.add_parser("rc-car")
    actions = car.add_subparsers(dest="pico_action", required=True)
    for name, description in (
        ("status", "Read one fresh firmware status"), ("watch", "Stream fresh firmware status"),
        ("mode", "Request Manual or Hold"), ("doctor", "Diagnose selection, access and link issues"),
    ):
        command = actions.add_parser(name, help=description)
        command.add_argument("--standalone", action="store_true", help="Use an independently built bench client")
        command.add_argument("--client", type=Path, help="Absolute path to rc_car_ctl on a standalone bench")
        command.add_argument("--device-id")
        command.add_argument("--profile-id")
        command.add_argument("--build-id")
        if name == "mode":
            command.add_argument("mode_choice", choices=("manual", "hold"))
        if name == "watch":
            command.add_argument("--duration", type=int, default=30, help="Seconds of output, from 1 to 600")
    calibrate = families.add_parser("calibrate", help="Run a stopped, model-specific actuator calibration")
    calibrations = calibrate.add_subparsers(dest="calibration_target", required=True)
    traxxas = calibrations.add_parser("traxxas")
    escs = traxxas.add_subparsers(dest="calibration_kind", required=True)
    esc = escs.add_parser("esc", help="Program an ESC over an exclusive RCPv1 maintenance session")
    esc.add_argument("--device-id", required=True)
    esc.add_argument("--profile-id", required=True)
    esc.add_argument("--build-id", required=True)
    esc.add_argument("--maintenance-client", required=True, type=Path)
    esc.add_argument("--esc", choices=("xl-5", "vxl-3s"), required=True)
    esc.add_argument("--neutral-us", type=int, default=1500)
    esc.add_argument("--forward-us", type=int, default=2000)
    esc.add_argument("--reverse-us", type=int, default=1000)
    rollback = families.add_parser("rollback", help="Select a verified compatible prior release; does not undo apt, firmware or image changes")
    rollback.add_argument("--release-id")
    shell = families.add_parser("shell", help="Manage owned Bash command exposure, completion and optional alias")
    shells = shell.add_subparsers(dest="shell_action", required=True)
    shell_install = shells.add_parser("install")
    shell_install.add_argument("--alias", action="store_true", help="Request the optional short Bash alias")
    shells.add_parser("remove")
    runtime = families.add_parser("runtime", help="Use robot_runtime's shared standalone grammar and policy")
    from robot_runtime.cli import configure_parser
    configure_parser(runtime)
    add_common(parser)
    return parser


def child_parsers(parser):
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            yield from dict.fromkeys(action.choices.values())


def add_common(parser):
    parser.add_argument("--site", type=Path, default=argparse.SUPPRESS, help="Private site YAML/JSON; otherwise use installation context")
    parser.add_argument("--definitions", type=Path, default=argparse.SUPPRESS, help="Explicit trusted definition root")
    parser.add_argument("--show-call", action="store_true", default=argparse.SUPPRESS,
                        help="Explain this actual route without executing, probing or contacting runtime")
    parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                        help="Emit structured JSON; standalone runtime output is always preserved")
    from .help import describe
    describe(parser)
    for child in child_parsers(parser):
        add_common(child)


def strip_common(argv):
    result = []
    iterator = iter(argv)
    for value in iterator:
        if value in ("--site", "--definitions"):
            next(iterator, None)
        elif value in ("--show-call", "--json") or value.startswith(("--site=", "--definitions=")):
            continue
        else:
            result.append(value)
    return result


def route(args, argv):
    """The same trusted call object supplies explanation and actual dispatch."""
    common = dict(site_path=getattr(args, "site", None), definitions=getattr(args, "definitions", None))
    family = args.family
    if family == "runtime":
        from .commands import runtime_argv
        return "robot_runtime.cli:main", dict(argv=runtime_argv(strip_common(argv)[1:], common["site_path"]))
    if family == "pico" and args.pico_target == "list":
        return "robot_deployment.pico:listing", {}
    if family == "pico" and args.standalone:
        return "robot_deployment.pico:operate", pico_args(args, common)
    from .commands import resolve_site
    if not (family == "info" and args.info_action == "host") and not (family == "host" and args.host_action == "repositories"):
        common["site_path"] = resolve_site(common["site_path"], optional=True)
    if family in ("install", "upgrade"):
        return "robot_deployment.commands:install", dict(common, deployment_wheel=args.deployment_wheel,
            source_cache=args.source_cache, release_id=args.release_id, stage_only=args.stage_only, no_shell=args.no_shell)
    if family == "config":
        return "robot_deployment.commands:config", dict(common, action=args.config_action,
            **(dict(release=args.release, output=args.output) if args.config_action == "render" else {}))
    if family == "host":
        return "robot_deployment.commands:host", dict(common, action=args.host_action, output=args.output)
    if family == "info":
        target = getattr(args, "target", None)
        return "robot_deployment.commands:info", dict(common, action=args.info_action,
            target="rc_car" if target == "rc-car" else target)
    if family == "doctor":
        return "robot_deployment.commands:doctor", common
    if family == "build":
        return "robot_deployment.build:ros" if args.build_kind == "ros" else "robot_deployment.firmware:build", dict(common,
            **(dict(workspace=args.workspace, clean=args.clean) if args.build_kind == "ros" else
               dict(target="rc_car" if args.target == "rc-car" else args.target)))
    if family == "flash":
        if args.target == "rc-car":
            return "robot_deployment.firmware:flash_rc_car", dict(common, device_id=args.device_id,
                manifest=args.manifest, report=args.report, usb_port=args.usb_port,
                actuators_isolated=args.actuators_isolated)
        if args.usb_port or args.actuators_isolated:
            raise ValueError("--usb-port and --actuators-isolated are RC Car flash options")
        return "robot_deployment.firmware:flash", dict(common, target=args.target, device_id=args.device_id,
            manifest=args.manifest, report=args.report)
    if family == "pico":
        return "robot_deployment.pico:operate", pico_args(args, common)
    if family == "calibrate":
        return "robot_deployment.calibration:calibrate", dict(common, device_id=args.device_id,
            profile_id=args.profile_id, build_id=args.build_id, maintenance_client=args.maintenance_client, esc=args.esc,
            neutral_us=args.neutral_us, forward_us=args.forward_us, reverse_us=args.reverse_us)
    if family == "rollback":
        return "robot_deployment.commands:rollback", dict(common, release_id=args.release_id)
    if family == "shell":
        return "robot_deployment.commands:shell", dict(common, action=args.shell_action, alias=getattr(args, "alias", False))
    raise ValueError("Unknown command route")


def pico_args(args, common):
    standalone = args.standalone or (args.pico_action == "doctor" and common["site_path"] is None and
                                     common["definitions"] is None)
    return dict(common, action=getattr(args, "mode_choice", args.pico_action), standalone=standalone,
        client=args.client, device_id=args.device_id, profile_id=args.profile_id, build_id=args.build_id,
        duration=getattr(args, "duration", 30), structured=getattr(args, "json", False))


def complete(words):
    """Read parser and local metadata only. No route is dispatched."""
    parser = build_parser()
    prefix = words[-1] if words else ""
    previous = words[:-1]
    waiting = None
    positionals = []
    for token in previous:
        if waiting:
            waiting = None
            continue
        action = next((item for item in parser._actions if token in item.option_strings), None)
        if action:
            if action.nargs != 0:
                waiting = action
            continue
        choices = next((item.choices for item in parser._actions if isinstance(item, argparse._SubParsersAction)), {})
        if token in choices:
            parser = choices[token]
        else:
            positionals.append(token)
    if waiting and waiting.choices:
        candidates = list(map(str, waiting.choices))
    elif waiting:
        candidates = []
    else:
        candidates = [flag for action in parser._actions for flag in action.option_strings]
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                candidates.extend(action.choices)
            elif not action.option_strings and action.choices:
                candidates.extend(map(str, action.choices))
    if "runtime" in previous:
        from .commands import local_catalog
        try:
            site = Path(previous[previous.index("--site") + 1]) if "--site" in previous else None
            catalog = local_catalog(site)
            if waiting and waiting.dest == "mode":
                unit = next((unit for unit in catalog if unit["id"] in previous), None)
                candidates.extend(mode["id"] for mode in (unit or {}).get("launch_modes", []))
            elif not waiting and any(item in previous for item in ("start", "stop", "restart", "log", "logs")):
                candidates.extend(unit["id"] for unit in catalog)
        except (ValueError, OSError, KeyError):
            pass
    return sorted({item for item in candidates if item.startswith(prefix)})


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["_complete"]:
        words = argv[1:]
        if words[:1] == ["--"]:
            words = words[1:]
        candidates = complete(words)
        if candidates:
            print("\n".join(candidates))
        return 0
    parser = build_parser()
    try:
        cleaned = strip_common(argv)
        if cleaned[:2] == ["runtime", "catalog"] and not any(value in ("--help", "-h", "--profile") or value.startswith("--profile=") for value in argv):
            context_parser = argparse.ArgumentParser(add_help=False)
            context_parser.add_argument("--site", type=Path)
            context, _remaining = context_parser.parse_known_args(argv)
            from .commands import resolve_site
            from .configuration import Inputs
            selected_site = resolve_site(context.site, optional=True)
            if selected_site:
                site = Inputs().read(selected_site)
                argv += ["--profile", str(Path(site["storage"]["installation_root"]) / "current/runtime.json")]
        args = parser.parse_args(argv)
        target, arguments = route(args, argv)
        if getattr(args, "show_call", False):
            explanation = dict(owner=target.split(".", 1)[0], entry_point=target,
                interpreter=sys.executable, arguments=arguments, executed=False)
            if target == "robot_runtime.cli:main":
                explanation["argv"] = [sys.executable, "-m", "robot_runtime.cli", *arguments["argv"]]
            else:
                # These are in-process Python callables, not executable modules.
                # The CLI argv reproduces the immediate dispatch, not every later
                # build tool or asynchronous supervisor action.
                explanation["argv"] = [sys.executable, "-m", "robot_deployment.cli",
                    *strip_common(argv)]
                for option, key in (("--site", "site_path"), ("--definitions", "definitions")):
                    if arguments.get(key) is not None:
                        explanation["argv"] += [option, str(arguments[key])]
                if "site_path" in arguments and arguments["site_path"] is None and not arguments.get("standalone") and not (
                    args.family == "info" and args.info_action == "host" or
                    args.family == "host" and args.host_action == "repositories"
                ):
                    explanation["unresolved_context"] = "Provide --site or configure local installation context before execution"
            emit(explanation, structured=getattr(args, "json", False))
            return 0
        module, function = target.split(":", 1)
        result = getattr(importlib.import_module(module), function)(**arguments)
        if isinstance(result, int):
            return result
        if result is not None:
            emit(result, structured=getattr(args, "json", False))
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        from robot_runtime.common import Fault
        import subprocess
        if isinstance(exc, Fault):
            error = exc.as_dict()
        else:
            error = dict(code="deployment_error", message=str(exc))
        print(json.dumps(dict(error=error)), file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError):
            return exc.returncode if exc.returncode > 0 else 128 - exc.returncode
        return 2


def emit(value, *, structured):
    if structured:
        print(json.dumps(value, default=str, indent=2))
        return
    if not isinstance(value, dict):
        print(value)
        return
    for key, item in value.items():
        label = key.replace("_", " ").capitalize()
        if isinstance(item, (dict, list)):
            print(label + ":\n" + json.dumps(item, default=str, indent=2))
        else:
            text = "yes" if item is True else "no" if item is False else "none" if item is None else str(item)
            print(label + ": " + text)


if __name__ == "__main__":
    raise SystemExit(main())
