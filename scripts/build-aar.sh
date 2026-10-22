#!/usr/bin/env bash
set -euo pipefail
: "${RELEASE_TAG:?}"
: "${RELEASE_SHA:?}"
mkdir -p dist
export PATH="$(go env GOPATH)/bin:$PATH"
export CGO_ENABLED=1
go install golang.org/x/mobile/cmd/gobind@latest
go install golang.org/x/mobile/cmd/gomobile@latest
gomobile init
output="dist/rclone-${RELEASE_TAG}-android.aar"
gomobile bind -v -target=android -androidapi 23 -javapkg=org.rclone   -ldflags="-s -w -X github.com/rclone/rclone/fs.Version=$RELEASE_TAG"   -o "$output" github.com/rclone/rclone/librclone/gomobile
unzip -tq "$output"
unzip -Z1 "$output" > dist/AAR_CONTENTS.txt
grep -Fxq classes.jar dist/AAR_CONTENTS.txt
for abi in armeabi-v7a arm64-v8a x86 x86_64; do
  grep -Fxq "jni/$abi/libgojni.so" dist/AAR_CONTENTS.txt || { echo "Missing $abi"; exit 1; }
done
(cd dist && sha256sum "$(basename "$output")" > SHA256SUMS && sha256sum -c SHA256SUMS)
printf 'upstream=wiserain/rclone\ntag=%s\ncommit=%s\n' "$RELEASE_TAG" "$RELEASE_SHA" > dist/BUILD_INFO.txt
cat dist/SHA256SUMS >> "$GITHUB_STEP_SUMMARY"
