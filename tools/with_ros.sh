#!/usr/bin/env bash
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
set -eo pipefail
source /opt/ros/jazzy/setup.bash
source "${RGBD_SETUP:?Declare the pinned RGB-D install setup path}"
exec "$@"
