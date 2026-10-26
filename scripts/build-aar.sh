#!/usr/bin/env bash
set -euo pipefail
# Only GitHub-hosted Linux x64 Actions runners may produce published AARs.
# External self-hosted build servers, including NAS/SSH agents, are rejected.
if [[ "${GITHUB_ACTIONS:-}" != true || "${RUNNER_ENVIRONMENT:-}" != github-hosted ||
      "${RUNNER_OS:-}" != Linux || "${RUNNER_ARCH:-}" != X64 ]]; then
  echo "::error::This release builder requires a GitHub-hosted Ubuntu x64 Actions runner." >&2
  exit 1
fi
: "${GITHUB_RUN_ID:?}"
: "${RELEASE_TAG:?}"
: "${RELEASE_SHA:?}"

mkdir -p dist
export PATH="$(go env GOPATH)/bin:$PATH"
export CGO_ENABLED=1
# Android 16 KiB devices require load segments aligned to at least 16384 bytes.
export CGO_LDFLAGS="-Wl,-z,max-page-size=16384"

# Upstream checkout stays pristine in the repository: copy our shim into
# the temporary checkout before invoking gomobile. Refuse to overwrite
# an upstream file if future versions introduce the same filename.
target="librclone/gomobile/ckreader_range.go"
test ! -e "$target" || { echo "::error::Upstream already contains $target"; exit 1; }
cp ../builder/scripts/ckreader_range.go "$target"
gofmt -w "$target"
for name in RcloneStatSize RcloneReadRange; do
  grep -q "^func $name(" "$target" || {
    echo "::error::Missing required Go binding: $name"
    exit 1
  }
done

go install golang.org/x/mobile/cmd/gobind@latest
go install golang.org/x/mobile/cmd/gomobile@latest
gomobile init

output="dist/rclone-${RELEASE_TAG}-android.aar"
gomobile bind -v -target=android -androidapi 23 -javapkg=org.rclone \
  -ldflags="-s -w -X github.com/rclone/rclone/fs.Version=$RELEASE_TAG -extldflags=-Wl,-z,max-page-size=16384" \
  -o "$output" github.com/rclone/rclone/librclone/gomobile

unzip -tq "$output"
unzip -Z1 "$output" > dist/AAR_CONTENTS.txt
grep -Fxq classes.jar dist/AAR_CONTENTS.txt
# Only ARM64 is a required compatibility target. Other architectures may
# still be present in the AAR but do not block publishing when unverified.
grep -Fxq "jni/arm64-v8a/libgojni.so" dist/AAR_CONTENTS.txt || {
  echo "::error::AAR missing arm64-v8a/libgojni.so"
  exit 1
}
# Fail the build (and block upload/publish) if the ARM64 ELF/JNI compatibility
# gate fails. Java API method/signature checks are shared across all ABIs.
python3 ../builder/scripts/verify-aar.py "$output" dist/AAR_VERIFICATION.json

(cd dist && sha256sum "$(basename "$output")" > SHA256SUMS && sha256sum -c SHA256SUMS)
printf 'upstream=wiserain/rclone\ntag=%s\ncommit=%s\nbindings=ckreader-stat-range\npage_alignment=16384\nverification_abi=arm64-v8a\nrunner_environment=%s\nrunner_os=%s\nrunner_arch=%s\ngithub_actions_run_id=%s\n' \
  "$RELEASE_TAG" "$RELEASE_SHA" "$RUNNER_ENVIRONMENT" "$RUNNER_OS" "$RUNNER_ARCH" "$GITHUB_RUN_ID" > dist/BUILD_INFO.txt
{
  echo "## ckReader-compatible Android AAR"
  echo "- Upstream version: $RELEASE_TAG"
  echo "- Source commit: $RELEASE_SHA"
  echo "- JNI and 16 KiB ELF checks: PASS (arm64-v8a only)"
  echo "- Other ABIs: not compatibility-verified"
  echo "- Build runner: $RUNNER_ENVIRONMENT / $RUNNER_OS / $RUNNER_ARCH"
  echo "- GitHub Actions run: $GITHUB_RUN_ID"
  cat dist/SHA256SUMS
} >> "$GITHUB_STEP_SUMMARY"
