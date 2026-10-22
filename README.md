# wiserain/rclone Android AAR Builder

Twice-daily GitHub Actions release check and conditional Android AAR build from the latest published non-prerelease of [wiserain/rclone](https://github.com/wiserain/rclone/releases).

- Automatic: **04:04 and 12:12 Asia/Seoul every day**, including weekends. GitHub cron schedules are in UTC: `4 19 * * *` (04:04 KST the next day) and `12 3 * * *` (12:12 KST the same day).
- Each scheduled run performs a version check first; builds do **not** run if the upstream version is already published as a successful AAR GitHub Release.
- Manual: Actions -> Build wiserain/rclone Android AAR -> Run workflow. Enter an optional upstream release_tag; an already successfully built version is skipped even for manual runs.
- On source updates: push to main touching the scripts or workflow launches an initial run.
- Source checkout: immutable commit SHA resolved from the published release tag.
- Android: gomobile bind -target=android, minimum API 23, four ABI variants.
- Outputs: Android AAR, SHA256SUMS, BUILD_INFO.txt, AAR_CONTENTS.txt in Actions artifacts and GitHub Releases (aar-<tag>).
- Skip unchanged: compare the upstream release tag with the last successfully published AAR version. A GitHub Release only counts as successful if it contains an `.aar` asset. Already built versions are never rebuilt, even if an older version is selected manually.
- Retry failures: failed or interrupted builds create no successful AAR Release; the next scheduled run will retry the same upstream version.
- Upstream/repository API errors abort version checking rather than triggering an unnecessary build.
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

The workflow must live on the default branch (main) for scheduled execution. Enable GitHub Actions and ensure repository policy permits the publishing job's contents:write. GitHub schedules are best-effort and may be delayed. Build artifacts are published only after successful compilation.
