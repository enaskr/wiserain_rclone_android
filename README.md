# wiserain/rclone Android AAR Builder

Daily GitHub Actions build of Android AAR from the latest published non-prerelease of [wiserain/rclone](https://github.com/wiserain/rclone/releases).

- Automatic: 03:17 UTC / 12:17 KST every day (GitHub Actions schedule).
- Manual: Actions -> Build wiserain/rclone Android AAR -> Run workflow. Enter optional release_tag; force rebuilds.
- On source updates: push to main touching the scripts or workflow launches an initial run.
- Source checkout: immutable commit SHA resolved from the published release tag.
- Android: gomobile bind -target=android, minimum API 23, four ABI variants.
- Outputs: Android AAR, SHA256SUMS, BUILD_INFO.txt, AAR_CONTENTS.txt in Actions artifacts and GitHub Releases (aar-<tag>).
- Skip unchanged: an upstream version with an existing output release is not rebuilt in daily runs.
- Publishing: only after successful build and checksums/contents verification.

## Android

Copy the downloaded AAR into app/libs and reference it via Gradle:

```kotlin
dependencies {
  implementation(files("libs/rclone-v1.75.2-338-android.aar"))
}
```

Go binding Java API: org.rclone.gomobile.Gomobile (rcloneInitialize, rcloneRPC, rcloneFinalize). Upstream reference: https://github.com/wiserain/rclone/blob/master/librclone/README.md.

## Operational requirements

The workflow must live on the default branch (main) for scheduled execution. Enable GitHub Actions and ensure repository policy permits the publishing job's contents:write. GitHub schedules are best-effort and may be delayed. Actual AAR compilation is unverified until Actions succeeds.
