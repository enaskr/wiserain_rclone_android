#!/usr/bin/env bash
set -euo pipefail
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
for abi in armeabi-v7a arm64-v8a x86 x86_64; do
  grep -Fxq "jni/$abi/libgojni.so" dist/AAR_CONTENTS.txt || {
    echo "::error::AAR missing libgojni.so for $abi"
    exit 1
  }
done
# Fail the build (and block upload/publish) if any ABI, JNI method, or ELF
# PT_LOAD segment fails 16 KiB compatibility checks.
python3 ../builder/scripts/verify-aar.py "$output" dist/AAR_VERIFICATION.json

(cd dist && sha256sum "$(basename "$output")" > SHA256SUMS && sha256sum -c SHA256SUMS)
printf 'upstream=wiserain/rclone\ntag=%s\ncommit=%s\nbindings=ckreader-stat-range\npage_alignment=16384\n' \
  "$RELEASE_TAG" "$RELEASE_SHA" > dist/BUILD_INFO.txt
{
  echo "## ckReader-compatible Android AAR"
  echo "- Upstream version: $RELEASE_TAG"
  echo "- Source commit: $RELEASE_SHA"
  echo "- JNI and 16 KiB ELF checks: PASS (4 ABIs)"
  cat dist/SHA256SUMS
} >> "$GITHUB_STEP_SUMMARY"
