# 1주차 진행 기록

작업일: 2026-10-07.

## 구현됨

- Git 초기화, PRD 보관, Python 3.12 프로젝트, uv.lock, 환경변수 예시.
- MinIO + JDBC REST catalog + Postgres + Trino Compose 구성.
- 원본 SHA-256 객체 보존, 스냅샷별 manifest, 원본 검증 후 파싱.
- 합성 표제부의 지역 선택, 타입 검증, 월·지역 범위 overwrite.
- Trino fingerprint/원본 검증 CLI와 재실행·월 교체·재시작 검증 스크립트.
- 데이터 출처·계약 초안, ADR 2건, README 및 SQL 예제.

## 검증

- 파서 단위 테스트: 13 passed.
- Ruff lint/format: 통과.
- Docker Compose config: 통과.
- Docker 통합 검증: 통과 (`scripts/verify_smoke.py --restart`).
  - 202601 마포구 합성 2행, 면적 합계 370.1250.
  - 202602 마포구 합성 3행, 면적 합계 499.1250.
  - 동일 입력 재실행 전후 5행 전체 해시 일치.
  - 1월을 1행으로 교체했을 때 2월 3행 유지, 1월 복원 후 전체 해시 일치.
  - 원본 체크섬 검증 및 최초 manifest 유지 확인.
  - Compose 재시작 후 전체 해시·원본 체크섬 일치.
- 결과 해시: `5f0e9ce58b3682d6608e5a950495085f777ac8b8bf8015c1f09d54cbf5eb7dc7`.
- 전체 실행 출력: 로컬 `artifacts/smoke-result.json` (Git 제외).

## 검증 버전

Python 3.12.14, PyIceberg 0.10.0, PyArrow 25.0.1, Trino Python client 0.339.0. 전이 의존성은 `uv.lock` 참조.

| 이미지 | 검증 digest |
|---|---|
| postgres:16.6-alpine | `sha256:1d04b9ba1d4996401f2552b51beda8187f175c0645c091e4781134fc9c9a3eef` |
| tabulario/iceberg-rest:1.6.0 | `sha256:3b7d31bdfec626b68e97531c9778a1b9119659e456fe28545a49f6aa6a9ce472` |
| trinodb/trino:470 | `sha256:a591436ddc20cef15a4424704423326828591727b0e7c40c6ea4165d4564df67` |
| 로컬 빌드 MinIO RELEASE.2025-04-22T22-12-26Z | `sha256:a9f108f304aa1685ba4229c3e66f57f3557cbccf740f6672a48f695736e20ef6` |

MinIO digest는 이 환경의 빌드 결과다. 기반 OS 패키지 업데이트로 재빌드 digest가 달라질 수 있다. 위 검증은 단일 로컬 환경의 합성 데이터 검증이며, 실데이터 성능·고가용성·동시 writer 검증은 포함하지 않는다.

## 실행 환경에서 확인한 제약

MinIO 고정 이미지 다운로드는 Docker Hub 접근 거부, Quay 401을 반환했다. 공식 바이너리 아카이브도 HTTP 410이었다. PRD의 스토리지 선택은 유지하면서 공식 고정 릴리스 소스를 Docker 안에서 빌드한다. 호스트에 Go를 설치하지 않는다.

## 남은 데이터 의존 작업

- [ ] 실제 표제부 파일·동봉 명세 확보 및 프로파일링.
- [ ] 여섯 데이터셋의 정확한 제공 단위와 과거 파일 다운로드 가능 여부 확인.
- [ ] 총괄/표제/층별/전유부 키 관계 확정.
- [ ] PK 전환 규칙 확인, PNU 변환 규칙 검증.
- [ ] 말소대장 서비스와 사유 코드 검증.
- [ ] 인허가 API 활용신청 및 실제 응답 확인.

실제 데이터 항목은 공개 서비스 안내만으로 완료 처리하지 않는다. 1주차 전체 완료는 실제 파일 검증까지 필요하다.

## 다음 작업

실제 표제부 한 파일의 압축·인코딩·구분자·헤더·키·날짜·면적 프로파일을 확인하고 운영 bronze 계약을 확정한다. 파일 단위 스트리밍과 월별 입력 manifest를 도입한 뒤 나머지 데이터셋으로 확장한다. Dagster 에셋은 이 수집·변환 함수에 연결한다.
