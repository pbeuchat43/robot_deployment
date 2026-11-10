"""Select/rerun an isolated completed release and exercise both ROS build routes.

Run using its matching bootstrap on reserved Jah. All declared storage and the
empty student workspace must be siblings under the private test output's parent.
Management and application workloads stay stopped; shell setup is skipped.
"""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from robot_deployment.configuration import load, require
from robot_deployment.records import write_json
from robot_deployment.services import active


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--source-cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--operator-python", type=Path,
                        help="Optional separately installed CLI to check against the same completed release")
    args = parser.parse_args(argv)
    output = args.output.resolve()
    site = load(args.site)["site"]
    installation = Path(site["storage"]["installation_root"]).resolve()
    data = Path(site["storage"]["data_root"]).resolve()
    student = Path(site["workspaces"]["student"]).resolve()
    require(all(path.is_relative_to(output.parent) and path != output.parent for path in (installation, data, student)),
            "Use isolated storage/workspace under the private test directory")
    require(site["runtime_namespace"] != "robot" and not site["management"]["start"] and not active(site),
            "Use a unique stopped test namespace with management.start false")
    record = data / "deployment/installations" / (args.release_id + ".json")
    require(json.loads(record.read_text()).get("result") == "succeeded", "Stage the complete selected release first")
    source = student / "src"
    require(not source.exists() or not any(source.iterdir()), "Student fixture needs an empty isolated src directory")
    output.mkdir(mode=0o700)
    env = dict(os.environ, XDG_CONFIG_HOME=str(output / "config"), XDG_STATE_HOME=str(output / "state"))
    env.pop("PYTHONPATH", None)
    report = dict(passed=False, checks=[], application_workloads_started=False, release_id=args.release_id)
    sequence = 0

    def invoke(argv):
        nonlocal sequence
        sequence += 1
        log = output / f"{sequence:02d}.log"
        with log.open("w") as stream:
            subprocess.run(list(map(str, argv)),
                           check=True, cwd=output, env=env, stdout=stream, stderr=subprocess.STDOUT)
        text = log.read_text()
        start = text.rfind("\n{")
        return json.loads(text[start + 1:] if start >= 0 else text)

    def cli(*arguments):
        return invoke([args.operator_python or sys.executable, "-m", "robot_deployment.cli", *arguments, "--json"])

    def select():
        # Installation uses the bootstrap/wheel identity frozen into this build.
        # A later presentation-only CLI can independently exercise the selected
        # release without rewriting that provenance or repeating native builds.
        return invoke([sys.executable, "-c",
            "import json, sys; from robot_deployment.commands import install; "
            "print(json.dumps(install(sys.argv[1], source_cache=sys.argv[2], release_id=sys.argv[3], no_shell=True)))",
            args.site, args.source_cache, args.release_id])

    try:
        release = installation / "releases" / args.release_id
        logs = release / "build/logs"
        before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in logs.iterdir() if path.is_file()}
        assert select()["selected"]
        selection = (data / "deployment/selection.json").read_bytes()
        assert select()["selected"]
        assert (data / "deployment/selection.json").read_bytes() == selection
        after = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in logs.iterdir() if path.is_file()}
        assert after == before and not active(site)
        report["checks"].append("completed_installer_rerun_reuses_artifacts_and_preserves_selection")
        assert cli("info", "installation")["selected"] == args.release_id
        assert cli("doctor")["installed_integrity"] == "passed"
        catalog = cli("runtime", "catalog")
        assert {unit["unit_id"] for unit in catalog["units"]} == {"perception", "video", "recording"}
        perception = next(unit for unit in catalog["units"] if unit["unit_id"] == "perception")
        assert {mode["id"] for mode in perception["launch_modes"]} == {
            camera + "-" + model for camera in ("oak", "d455") for model in ("camera", "cones", "coco", "both")}
        assert (release / "ros/install/lib/robot_runtime_recording/recording_node").is_file()
        explained = cli("runtime", "start", "perception", "--show-call")
        assert not explained["executed"] and explained["entry_point"] == "robot_runtime.cli:main"
        report["checks"].append("installed_context_catalog_doctor_and_call_explanation")
        system = cli("build", "ros", "system")
        assert Path(system["install"]).joinpath("share/rgbd_camera/package.xml").is_file()
        assert Path(system["install"]).joinpath("share/rgbd_object_detector/package.xml").is_file()
        assert Path(system["install"]).joinpath("lib/robot_runtime_recording/recording_node").is_file()
        assert not system["runtime_restarted"] and not system["dependencies_installed"]
        report["checks"].append("system_build_uses_separate_pinned_outputs")
        fixture = source / "robot_deployment_build_fixture"
        fixture.mkdir(parents=True)
        (fixture / "package.xml").write_text('<package format="3"><name>robot_deployment_build_fixture</name><version>0.0.0</version>'
            '<description>Isolated deployment build check</description><maintainer email="fixture@example.invalid">Fixture</maintainer>'
            '<license>MIT</license><buildtool_depend>ament_cmake</buildtool_depend><export><build_type>ament_cmake</build_type></export></package>\n')
        (fixture / "CMakeLists.txt").write_text('cmake_minimum_required(VERSION 3.16)\nproject(robot_deployment_build_fixture)\n'
            'find_package(ament_cmake REQUIRED)\ninstall(PROGRAMS fixture DESTINATION lib/${PROJECT_NAME})\nament_package()\n')
        executable = fixture / "fixture"
        executable.write_text("#!/bin/sh\nprintf '%s\\n' 'student build fixture'\n")
        executable.chmod(0o755)
        source_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in fixture.iterdir()}
        built = cli("build", "ros", "student")
        clean = cli("build", "ros", "student", "--clean")
        assert built["install"] == clean["install"] and not clean["runtime_restarted"]
        observed = subprocess.check_output([str(Path(clean["install"]) / "lib/robot_deployment_build_fixture/fixture")], text=True)
        assert observed.strip() == "student build fixture"
        assert {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in fixture.iterdir()} == source_hashes
        report["checks"].append("student_build_and_clean_preserve_sources_and_use_selected_underlay")
        assert not active(site)
        report["passed"] = True
    except BaseException as exc:
        report["error"] = repr(exc)
        raise
    finally:
        write_json(output / "report.json", report)
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
