# RP2040-Zero bare-board verification, 15 November 2026

The operator identified the attached board as a Waveshare RP2040-Zero, powered
only by USB with nothing else connected. It was discovered in physical BOOTSEL
on reserved Jah. Its existing RC application passed identity, USB status and
Hold/Manual checks. **No flash was written.** The board was left in Hold for
the current boot, and Jah's everyday perception deployment was restored unchanged.

The [redacted numeric record](summary.json) contains exact source selections,
artifact hashes, original comparison outcome, protocol observations and evidence
limits. This supplements the earlier
[recording and RC build verification](../2026-11-11-consolidation/README.md).

## Preparation and existing flash

The private tool build used these unchanged published component selections:

| Component | Commit |
| --- | --- |
| RC firmware | `f25b331810f56f4ca61dfe201e129046b4ed557b` |
| RC interface | `1903b9524a82255b2a230cdc26cb5bf255487210` |
| Pico SDK 2.3.1 | `079c6f39023649b154152db30f1d781e884879bc` |
| picotool 2.3.1 | `2041936441b48a3cc53ae3da9e805229fe8f4e18` |

SDK submodule identities were verified. USB-enabled picotool and the standalone
RC client built successfully, and the Linux transport CTest passed. The RP2040
bundle used the unchanged `profiles/research_car.example.hpp` bench profile:

- Board: `waveshare_rp2040_zero`; protocol: `RCPv1`.
- Profile ID: `a6b661b9f16e61b3`; build ID: `81bfd20e371a38fc`.
- Rebuilt UF2 SHA-256:
  `794905f12811ffb8a37012ee7564e31a55c1be9f2bcb18774decc068a25c864c`.

Both IDs match the earlier consolidated build. These IDs describe the selected
source/profile inputs; they do not imply byte-identical artifacts across dates.

Address-scoped picotool inspection established the RP2040 flash identity and
reported the correct board, SDK 2.3.1 and a Release build dated 8 November.
`save -a -v` preserved and verified all 2 MiB of flash as a 4 MiB UF2 before
reboot. The ROM USB serial and application flash identity were kept distinct.

A literal `picotool verify` against the rebuilt UF2 **reported a mismatch**.
Comparing all 70,656 payload bytes covered by the rebuilt image localized it to
exactly two bytes in the embedded build date: `Nov  8 2026` versus
`Nov 15 2026`. The remaining covered bytes matched. The existing flash also
contained the expected protocol, build and profile identifiers. Consequently,
there was no reason to replace the existing application merely to change its
date. The failed literal comparison and detailed byte comparison are both retained.

## Observed bare-board behavior

With everyday workloads stopped, the existing application was rebooted and
verified at the same USB port. Fresh protocol status matched the BOOTSEL flash
identity and the expected board, build and profile.

| Request | Result | Fresh observed state |
| --- | --- | --- |
| Hold | OK, accepted and confirmed | HOLD / REQUESTED |
| Manual | OK, accepted and confirmed | NEUTRAL / RC_BAD |
| Hold | OK, accepted and confirmed | HOLD / REQUESTED |

With no receiver connected, firmware reported bad RC quality, no valid input
axes, no selected drive/steer source and 1500 microsecond programmed drive and
steer PWM values. The independent pan channel reported 1500 microseconds as well;
Hold does not disable pan.

Six independent USB sessions had distinct session tokens and the same boot
identity. A separate status query confirmed that Hold survived closing and
reopening the client. The five-second Hold watch received 126 fresh statuses
spanning 5,000 ms, with a maximum tick interval of 40 ms and zero invalid frames.
All mode requests received confirmed results; no uncertain mutation was retried.

## Final state and limits

The Pico remains in **Hold for the current boot**. This is not a persistent boot
configuration. All test clients exited. The installed `r20261115-dev` release
remained selected, both everyday management services returned enabled and active,
and application workloads were fresh, stopped and unblocked. An initial read-only
status poll during manager startup was retried until fresh status became
available. Host packages were unchanged and the shared test reservation was
released.

The RC vehicle unit is still not selected in the everyday composition. Exact
device/profile/build pins are now retained privately for later explicit RC
provisioning. This bench profile remains unqualified for an actual vehicle.
Receiver behavior, signal levels, physical PWM timing, ESC neutral, steering,
pan motion, actuator power and driving were not tested. Programmed PWM values
are firmware reports, not oscilloscope measurements. No RP2350 hardware or new
firmware implementation was tested in this follow-up.

Private tools, source snapshots, profile, manifests, logs, flash backup and
identity records remain under
`/home/poi/.local/state/robot-experiments/rc-pico-bench-20261115` on Jah.
Device and session identities and the raw flash image are excluded from Git.
The public record retains hashes linking observations to those private records.
