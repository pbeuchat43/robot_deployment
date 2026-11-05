# Repository guidance

This repository is robot_deployment, evolved from robot_composition with its Git
history intact. It owns reproducible component/model selections, robot geometry,
named configurations, launch topology, host installation/build/maintenance,
the common CLI and system integration evidence. Image acquisition
belongs to `rgbd_camera`; inference/model/spatial contracts belong to
`rgbd_object_detector`; supervision and media coordination belong to `robot_runtime`.

For shared ownership and system boundaries, read the current
[system architecture](../robot_runtime/docs/research-platform-architecture.md)
in the corresponding runtime checkout. Sections labelled as original proposals
are historical context, not claims about current implementation.
Use `docs/operations.md` for installation/maintenance, `docs/configuration.md`
for configuration contracts, and `docs/launch.md` for topology, as relevant to
the change. Dated implementation plans record past work; they do not define
current task scope or authorization.
Public CLI naming is confined to entry points, shell integration and help/examples;
Python packages, configuration, state and services use neutral robot names.

- Follow the user's global workflow preferences. Preserve unrelated work and data.
- `main` is the verified baseline; `dev` is for development. Work on feature or
  maintenance branches from `dev`. Squash into `dev` after the user's finish
  confirmation. Promote `main` only with separate agreement on a coordinated
  milestone, then synchronize `dev`. Follow the user's global preferences for
  history retention and cleanup. Passing checks alone does not authorize promotion.
- Coordinate public interface/configuration changes with affected consumers.
  Update package/interface versions and `robot_deployment/sources.json` pins
  where required; record compatibility, rebuild requirements and tested revisions.
  Run focused checks on both sides of the changed contract within the authorized scope.
- Run execution checks only on reserved Jah (`ssh jah`), using isolated files,
  processes, ROS domains and ports as applicable. Local editing, Git operations
  and static inspection are allowed. Inspect workloads before hardware use or deployment.
- Preserve a useful rollback copy before replacing a persistent deployment.
- Record exact software/configuration identities and evidence limits. Synthetic
  or software checks do not establish observed hardware or display performance.
- Keep secrets, device-specific identity and private imagery out of source control.
- New material is MIT, copyright Paul N. Beuchat. Preserve third-party notices.

Verification commands and evidence limits are in `tests/README.md`.

The canonical repository is `https://github.com/pbeuchat43/robot_deployment`,
configured as `origin`. The published development branch is `dev`; creating or
promoting a verified `main` baseline remains a separate coordinated milestone.
