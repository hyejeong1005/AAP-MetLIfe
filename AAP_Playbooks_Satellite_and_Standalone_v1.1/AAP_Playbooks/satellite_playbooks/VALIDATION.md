# 검증 결과와 남은 적용 조건

검증일: 2026-10-20. 고객 서버에 접속하거나 실제 서비스·패키지·전원을 변경하지 않았습니다.

## 수행한 검증

| 항목 | 결과와 범위 |
|---|---|
| Ansible 구문 검사 | ansible-core 2.16.14 및 redhat.satellite 5.3.0 소스의 모듈 해석으로 3개 플레이북 --syntax-check 통과 |
| YAML·Jinja | 예제와 공통 Task를 포함한 YAML 파싱, Jinja 템플릿 구문 확인 |
| CSV 데이터 처리 | Satellite 우선·SSH fallback, CPU/메모리 경로 매핑, 양쪽 실패·부분 성공, 빈 입력 처리 확인 |
| CSV 형식과 보관 | 6개 CSV, UTF-8 BOM, 한글·쉼표·줄바꿈 보존, 수식 문자열 보호, 권한 0600/0700, 고유 경로 확인 |
| 실제 로컬 Ansible 수집 | 도달 불가한 테스트 Satellite URL과 로컬 SSH 대체 연결로 실행. Satellite 실패를 부분 성공으로 기록하고 CSV 생성·임시 JSON 정리 확인 |
| 수집 실패 정책 | inventory_fail_on_error=false는 결과 저장 후 성공, 기본 true는 결과 저장 후 Job 실패 확인 |
| 공통 서비스 Task | 테스트 파일로 상태를 흉내 낸 명령의 start → start 재호출 → stop → status 실행. 상태 변경 2건, 반복 start 시 변경 없음 확인 |
| 잘못된 서비스 상태 | 테스트 상태 명령이 인증 오류에 해당하는 미지원 RC를 반환하면 제어 전에 실패하는지 확인 |
| 상태 판정식 | systemd active/inactive/activating 및 command 정상/비정상 RC 분기 확인 |
| 패치 제한 조건 | 적용 확인 변수 조건, 모의 DNF 설정을 이용한 외부 URL·HTTP·GPG 해제·TLS 해제·mirrorlist 거부 확인 |

Collection 소스는 검증 환경에서만 사용했으며 ZIP에 포함하지 않습니다. 고객 운영 EE의 Collection은 승인된 공식 배포 경로에서 확보해야 합니다. 테스트 실행의 상세 로그에는 로컬 환경정보가 포함되어 최종 패키지에 넣지 않았습니다.

## 고객 테스트 서버에서 확인할 사항

1. 고객 AAP·Satellite·EE·Python·Collection 버전의 호환성과 지원 범위
2. 실제 API 인증·권한·CA, 등록 FQDN 및 반환 필드·보고시각·CPU/메모리 단위
3. AAP1·AAP2 실행 위치별 API/SSH/이미지 접근과 CSV 영구 볼륨 권한
4. WEB·WAS·DB의 실제 경로·계정·환경파일·인증·상태 반환코드와 출력 패턴
5. 서비스 단위 기동·정지와 제품별 업무 정상성 검증, 서버 간 AAP Workflow 순서
6. Pacemaker 등 클러스터의 승인된 자원 제어 절차. Standalone DB 예제를 클러스터에 사용하지 않음
7. Satellite Content View·저장소 ID·baseurl·Capsule·Errata 메타데이터·DNF Python 바인딩
8. 실제 업데이트 Preview와 트랜잭션, 패키지·커널 결과, 재부팅·복귀, 사전 백업과 실패 복구
9. Satellite BMC/Compute Resource 연동 및 전원 기동, 부팅 후 SSH·애플리케이션 정상 상태
10. 작업 강제 취소·통신 단절 시 정지된 서비스와 불완전 패치에 대한 운영자 복구 절차

실제 RPM 업데이트, 재부팅, 전원 요청, 운영 WebSphere·DB 실행을 검증 완료했다고 볼 수는 없습니다. 최종 반영 전 소수 호스트 Limit으로 위 항목을 검증해야 합니다.
