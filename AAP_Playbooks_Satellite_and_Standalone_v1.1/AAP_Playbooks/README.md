# AAP 자동화 플레이북 통합 패키지

- satellite_playbooks/: 기존 Satellite 연동 v1.0 원본
- standalone_playbooks/: Satellite 비연동 버전

|요구사항|Satellite 연동|비연동|
|---|---|---|
|인벤토리|Satellite 메타데이터+SSH, CSV 6종|SSH 직접 수집, CSV 5종|
|기동·정지|직접 서비스 제어+조건부 Satellite power_on|직접 서비스 제어, power_on 제외|
|패치|Satellite 등록·콘텐츠 URL 확인+DNF|지정한 내부 저장소 URL 확인+DNF|

각 폴더의 README.md와 examples를 참고하십시오. 비연동은 Satellite API/Collection 없이 동작하지만 SSH와 내부 RPM 공급은 필요합니다. 두 버전 모두 고객 실제 접속정보·서비스 정의·저장소 설정이 필요합니다. 운영 서비스·패치 작업은 이 패키지 제작 과정에서 실행하지 않았습니다.
