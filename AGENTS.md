# Repository guidance

This repository owns reproducible component/model selections, named camera and
video configurations, launch topology and system integration evidence. Acquisition
belongs to `rgbd_camera`; inference/model/spatial contracts belong to
`rgbd_object_detector`; supervision and media coordination belong to `robot_runtime`.

- Follow the user's Solo preferences. Preserve unrelated work and data.
- Work on feature/maintenance branches, normally from `dev`, with meaningful
  intermediate commits. Archive intermediate history before squash consolidation
  into `dev`. Do not promote `main` without an agreed coordinated milestone.
- Run execution checks only on reserved Jah using isolated files, processes,
  namespaces and ports. Inspect workloads before hardware use or deployment.
- Preserve a useful rollback copy before replacing a persistent deployment.
  A passing software check is not observed camera or display performance.
- Keep secrets, device-specific identity and private imagery out of source control.
- New material is MIT, copyright Paul N. Beuchat.

The initial repository is local; no remote has been created or published.
