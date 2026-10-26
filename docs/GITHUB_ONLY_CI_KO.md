# GitHub Actions 전용 빌드 정책

점검 기준일: 2026-10-26

이 저장소의 AAR 빌드, ARM64 JNI/16 KiB ELF 검증, Artifact 업로드, Release 발행 및 README_KO.md 생성은 모두 GitHub가 제공하는 표준 Ubuntu runner에서 수행합니다. Synology/NAS, 외부 SSH 서버, 사설 빌드 에이전트, self-hosted runner에 의존하지 않습니다.

## 워크플로 및 실행 환경

| 워크플로 | 작업 | 실행 환경 |
|---|---|---|
| .github/workflows/build-aar.yml | resolve, build, publish | GitHub-hosted ubuntu-24.04 (x64) |
| .github/workflows/translate-readme.yml | translate | GitHub-hosted ubuntu-24.04 (x64) |

ubuntu-latest는 향후 이미지가 자동 변경될 수 있으므로 ubuntu-24.04를 명시했습니다.

모든 job의 첫 단계에서 GitHub 기본 변수값을 검사합니다.

- GITHUB_ACTIONS=true
- RUNNER_ENVIRONMENT=github-hosted
- RUNNER_OS=Linux
- RUNNER_ARCH=X64

검사에 실패하면 작업을 중단합니다. 정적 회귀 테스트(scripts/test_ci_environment.py)도 저장소의 모든 워크플로에 GitHub-hosted runner와 런타임 검사가 있는지 확인합니다. 새 워크플로를 만들면 허용 목록과 해당 검사를 갱신해야 합니다.

## 컴파일부터 배포까지

1. **resolve**: GitHub-hosted runner에서 GitHub API로 wiserain/rclone의 최신 정식 릴리스와 커밋 SHA를 확인합니다. 이미 성공 배포된 버전은 빌드를 건너뜁니다.
2. **build**: GitHub-hosted runner에 원본 rclone을 체크아웃하고 Go/Java/Android SDK·NDK를 준비합니다. ckReader Go 바인딩을 임시 작업 트리에 삽입하고 gomobile AAR을 컴파일합니다. arm64-v8a JNI 및 16 KiB ELF 정렬 검증을 통과해야 합니다.
3. **Artifact**: 작업 결과를 GitHub Actions Artifact에 보관합니다.
4. **publish**: GitHub-hosted runner에서 Artifact 및 SHA256SUMS를 확인하고 BUILD_INFO.txt에 기록된 runner_environment=github-hosted, runner_os=Linux, runner_arch=X64를 검증한 뒤 GitHub Release로 게시합니다.
5. **translate**: README.md의 한국어 번역은 GitHub-hosted runner에서 Argos Translate 로컬 추론으로 수행합니다. 외부 번역 API에 텍스트를 전송하지 않습니다.

BUILD_INFO.txt에는 실행한 GitHub Actions run ID와 runner 종류·OS·아키텍처를 남깁니다. 최종 검증이 성공했을 때만 GitHub Release를 업데이트합니다.

## 기존 일정 및 빌드 정책 유지

- 매일 **04:04 KST** (cron: 4 19 * * *, UTC 전날 19:04)
- 매일 **12:12 KST** (cron: 12 3 * * *, UTC 03:12)
- 예약 실행에서 원본 버전이 동일하고 정상 배포돼 있다면 컴파일과 게시를 생략합니다.
- 빌드 스크립트 변경을 main에 push하거나 수동으로 force=true를 지정하면 기존 버전 재빌드가 가능합니다.
- ARM64만 필수 호환성 검증 대상이며 다른 ABI의 16 KiB 정렬은 보장하지 않습니다.

## 외부 서버를 사용하지 않는다는 의미

**외부 서버에서 컴파일/검증/배포 코드를 실행하지 않는다**는 의미입니다. GitHub-hosted VM에서 실행돼도 빌드 재료의 외부 네트워크 다운로드는 남습니다. 예를 들어 wiserain/rclone GitHub 소스, Go 모듈 저장소, Google Android SDK/NDK 공식 저장소, Argos 번역 모델 저장소에서 패키지를 받아옵니다. 이는 외부 컴퓨팅 서버를 빌드 실행기로 사용하는 것과 다릅니다.

공식 소스 및 의존성 다운로드까지 차단하는 완전 오프라인 빌드는 아닙니다. 완전 오프라인 빌드를 원한다면 소스·모듈·Android 도구·번역 모델을 GitHub 저장소나 GitHub Artifact 등에 미리 보관하는 별도 설계가 필요합니다.

## 검증과 운영

- GitHub Actions: https://github.com/enaskr/wiserain_rclone_android/actions
- 정책 테스트: python3 -m unittest discover -s scripts -p test_ci_environment.py -v
- 실행 환경 근거: https://docs.github.com/en/actions/reference/workflows-and-actions/variables
- runner 이미지 근거: https://docs.github.com/en/actions/reference/runners/github-hosted-runners

GitHub 예약 실행은 지정 시간보다 지연될 수 있습니다.


## 실환경 검증 결과 (2026-10-26)

- 변경 사항: https://github.com/enaskr/wiserain_rclone_android/pull/10 (main 병합 완료)
- AAR 빌드·배포: https://github.com/enaskr/wiserain_rclone_android/actions/runs/40301125717 (resolve/build/publish 모두 성공)
- 번역: https://github.com/enaskr/wiserain_rclone_android/actions/runs/40301125649 (translate 성공)
- 정책 테스트: 4개 통과; 기존 ARM64 ELF·JNI 테스트: 10개 통과; 번역 구조 테스트: 6개 통과
- arm64-v8a JNI: named_jni_exports 확인; ELF PT_LOAD 세그먼트 4개 모두 16,384바이트 정렬 확인
- AAR SHA256SUMS 검증: 통과
- 최종 GitHub Release: https://github.com/enaskr/wiserain_rclone_android/releases/tag/aar-v1.75.2-338
- 최종 배포 AAR: rclone-v1.75.2-338-android.aar (122,211,406바이트)
- GitHub Release 자산 갱신 확인: 2026-10-26 09:42 UTC

모든 작업 로그에서 GitHub-hosted ubuntu-24.04를 확인했습니다. 실물 Android 기기에서의 동작까지 검증했다는 의미는 아닙니다.
