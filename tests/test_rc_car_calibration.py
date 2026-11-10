import unittest
from unittest.mock import patch

from robot_deployment import calibration, cli


class FakeMaintenance:
    def __init__(self, hold=1500):
        self.events = []
        self.hold = hold

    def command(self, command, mode, drive=None, steer=None):
        self.events.append(command)
        if command == "HOLD" and drive != self.hold:
            raise ValueError("neutral mismatch")
        return drive, 1500


class CalibrationTests(unittest.TestCase):
    def test_cli_routes_to_deployment(self):
        arguments = [
            "calibrate", "traxxas", "esc", "--esc", "xl-5",
            "--site", "/tmp/rc-car-example-site.json",
            "--device-id", "123456789ABCDEF0", "--build-id", "build",
            "--profile-id", "profile", "--maintenance-client", "/tmp/example-helper",
        ]
        args = cli.build_parser().parse_args(arguments)
        entry, kwargs = cli.route(args, arguments)
        self.assertEqual(entry, "robot_deployment.calibration:calibrate")
        self.assertEqual((kwargs["neutral_us"], kwargs["forward_us"], kwargs["reverse_us"]),
                         (1500, 2000, 1000))

    def test_sequence_returns_to_neutral_hold(self):
        maintenance = FakeMaintenance()
        def cue(client, _, pulse, steering, deadline, *, terminal):
            client.command(f"PULSE {pulse}", "MAINTENANCE", pulse, steering)
        with patch.object(calibration.time, "sleep"), patch.object(calibration, "prompt_with_pulse", cue):
            calibration.program(maintenance, 1500, 2000, 1000, terminal=None)
        self.assertEqual(maintenance.events, ["HOLD", "ENTER", "PULSE 1500", "PULSE 2000",
                                        "PULSE 1000", "PULSE 1500", "EXIT"])

    def test_cancel_aborts_and_mismatched_neutral_never_enters(self):
        maintenance = FakeMaintenance()
        with patch.object(calibration.time, "sleep"), patch.object(calibration, "prompt_with_pulse",
                                                                   side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                calibration.program(maintenance, 1500, 2000, 1000, terminal=None)
        self.assertEqual(maintenance.events, ["HOLD", "ENTER", "ABORT"])
        wrong = FakeMaintenance(1490)
        with self.assertRaisesRegex(ValueError, "neutral mismatch"):
            calibration.program(wrong, 1500, 2000, 1000, terminal=None)
        self.assertEqual(wrong.events, ["HOLD"])


if __name__ == "__main__":
    unittest.main()
