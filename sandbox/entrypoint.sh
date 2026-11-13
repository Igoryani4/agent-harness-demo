#!/bin/bash
set -e
SUBDIR="${1:-.}"
M2="${M2_DIR:-/tmp/m2}"
mkdir -p "$M2" /tmp/work
cp -r /opt/m2-seed/. "$M2/" 2>/dev/null || true
cp -r /workspace/. /tmp/work/
cd "/tmp/work/${SUBDIR}"
export MAVEN_OPTS="-Djansi.passthrough=true -Dstyle.color=never"
mvn -B -o -Dmaven.repo.local="$M2/repository" test
