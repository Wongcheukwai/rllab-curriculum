#!/bin/sh
parent_path=$( cd "$(dirname "${BASH_SOURCE}")" ; pwd -P )
gcc -E -CC $parent_path/../../../private/mujoco/1_22/osx/mujoco.h > /tmp/code_gen_mujoco.h
ruby $parent_path/codegen.rb /tmp/code_gen_mujoco.h #> $parent_path/mjtypes.py