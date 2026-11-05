# CaptureDetections consolidation

Date: 6 November 2026 (Australia/Sydney).

The user approved squash-merging the four completed feature branches into `dev`,
deleting those branches, pushing `dev`, and creating the `robot_deployment`
GitHub repository. Existing `main` branches are unchanged; deployment continues
with `dev` as its published branch and has no `main` promotion in this change.
The active RC-car worktree and all unrelated branches remain outside this task.

## Source identity mapping

The original [verification record](README.md) and [summary](summary.json) retain
the exact revisions, artifact hashes and limitations of the Jah software checks.
The summary is unchanged. These are source-equivalence checks for consolidation,
not new execution, installed-artifact or hardware results.

| Repository | Recorded tested revision | Consolidated `dev` revision |
| --- | --- | --- |
| `rgbd_camera` | `b43cb999f57bb834b756a0eb7f7213b02bf249fc` | `e225ea79c885b29d54f1fee2861c9d3a25e60cb0` |
| `rgbd_object_detector` | `cda6e3efd6aa75b6581a95088c999c0e5df0c21f` | `68215056f36a423458c7968111ccfb6ff247e834` |
| `robot_runtime` | `36249160ead1f4f9bf67ad7f6ccf8497f883b651` | `3f50ffb006df7df4401370c31b5f2e0e625be96f` |
| `robot_deployment` | `400e3e5fd5a3f308e243c3da1f14ca08a163707c` | The commit introducing this record; resolve with the command below. |

```sh
git log --diff-filter=A --format=%H -- docs/evidence/2026-11-06-capture-detections/consolidation.md
```

The camera, detector and runtime squashes each have exactly the tree of their
completed feature tip. Relative to the recorded tested revision, each differs
only in `AGENTS.md`. Runtime's contribution here is guidance only; no runtime
regression suite was rerun or newly qualified by this change.

Deployment's `sources.json` selects the three consolidated commits above. Its
other differences from the tested revision are guidance, documentation and the
recorded evidence. Implementation, launch logic, tests, probe source and package
version are unchanged. No source URL, dependency, model selection or configuration
value changes with the repin. The final deployment squash has exactly the tree of
its updated feature branch, including this record and the publication metadata.

Git tree comparisons, scoped diffs, parsed component-pin validation, local
documentation references and whitespace checks establish this relationship.
Earlier compiled libraries, wheels and archives keep their recorded identities;
they are not relabelled as artifacts built from the consolidated commits.

## Publication and cleanup

Only `dev` is pushed. The completed `feature/capture-detections` branches in
camera, detector and deployment, and `feature/system-guidance` in runtime, are
removed after the resulting commits and remote heads are verified. No archive
branches, tags or bundles are created to retain their intermediate history.
The recorded commit IDs remain provenance even if intermediate commits later
become unreachable. This supersedes the earlier record's prospective archive
instruction in accordance with the user's global cleanup preference.

Publication does not deploy or restart the robot. The existing everyday release
and earlier hardware evidence retain their original interfaces and identities.
