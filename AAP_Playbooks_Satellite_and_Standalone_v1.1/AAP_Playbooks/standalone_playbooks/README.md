# Satellite 비연동 플레이북

Satellite API, Collection, 등록 상태에 의존하지 않습니다. 직접 관리한 AAP Inventory와 Machine Credential을 사용합니다.

|파일|기능|
|---|---|
|01_inventory.yml|SSH facts·서비스 수집, CSV 5종 생성|
|02_lifecycle.yml|WEB/WAS/DB 상태·기동·정지, OS 상태·재부팅·종료|
|03_patch.yml|지정한 내부 HTTPS RPM 저장소 검증·업데이트·서비스 복구|

## 준비
- EE에 ansible-core와 Python 3가 필요합니다. 추가 Collection이나 openpyxl은 필요하지 않습니다.
- 대상 RHEL 8/9에 SSH·Python·필요한 sudo 권한을 준비합니다.
- examples/inventory.ini 및 호스트별 service_definitions를 실제 환경으로 수정합니다. 비밀번호와 개인키는 AAP Credential로 관리합니다.
- examples의 host_vars 파일은 자동 로드되지 않습니다. inventory 옆 host_vars/<실제호스트명>.yml로 배치하거나 AAP 호스트 변수에 입력합니다.
- /reports를 EE에서 쓸 수 있는 영구 경로로 마운트합니다. Job 컨테이너 내부에만 저장하면 종료 후 사라질 수 있습니다.

## 인벤토리
```bash
ansible-playbook -i examples/inventory.ini 01_inventory.yml -e report_dir=/reports
```
server_inventory.csv, disk_inventory.csv, network_inventory.csv, service_inventory.csv, collection_result.csv를 생성합니다. CPU는 논리 CPU(vCPU)이며 물리 소켓 수가 아닙니다. 설치 RPM·JAR·DB 내부 정보는 별도 수집 구현이 필요합니다. 일부 수집 실패도 결과를 저장하고 기본적으로 Job을 실패 처리합니다.

## 기동·정지
기본값은 services/status입니다. 변경 작업은 lifecycle_confirm=true가 필요합니다.
```bash
ansible-playbook -i examples/inventory.ini 02_lifecycle.yml -e control_scope=services -e control_action=status
ansible-playbook -i examples/inventory.ini 02_lifecycle.yml -e control_scope=services -e control_action=start -e lifecycle_confirm=true
```
서비스 정의 순서대로 기동하고 역순으로 정지합니다. 상태 판정·명령·계정은 tasks/service_state.yml 및 examples의 정의를 참고합니다. 서버 간 DB→WAS→WEB 순서는 AAP Workflow와 대상 그룹으로 구성합니다. OS 변경은 automation_infrastructure 그룹, os_control_configured=true 및 종료/재부팅에 os_services_configured=true가 필요합니다. 꺼진 서버의 power_on은 지원하지 않으며 별도 VMware/BMC 연동이 필요합니다.

## 패치
examples/patch_vars.yml의 patch_repo_ids와 patch_content_hosts를 고객 내부 저장소로 수정합니다. Satellite 등록 검사 없이 실제 저장소 baseurl을 검증합니다. HTTPS·TLS 검증·RPM GPG 검증이 필요하며 mirrorlist/metalink 및 file:// 저장소는 이 예제에서 지원하지 않습니다. 대상의 DNF needs-restarting 플러그인을 미리 준비합니다.
```bash
ansible-playbook -i examples/inventory.ini 03_patch.yml -e @examples/patch_vars.yml
```
기본값 precheck는 DNF 트랜잭션을 미리 계산하며 패키지 업데이트·서비스 중지·재부팅을 수행하지 않습니다. 저장소 메타데이터/캐시는 갱신될 수 있습니다. 실제 적용은 patch_action=apply, patch_confirm=true, patch_services_configured=true를 설정한 후 수행합니다. patch_scope는 security/all/packages, 재부팅은 never/if_required입니다. security는 저장소의 보안 advisory 메타데이터가 필요합니다. 적용 중 한 호스트가 실패하면 다음 호스트 진행을 중단합니다. 자동 롤백은 없으며 일부 서비스가 정지 상태로 남을 수 있습니다.

## AAP 설정
각 Job Template에 이 폴더의 플레이북, 직접 관리한 Inventory, Machine Credential, EE를 연결합니다. Satellite API Credential은 필요하지 않습니다. Linux 서버별 명령·권한·저장소를 입력하고 소규모 시험 후 적용합니다.
