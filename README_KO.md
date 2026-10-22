<!-- Auto-generated from README.md with Argos Translate. Source SHA-256: 9b160d4181526451ad9a10fb4782ec51d1da7202f029ccba84cd17c84184cdb4. -->

# wiserain/rclone 안드로이드 AAR 빌더

[한국어 설명서 / Korean README](README_KO.md)

Twice-daily GitHub Actions release check and conditional Android AAR build from the latest released of the 최신 출판 비 발표 [wiserain/rclone](https://github.com/wiserain/rclone/releases).

- 자동: **04:04 과 12:12 아시아/서울 매일**, 주말 포함. GitHub cron 스케줄은 UTC에 있습니다. `4 19 * * *` (04:04 다음 날 KST)와 `12 3 * * *` (12:12 KST 같은 날).
- 각 예정된 실행은 먼저 버전 확인을 수행합니다. 빌드는 **** 을 실행하면 업스트림 버전이 성공적인 AAR GitHub 릴리스로 이미 게시됩니다.
- 수동 : 동작 -> wiserain/rclone 인조 인간 AAR를 건설하십시오 -> 워크플로우 실행 선택적 업스트림 release tag 공급; 이미 게시 된 태그의 빌드는 force=true없이 건너 뛸 수 있습니다.
- 소스 업데이트 : 빌드 스크립트 또는 워크플로우를 메인 터치하는 푸시 ** 새로운 ckReader 바인딩으로 현재 업스트림 릴리스; 두 배로 예정된 실행은 여전히 성공적으로 게시 된 버전을 건너뛰고 있습니다.
- 소스 체크 아웃: immutable commit SHA는 게시된 릴리스 태그에서 해결.
- Android: gomobile bind -target=android, 최소 API 23, 4 ABI 변형. 빌드는 gomobile의 앞에 ckReader의 이동 바인딩을 주사합니다.
- 출력: Android AAR, SHA256SUMS, BUILD INFO.txt, AAR CONTENTS.txt, AAR VERIFICATION.json in Actions artifacts and GitHub Releases (aar-<tag>).
- Skip unchanged: 예정된 실행은 성공적으로 AAR 버전을 발표한 업스트림 릴리스 태그를 비교합니다. GitHub 릴리스는 성공하면 계산됩니다. `.aar` 자산. 수동 실행은이를 override 할 수 있습니다 `force=true` 기존의 릴리스 자산을 대체하기 위해.
- Retry 실패 : 실패하거나 중단 된 빌드는 성공적인 AAR 릴리스를 만들 수 없습니다. 다음 예정된 실행은 동일한 업스트림 버전을 다시합니다.
- Upstream/repository API 오류가 불필요한 빌드를 트리거하는 것보다 검사 버전.
- 출판 : 성공적인 빌드 후, 체크섬, JNI 방법 서명, `JNI_OnLoad` Loader 기호 및 **16 KiB ELF PT LOAD alignment for all four ABIs** 확인되었습니다.
- ckReader 바인딩: `scripts/ckreader_range.go` 앞에 임시 상류 체크 아웃으로 복사됩니다 `gomobile bind`, 수출 `rcloneStatSize` · `rcloneReadRange` 업스트림 저장소를 수정하지 않고.
- 범위 읽기 : `rcloneReadRange(fsrc, remote, offset, count)` 통화 당 대부분의 2 MiB에서 반환하고, 백엔드는 전체 파일을 다운로드하는 것을 방지하기 위해 범위를 읽습니다.
- 이미 게시된 릴리즈를 위해 **Actions → Runflow**를 사용하세요. `release_tag` · `force=true`. 성공적인 검증은 자산이 대체되기 전에 필요합니다.
- 한국어 README: `README_KO.md` 오프라인 English-to-Korean 번역을 이용하여 자동으로 재생 `README.md` 관련 기사 `main`. 워크플로우는 코드 블록, 인라인 코드, 링크 및 URL intact를 유지합니다. 기계식 텍스트는 교정이 필요할 수 있습니다.

## 지원하다

다운로드 AAR를 app/libs로 복사하고 Gradle을 통해 참조하십시오:

```kotlin
dependencies {
  implementation(files("libs/rclone-v1.75.2-338-android.aar"))
}
```

바인딩 Java API: org.rclone.gomobile. Gomobile (rcloneInitialize, rcloneRPC, rcloneFinalize, rcloneStatSize, rcloneReadRange). Upstream 참고: https://github.com/wiserain/rclone/blob/master/librclone/README.md.

## 작업 요구 사항

워크플로우는 예정된 실행을 위한 기본 지점(main)에 있어야 합니다. GitHub Actions를 활성화하고 저장소 정책은 게시 작업의 내용을 허용:쓰기. GitHub 일정은 최고의 노력이며 지연 될 수 있습니다. artifacts는 성공적인 컴파일 및 검증 후만 출판됩니다. AAR ELF 16 KiB는 APK / AAB zip 정렬 검증을 대체하지 않습니다.
