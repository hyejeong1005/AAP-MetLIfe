# Satellite 환경용 AAP 플레이북 3종

AAP1·AAP2 설치 완료, 고객 Satellite 운영 중인 폐쇄망을 대상으로 합니다. 고객 서버에서 바로 실행할 수 있는 확정 설정은 아니며, 아래 입력값을 실제 환경에 맞춰 지정해야 합니다. 기존 Excel 패키지와 별도인 CSV 버전입니다.

## 1. 플레이북 구성

| 파일 | 요구사항 | 기본 동작 |
|---|---|---|
| `01_inventory.yml` | 인벤토리 수집 | Satellite 호스트 정보와 직접 수집 결과를 결합하여 CSV 6개 생성 |
| `02_lifecycle.yml` | OS·WEB·WAS·DB 기동/정지 | 서비스 상태 확인. start/stop 또는 OS 작업은 별도 변수로 선택 |
| `03_patch.yml` | Satellite 저장소 기반 RHEL 패치 | precheck. 업데이트 적용·서비스 정지·재부팅은 수행하지 않음 |

`tasks/service_state.yml`은 2번과 3번이 공통으로 사용하는 파일입니다. `scripts/inventory_to_csv.py`는 Python 표준 라이브러리만 사용합니다. **ZIP 안의 디렉터리 전체를 Git Project에 등록**하세요. YAML 하나만 복사하면 include 또는 CSV 생성이 실패합니다.

## 2. EE와 대상 서버 준비

- EE: 고객과 호환되는 ansible-core, `redhat.satellite`, Collection에 필요한 Python 라이브러리(requests 등), 내부 CA를 준비합니다. requirements.yml의 5.3.0은 이번 구문 검사에 사용한 버전이며 고객 호환·지원 버전을 확인해 고정하세요. 내부 Hub 등 승인된 경로로 설치합니다.
- Inventory: 대상 서버는 `managed_linux` 그룹에 넣습니다. Satellite 동적 인벤토리를 사용한다면 constructed group 또는 그룹 매핑으로 이 그룹을 구성합니다. 예시 inventory.ini의 TEST-NET 주소·도메인은 실제 주소가 아닙니다.
- OS 전원 작업과 실제 패치는 `automation_infrastructure` 그룹이 있어야 합니다. AAP1·AAP2 등 작업 지속에 필요한 인프라의 **동일한 인벤토리 이름**을 등록하고 managed_linux와 중복 여부를 검토합니다. 계정·별칭을 달리 등록하여 보호를 우회하지 않도록 관리합니다.
- 대상 Linux: 해당 EE의 Ansible 버전에 맞는 Python, 사실 수집용 iproute, 서비스 조회 도구가 필요합니다. 인벤토리 기본값은 sudo를 사용하지 않습니다. 사용자 권한 제한으로 값이 누락되면 해당 수집 단계의 권한을 고객 정책에 맞춰 조정하세요.
- 패치 대상: RHEL 8/9의 DNF4 환경, python3-dnf 바인딩, `dnf needs-restarting -r`(일반적으로 dnf-utils 플러그인 제공)을 Satellite에서 미리 준비합니다. `patch_dnf_python`과 Ansible이 사용하는 Python 모두 dnf를 import할 수 있어야 합니다. RHEL 10/DNF5는 이 패키지의 대상이 아닙니다.
- SSH Machine Credential과 서비스 실행 계정으로의 sudo 권한을 준비합니다. 비root 계정으로 become할 때 임시 모듈 파일 접근 권한/ACL 등 Ansible의 권한 전환 조건도 확인합니다.
- 인벤토리 Job은 **Run / Job Slicing 1**로 실행합니다. serial·strategy를 변경하지 마세요. 기동정지·패치는 기본 한 대씩 처리하며 오류가 발생하면 배치를 중단합니다.

## 3. AAP Credential 설정

Satellite API 조회/전원 기동용으로 `examples/credential_type.yml`의 inputs와 injectors를 이용한 Custom Credential Type을 생성합니다. 여기에 Satellite username/password를 저장하면 `satellite_username`, `satellite_password`가 작업 변수로 주입됩니다. 비밀번호를 Git이나 평문 Survey에 넣지 마세요.

**Inventory Source에 연결한 기본 Red Hat Satellite 6 Credential이 이 플레이북의 사용자 정의 변수까지 자동 생성하는 것은 아닙니다.** API 작업에 위 Credential을 별도로 연결하세요. Machine Credential도 연결합니다.

`satellite_url`, `satellite_organization`, `satellite_ca_path`는 실제 환경값으로 지정합니다. CA 경로는 EE 내부 기준이며 OS 경로와 다를 수 있습니다. TLS 검증은 항상 켜져 있습니다. Satellite API 연결 실패의 상세 원문은 비밀번호 보호를 위해 보고서에 넣지 않고 일반 오류로 기록합니다.

