# wiserain/rclone Android AAR Builder

[한국어 설명서 / Korean README](README_KO.md)

Twice-daily GitHub Actions release check and conditional Android AAR build from the latest published non-prerelease of [wiserain/rclone](https://github.com/wiserain/rclone/releases).

- Automatic: **04:04 and 12:12 Asia/Seoul every day**, including weekends. GitHub cron schedules are in UTC: `4 19 * * *` (04:04 KST the next day) and `12 3 * * *` (12:12 KST the same day).
- Each scheduled run performs a version check first; builds do **not** run if the upstream version is already published as a successful AAR GitHub Release.
- Manual: Actions -> Build wiserain/rclone Android AAR -> Run workflow. Supply an optional upstream release_tag; builds of an already-published tag are skipped unless force=true.
- On source updates: a push to main touching the build scripts or workflow **rebuilds** the current upstream release with new ckReader bindings; the twice-daily scheduled runs still skip successfully published versions.
- Source checkout: immutable commit SHA resolved from the published release tag.
- Android: gomobile bind -target=android, minimum API 23, four ABI variants. The build injects ckReader's Go bindings before gomobile.
- Outputs: Android AAR, SHA256SUMS, BUILD_INFO.txt, AAR_CONTENTS.txt, and AAR_VERIFICATION.json in Actions artifacts and GitHub Releases (aar-<tag>).
- Skip unchanged: scheduled runs compare the upstream release tag with the last successfully published AAR version. A GitHub Release only counts as successful if it contains an `.aar` asset. A manual run may override this with `force=true` to replace the existing release assets.
- Retry failures: failed or interrupted builds create no successful AAR Release; the next scheduled run will retry the same upstream version.
- Upstream/repository API errors abort version checking rather than triggering an unnecessary build.
- Publishing: only after successful build, checksums, JNI method signatures, JNI native entry points (`JNI_OnLoad` or named `Java_*` exports), and **16 KiB ELF PT_LOAD alignment for all four ABIs** have been verified.
- ckReader bindings: `scripts/ckreader_range.go` is copied into the temporary upstream checkout before `gomobile bind`, exporting `rcloneStatSize` and `rcloneReadRange` without modifying the upstream repository.
- Range reads: `rcloneReadRange(fsrc, remote, offset, count)` returns at most 2 MiB per call, and the backend must support ranged reads to avoid downloading the full file.
- For an already-published release, use **Actions → Run workflow** with the desired `release_tag` and `force=true`. Successful validation is required before its assets are replaced.
- Korean README: `README_KO.md` is automatically regenerated using offline English-to-Korean translation when `README.md` changes on `main`. The workflow keeps code blocks, inline code, links, and URLs intact; machine-translated text may require proofreading.

## Android

Copy the downloaded AAR into app/libs and reference it via Gradle:

```kotlin
dependencies {
  implementation(files("libs/rclone-v1.75.2-338-android.aar"))
}
```

Go binding Java API: org.rclone.gomobile.Gomobile (rcloneInitialize, rcloneRPC, rcloneFinalize, rcloneStatSize, rcloneReadRange). Upstream reference: https://github.com/wiserain/rclone/blob/master/librclone/README.md.

## Operational requirements

The workflow must live on the default branch (main) for scheduled execution. Enable GitHub Actions and ensure repository policy permits the publishing job's contents:write. GitHub schedules are best-effort and may be delayed. Build artifacts are published only after successful compilation and validation. AAR ELF 16 KiB checks do not replace end-to-end APK/AAB zip alignment verification.
