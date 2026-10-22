# wiserain/rclone Android AAR 자동 빌더

[English README](README.md)

이 프로젝트는 [wiserain/rclone](https://github.com/wiserain/rclone/releases)의 최신 정식 릴리스를 하루 두 번 확인하고, 필요한 경우 Android AAR 라이브러리를 빌드하는 GitHub Actions 프로젝트입니다. 빌드에 필요한 스크립트만 보관하며 원본 rclone 저장소는 수정하지 않습니다.

- **자동 실행**: 한국시간(KST) 매일 **04:04, 12:12**, 주말 포함. GitHub Actions는 UTC를 사용하므로 각각 `4 19 * * *`(한국시간 다음 날 04:04), `12 3 * * *`(당일 12:12)으로 지정합니다.
- **버전 확인 후 빌드**: 예약 실행 때 최신 릴리스와 이미 정상 배포된 AAR 버전을 비교합니다. 이미 게시된 버전이라면 빌드를 건너뜁니다.
- **수동 실행**: Actions → Build wiserain/rclone Android AAR → Run workflow. 필요하면 `release_tag`를 지정합니다. 같은 버전을 다시 빌드하려면 `force=true`를 선택할 수 있습니다.
- **빌드 스크립트 업데이트**: `main`에 빌드 스크립트 또는 워크플로 변경이 반영되면 ckReader 바인딩을 반영하기 위해 현재 릴리스로 강제 재빌드합니다. 하루 두 차례의 예약 실행에서는 버전 중복 빌드를 하지 않습니다.
- **정확한 소스 버전**: upstream 릴리스 태그를 변경할 수 없는 Git 커밋 SHA로 해석한 뒤 해당 소스를 체크아웃합니다.
- **Android 지원**: `gomobile bind -target=android`, 최소 API 23. armeabi-v7a, arm64-v8a, x86, x86_64의 네 가지 ABI를 지원합니다.
- **산출물**: `.aar`, `SHA256SUMS`, `BUILD_INFO.txt`, `AAR_CONTENTS.txt`, `AAR_VERIFICATION.json`을 Actions Artifacts와 GitHub Releases(`aar-<tag>`)에 보관합니다.
- **중복 빌드 방지**: 릴리스에 실제 `.aar` 자산이 있는 경우에만 성공한 배포로 취급합니다. 수동으로 `force=true`를 지정하지 않으면 동일 버전은 재빌드하지 않습니다.
- **실패 시 재시도**: 컴파일이나 검증에 실패한 릴리스는 성공한 배포로 기록되지 않으므로 다음 예약 실행에서 다시 시도합니다.
- **API 오류 시 안전 종료**: upstream 또는 GitHub API를 조회할 수 없는 경우 불필요한 빌드를 시작하지 않습니다.
- **검증 후 배포**: 체크섬, JNI 메서드 시그니처, 네이티브 `JNI_OnLoad` 심볼, 네 가지 ABI의 **16 KiB ELF `PT_LOAD` 정렬**을 모두 확인한 경우에만 릴리스를 게시합니다.
- **ckReader 전용 함수**: 빌드 전에 `scripts/ckreader_range.go`를 임시로 체크아웃한 upstream 소스에 복사해 `rcloneStatSize`와 `rcloneReadRange`를 추가합니다. upstream 원본 저장소는 변경하지 않습니다.
- **범위 읽기**: `rcloneReadRange(fsrc, remote, offset, count)`는 한 번에 최대 2 MiB를 반환합니다. 전체 파일을 다운로드하지 않으려면 연결한 백엔드가 Range 요청을 지원해야 합니다.
- **기존 릴리스 교체**: 기존 버전에 수정된 바인딩을 적용하려면 Actions → Run workflow에서 `release_tag`를 지정하고 `force=true`를 선택합니다. 모든 검증이 성공해야 기존 Release 자산을 교체합니다.
- **한국어 README 자동 갱신**: `README.md`가 `main`에서 변경되면 별도 Actions가 오프라인 영→한 번역 모델을 이용해 `README_KO.md`를 자동 생성합니다. 코드 블록, 인라인 코드, 링크 및 URL은 유지합니다. 기계 번역된 내용은 검수가 필요할 수 있습니다.

## Android 앱에서 사용하기

GitHub Releases에서 AAR을 받아 앱 모듈의 `app/libs/`에 복사한 다음 Gradle에 다음을 추가합니다.

```kotlin
dependencies {
  implementation(files("libs/rclone-v1.75.2-338-android.aar"))
}
```

생성되는 Java API는 `org.rclone.gomobile.Gomobile`에 있으며 `rcloneInitialize`, `rcloneRPC`, `rcloneFinalize`, `rcloneStatSize`, `rcloneReadRange` 메서드를 제공합니다.

자세한 기본 API는 [wiserain/rclone의 librclone 설명서](https://github.com/wiserain/rclone/blob/master/librclone/README.md)를 참고하세요.

## 운영상 주의사항

GitHub Actions의 예약 실행은 기본 브랜치(`main`)에 워크플로가 있어야 작동합니다. 저장소에서 Actions 사용이 허용되어 있어야 하며, Release 게시 작업에 `contents: write` 권한이 필요합니다.

예약 실행 시각은 GitHub 서비스 부하에 따라 지연될 수 있습니다. AAR 산출물은 컴파일과 검증이 모두 성공했을 때만 게시됩니다. AAR의 ELF 16 KiB 검사는 최종 APK/AAB의 ZIP 정렬 검사를 대신하지 않으므로, 앱 배포 전에 별도로 검증하세요.