## 4. 인벤토리 수집과 CSV

추가 변수 예시는 `examples/satellite_vars.yml`을 참고합니다. 인벤토리 이름과 Satellite 등록 FQDN이 다르면 호스트 변수에 `satellite_hostname`을 지정합니다. 등록된 이름을 정확하게 매핑하며 SSH IP로 이름을 임의 추정하지 않습니다.

### 수집과 병합 기준

1. 선택한 호스트마다 `host_info`를 EE localhost에서 실행하여 Satellite에 HTTPS로 조회합니다. 최대 동시 요청은 5개입니다. 조회 권한만으로 실행할 수 있습니다.
2. Linux 서버에 SSH 접속하여 fresh setup/service_facts를 수집합니다. 캐시를 재사용하지 않습니다. 누락값 보완과 현재 상태 확인을 위해 SSH 수집은 전체 대상에 시도합니다.
3. 호스트명·OS·Architecture는 지원하는 Satellite 반환 필드가 있으면 사용하고, 없으면 직접 수집값을 사용합니다. 실제 사용 출처를 별도 열에 기록합니다. OS의 직접 수집값도 비교 열로 남깁니다.
4. vCPU·전체 메모리는 기본적으로 직접 수집합니다. 고객 Satellite의 정확한 필드와 단위를 확인하면 다음과 같이 반환 host 객체 기준 경로를 매핑할 수 있습니다. 아래 `customer_*`는 실제 필드명이 아닌 예시입니다.

```yaml
satellite_field_map:
  cpu_vcpus: customer_vcpu_count
  memory_mib: customer_memory_mib
```

매핑값이 비어 있거나 숫자로 변환되지 않으면 직접 수집값으로 보완합니다. 소켓 수를 vCPU로 매핑하지 마세요. 메모리는 숫자 MiB 단위로 매핑하며 문자열 `16 GB` 등은 자동 단위 변환하지 않습니다. Satellite 호스트 API가 전체 Facts를 항상 반환한다고 가정하지 않습니다.

### 출력 파일

| CSV | 내용 |
|---|---|
| server_inventory.csv | 기본정보, vCPU·메모리, 값의 출처, 현재 Kernel/IP/Uptime, 수집시각 |
| satellite_inventory.csv | 등록 호스트 ID·이름, 조직·위치·그룹, Content View·배포 환경, 제공된 보고/수정시각 |
| disk_inventory.csv | 마운트된 파일시스템의 용량·사용률·옵션 |
| network_inventory.csv | NIC, MAC, IPv4/IPv6, 활성 상태, MTU |
| service_inventory.csv | service_facts가 반환하는 관리 서비스 이름·상태·활성화 정보 |
| collection_result.csv | 모든 대상의 성공·부분 성공·실패와 단계별 결과 |

`report_dir` 아래 UTC 시각+고유 ID의 폴더를 생성합니다. UTF-8 BOM과 CSV quoting을 사용하여 한글·쉼표·줄바꿈을 처리합니다. 수식으로 해석될 수 있는 원격 문자열은 텍스트로 처리합니다. 폴더 0700/파일 0600입니다.

`last_report`는 해당 호스트의 구성 보고 등일 수 있고, `updated_at`은 Satellite 레코드 수정시각입니다. 두 값을 모든 필드의 최종 Facts 갱신시각으로 간주하지 마세요. 값이 없으면 빈 셀로 남기며 별도 API 확장이 필요할 수 있습니다.

Satellite 실패·SSH 성공 또는 그 반대는 부분 성공입니다. 양쪽이 실패해도 수집 결과 CSV에 남습니다. 기본 `inventory_fail_on_error: true`는 CSV 저장 후 불완전 수집을 AAP Job 실패로 표시합니다. false는 수집 실패를 보고서에 남기되 내보내기가 성공하면 Job이 성공합니다.

### 영구 저장 경로

실제 Job 실행 노드 모두에서 쓸 수 있는 저장소를 EE `/reports`에 연결합니다. 호스트 OS에 디렉터리만 만드는 것으로는 충분하지 않습니다. 컨테이너형 AAP의 상위 서비스 볼륨, Job 격리 볼륨, UID/GID, NFS 권한과 SELinux를 확인하세요. `:O` 임시 overlay는 결과 영구 보관용으로 사용하지 않습니다.

파일은 Job artifacts의 경로와 로그에서 위치를 확인해 NFS/파일 서버에서 가져옵니다. AAP에 자동 다운로드 버튼이 생기는 방식은 아닙니다. 강제 취소 시 남는 임시 raw JSON은 고객 보관정책으로 정리해야 합니다.

## 5. WEB·WAS·DB 서비스 제어

