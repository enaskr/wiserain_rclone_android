<!-- Auto-generated from README.md with Argos Translate. Source SHA-256: be30f504de3da08d284661edd81ccfe22deb953a9f25cff9f6c7aa33873baae2. -->

# wiserain/rclone Android AAR 자동 빌더

[English README](README.md)

이 프로젝트는 [wiserain/rclone](https://github.com/wiserain/rclone/releases)의 최신 정식 릴리스를 하루 두 차례 확인하고, 새로운 버전이 있을 때 Android AAR 라이브러리를 빌드하는 GitHub Actions 프로젝트입니다.

- **자동 실행**: 한국시간(Asia/Seoul) 매일 **04:04 및 12:12**, 주말 포함. GitHub Actions의 cron은 UTC 기준이므로 각각 `4 19 * * *`(다음 날 04:04 KST), `12 3 * * *`(당일 12:12 KST)를 사용합니다.
- **버전 변경 검사**: 모든 예약 실행에서 먼저 원본 릴리스 버전을 확인합니다. 동일 버전의 AAR이 이미 정상적으로 게시됐다면 **빌드하지 않습니다**.
- **수동 실행**: Actions → Build wiserain/rclone Android AAR → Run workflow에서 필요 시 `release_tag`를 지정합니다. 이미 게시한 버전은 `force=true`를 지정하지 않으면 건너뜁니다.
- **빌드 소스 변경 시**: 빌드 스크립트 또는 워크플로의 변경 사항이 `main`에 반영되면 새로운 ckReader 바인딩을 적용하기 위해 현재 원본 버전의 AAR을 **다시 빌드합니다**. 하루 두 번 실행되는 예약 작업은 기존 정상 배포 버전을 건너뜁니다.
- **소스 추적성**: 배포 릴리스 태그를 원본 Git 커밋 SHA로 확인하고 해당 버전의 소스만 체크아웃합니다.
- **Android 빌드**: `gomobile bind -target=android`를 사용하며 최소 API는 23입니다. 네 가지 ABI용 라이브러리를 생성하고 `gomobile` 실행 전에 ckReader 전용 Go 바인딩을 삽입합니다.
- **산출물**: Android AAR, `SHA256SUMS`, `BUILD_INFO.txt`, `AAR_CONTENTS.txt`, `AAR_VERIFICATION.json`을 GitHub Actions Artifacts 및 GitHub Releases(`aar-<tag>`)에 보관합니다.
- **중복 방지**: 예약 실행은 최신 원본 태그와 마지막 성공 배포 버전을 비교합니다. GitHub Release에 실제 `.aar` 파일이 있는 경우에만 성공한 배포로 인정합니다. `force=true`를 지정한 수동 실행은 기존 릴리스 파일을 교체할 수 있습니다.
- **실패 후 재시도**: 실패하거나 중단된 빌드는 정상 배포로 기록되지 않으므로 다음 예약 실행에서 동일한 원본 버전을 다시 빌드합니다.
- **API 오류 처리**: 원본 또는 GitHub API 조회에 실패하면 불필요한 빌드를 시작하지 않고 작업을 실패 처리합니다.
- **배포 전 검증**: 컴파일 성공 여부, 체크섬, JNI 메서드 시그니처, JNI 네이티브 연결점(`JNI_OnLoad` 또는 이름이 지정된 `Java_*` 심볼), 네 가지 ABI 모두의 **16 KiB ELF `PT_LOAD` 정렬**을 확인합니다. 하나라도 실패하면 배포하지 않습니다.
- **ckReader 바인딩**: 빌드 전에 `scripts/ckreader_range.go`를 임시 체크아웃한 원본의 `librclone/gomobile` 폴더에 복사합니다. 따라서 원본 저장소를 수정하지 않고 `rcloneStatSize`와 `rcloneReadRange`를 노출합니다.
- **범위 읽기**: `rcloneReadRange(fsrc, remote, offset, count)`는 한 번의 호출에 최대 2 MiB를 반환합니다. 파일 전체 다운로드를 피하려면 연결된 백엔드가 범위 읽기를 지원해야 합니다.
- **기존 배포 파일 갱신**: Actions → Run workflow에서 원하는 `release_tag`와 `force=true`를 지정하세요. 모든 검증을 통과해야 기존 GitHub Release 자산을 교체합니다.
- **한국어 README 자동 갱신**: `README.md`가 `main`에서 변경되면 별도 워크플로가 `README_KO.md`를 자동 재생성합니다. 검수된 번역은 우선 적용하고, 새로운 문장은 영어→한국어 번역 모델을 사용합니다. 코드 블록, 인라인 코드, 링크, URL은 보호하지만 자동 번역 결과는 검수가 필요할 수 있습니다.

## Android 앱에 적용하기

다운로드한 AAR 파일을 Android 앱의 `app/libs` 폴더에 복사하고 Gradle 의존성에 추가합니다.

```kotlin
dependencies {
  implementation(files("libs/rclone-v1.75.2-338-android.aar"))
}
```

생성되는 Java API는 `org.rclone.gomobile.Gomobile`에 있으며 `rcloneInitialize`, `rcloneRPC`, `rcloneFinalize`, `rcloneStatSize`, `rcloneReadRange`를 제공합니다. 기본 API 설명은 https://github.com/wiserain/rclone/blob/master/librclone/README.md를 참고하세요.

## 운영 및 배포 시 주의사항

예약 작업이 실행되려면 GitHub Actions 워크플로가 기본 브랜치(`main`)에 있어야 합니다. 저장소에서 GitHub Actions 실행과 릴리스 게시 작업의 `contents: write` 권한이 허용돼야 합니다. GitHub 부하에 따라 예약 실행은 지연될 수 있습니다. AAR 파일은 컴파일과 검증이 성공한 경우에만 게시됩니다. 또한 AAR의 16 KiB ELF 정렬 검사는 최종 APK/AAB의 ZIP 정렬 검사를 대체하지 않으므로 Android 앱 배포 시 추가로 확인해야 합니다.