서버별 `service_definitions`를 AAP Host Variables 또는 Git host_vars에 등록합니다. WEB·Traditional WebSphere·Standalone DB·동일 호스트 복합 서비스 예제가 examples에 있습니다. 예시의 unit/계정/Profile 경로를 확인 없이 사용하지 마세요.

- 목록 순서대로 기동하고 역순으로 정지합니다. 현재 상태를 먼저 확인하고 필요한 경우에만 실행합니다.
- `kind: systemd`: unit을 systemd_service로 제어하고 systemctl 상태로 검증합니다.
- `kind: command`: start_argv/stop_argv/status_argv로 실행합니다. 기본 상태 RC는 running=0, stopped=3이며 status_ok_rcs를 지정할 수 있습니다. 상태 출력으로 구분하는 도구는 running_regex/stopped_regex를 함께 지정하세요.
- 알 수 없는 상태, 인증 오류, 존재하지 않는 unit은 정지 상태로 간주하지 않고 실패 처리합니다. 시작·정지 후 상태가 목표가 될 때까지 확인합니다. 명령 실행은 기본 300초, 확인 재시도는 기본 30회/5초입니다.
- `user`로 실행 계정을, `profile`로 **명시적으로 source할 Bash 환경파일**을 지정합니다. source와 명령은 같은 셸에서 실행하며 기본 sudo가 .bash_profile을 자동 로딩한다고 가정하지 않습니다.
- 관리 비밀번호를 command argv나 profile 출력에 넣지 마세요. WebSphere 관리 보안은 보호된 제품 인증 설정을 이용합니다. ND의 Dmgr/Node Agent 순서는 별도 설계가 필요합니다.
- Pacemaker DB는 예시의 standalone systemd 명령으로 제어하지 마세요. 해당 클러스터의 승인된 상태/기동/정지 절차에 맞춘 command 정의가 필요합니다.

기본 추가 변수:

```yaml
control_scope: services
control_action: status
```

기동 예시:

```yaml
control_scope: services
control_action: start
lifecycle_confirm: true
```

정지는 control_action=stop으로 변경합니다. 확인 변수는 작업 의도 오입력을 줄이는 설정이며 별도 승인 시스템이 아닙니다.

**서비스 순서는 호스트 내부 기준입니다.** 서로 다른 서버의 DB → WAS → WEB 전역 순서를 자동 추론하지 않습니다. AAP Workflow에서 같은 플레이북을 DB Limit → WAS Limit → WEB Limit 순으로 호출하고, 정지는 반대로 구성하세요. 한 호스트의 실패는 배치를 중단하지만 이미 성공한 호스트를 자동 되돌리지 않습니다.

## 6. OS 제어와 Satellite 전원 기동

`control_scope: os`에서 다음 작업을 선택합니다.

| action | 처리 |
|---|---|
| status | SSH로 현재 커널 조회 |
| reboot | 정의된 서비스 역순 정지 → 재부팅·접속 복귀 → 정의 순서 기동·상태 확인 |
| shutdown | 정의된 서비스 역순 정지 → 1분 뒤 정상 종료 예약 → SSH 종료 확인 |
| power_on | EE localhost에서 Satellite host_power 호출 → SSH/Ansible 접속 복귀 확인 |

변경 작업은 lifecycle_confirm=true, os_control_configured=true가 필요합니다. reboot/shutdown은 os_services_configured=true도 요구합니다. service_definitions가 빈 목록이면 애플리케이션 제어 없이 OS만 조작한다는 명시적 선택입니다.

power_on은 OS가 꺼져도 SSH 전제 없이 Satellite에 먼저 요청합니다. 고객 Satellite의 BMC/IPMI 또는 지원 Compute Resource·실제 VM 연결·권한이 사전에 구성되어 있어야 합니다. **전원 기동 후 서비스 start 작업은 별도 Job 또는 Workflow에서 실행**합니다. systemd 자동 시작 서비스는 OS 정책에 따라 먼저 올라올 수 있습니다.

shutdown의 SSH 종료는 물리 전원 OFF의 증거가 아닙니다. 관리 플랫폼에서 실제 전원 상태를 추가 확인할 수 있습니다. SSH ProxyJump가 필요한 환경의 shutdown 대기는 EE에서 직접 TCP 접근하는 wait_for 조건을 해당 네트워크 방식으로 조정해야 합니다.

## 7. Satellite 저장소 기반 패치

`examples/patch_vars.yml`의 저장소 ID·Satellite/Capsule 호스트명을 실제 환경으로 바꿉니다. 실제 적용 전에 서비스 정의, 백업·복구·점검 창 및 패치 범위를 확정합니다. 이 플레이북은 Content View 발행·승격이나 등록 저장소 변경을 자동 수행하지 않습니다.

### 기본 precheck

- RHEL 배포판·버전, 등록 상태, 명시된 저장소 존재 여부를 확인합니다.
- 지정 저장소의 baseurl이 HTTPS이며 satellite_content_hosts에 속하는지 확인합니다. GPG·TLS 검증을 요구합니다. 미러 목록/Metalink 및 wildcard repo ID는 이 예제에서 허용하지 않습니다.
- dnf needs-restarting 기능, 지정 서비스의 현재 기동 상태, 업데이트 의존성 해석을 확인합니다. 업데이트 미리보기는 dnf 모듈의 Check Mode를 사용합니다.
- 패키지 설치·서비스 정지·재부팅은 수행하지 않습니다. 다만 DNF 메타데이터/캐시는 갱신될 수 있습니다. Preview는 실제 실행시각의 동일 트랜잭션을 고정·보장하는 기능이 아닙니다.

### 실제 적용 변수

```yaml
patch_action: apply
patch_confirm: true
patch_scope: security
patch_services_configured: true
patch_reboot_policy: if_required
```

고객이 원하는 패키지와 저장소 정보를 함께 전달해야 합니다. Scope는 security / all / packages입니다. packages는 patch_packages 목록을 지정하며 설치된 패키지만 업데이트합니다. security는 저장소의 Errata/updateinfo 메타데이터에 의존하며 특정 RHSA 고정이나 upgrade-minimal과 동일한 의미가 아닙니다.

처리 흐름은 precheck → 서비스 역순 정지 → 승인 저장소만 활성화한 dnf 업데이트 → 재부팅 필요 판정 → 허용된 경우 재부팅 → 서비스 기동·상태 확인입니다. RPM 스크립트나 부팅 정책으로 일부 서비스가 먼저 올라올 수 있으므로 엄격한 전역 기동 순서는 제품·OS 설정과 함께 설계해야 합니다.

기본 재부팅 정책 never에서는 서비스 복구 후 재부팅이 필요하다고 판정되면 Job을 실패로 표시하고 다음 서버 진행을 중단합니다. if_required는 필요한 경우에만 재부팅합니다. needs-restarting 판정은 모든 애플리케이션 재시작 필요성까지 보장하지 않습니다.

**업데이트·부팅·기동 실패 시 자동 롤백이나 무조건적인 서비스 재기동을 하지 않습니다.** 일부 서비스가 정지 상태로 남을 수 있으므로 실패한 서버를 점검하고 복구 후 재실행합니다. AAP Job 강제 취소나 EE 종료도 동일하게 운영자가 확인해야 합니다. 패키지 롤백은 Content View 이전 버전 지정만으로 해결되지 않습니다.

프로세스/서비스 상태 확인은 업무 트랜잭션 정상성의 보장이 아닙니다. 고객별 HTTP/API/DB 접속 검증과 남은 업데이트·커널 버전 확인은 인수 항목에 맞춰 추가합니다. 보고 결과는 AAP Job 로그에 남습니다.

## 8. AAP Job Template 권장 설정

| Job Template | Playbook | 기본 변수 | Credential |
|---|---|---|---|
| Satellite 인벤토리 CSV | 01_inventory.yml | satellite_vars 예시 | Machine + Satellite API |
| 서비스와 OS 제어 | 02_lifecycle.yml | status 기본값 | Machine. power_on은 Satellite API 추가 |
| Satellite 저장소 패치 | 03_patch.yml | patch_vars의 precheck | Machine + root become |

모두 Job Type=Run입니다. 인벤토리 Slicing=1을 유지하고, OS·패치는 실제 운영 범위를 Limit으로 지정합니다. 계정 권한과 RBAC는 고객 정책에 맞춰 설정하세요. 인벤토리 수집에는 보고 경로가 필요하고, 나머지 두 플레이북은 /reports를 사용하지 않습니다.

## 9. 검증 범위

검증 결과는 패키지의 VALIDATION.md를 참고하세요. 실제 고객 Satellite API 성공 응답, 운영 WAS·DB 명령, 전원 제어, 실제 RPM 업데이트·재부팅은 고객 테스트 서버에서 검증해야 합니다. 모든 예시 설정을 실제 서버에 맞춰 검토한 뒤 소규모 Limit부터 적용하세요.

## 공식 참고 문서

- Satellite Collection: https://redhatsatellite.github.io/satellite-ansible-collection/5.3.0/plugins/index.html
- host_info: https://redhatsatellite.github.io/satellite-ansible-collection/5.3.0/plugins/host_info_module.html
- host_power: https://redhatsatellite.github.io/satellite-ansible-collection/5.3.0/plugins/host_power_module.html
- dnf: https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/dnf_module.html
- AAP와 Satellite 통합: https://docs.redhat.com/ko/documentation/red_hat_satellite/6.18/html/managing_configurations_by_using_ansible_integration/integrating_satellite_and_ansible_automation_platform_ansible
