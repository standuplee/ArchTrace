# ADR 0001: 로컬 REST 카탈로그와 Postgres

상태: 로컬 검증용 채택. 실제 실행 결과는 `docs/week-01-status.md` 참조.

## 결정

PyIceberg가 쓰고 Trino 470이 읽는 공통 REST 카탈로그를 사용한다. 구현체는 `tabulario/iceberg-rest:1.6.0`, 백엔드는 JDBC Postgres로 지정한다. 기본 in-memory/SQLite 설정을 사용하지 않는다. 객체와 DB는 서로 다른 Docker named volume에 둔다.

Python은 호스트 포트(19000/18181), 컨테이너는 서비스 DNS(minio/rest)를 사용한다. Trino는 S3 native filesystem과 path-style 접근을 사용한다. 포트는 localhost에만 공개한다.

## 근거와 제한

[REST 이미지 구현](https://github.com/databricks/iceberg-rest-image)은 Java 카탈로그를 REST로 노출하고 환경변수를 카탈로그 속성으로 변환한다. [Iceberg JDBC](https://iceberg.apache.org/docs/latest/jdbc/)의 Postgres 저장으로 컨테이너 재시작 후에도 테이블 포인터를 유지한다.

이 이미지는 실험용 참조 구현이다. 운영 고가용성·인증·다중 노드 장애 전환을 검증한 구성이 아니다. MinIO는 Docker Hub pull 거부, Quay 401, 공식 바이너리 URL 410을 확인하여 공식 GitHub 릴리스 소스를 Docker에서 빌드한다(`infra/minio/Dockerfile`). 소스 태그·Go 버전·Python lockfile을 고정한다. 최초 빌드에는 네트워크와 시간이 필요하다. 실제 검증한 이미지 digest를 실행 기록에 남긴다.

Spark를 먼저 도입하지 않고 표제부 샘플의 overwrite를 검증한다. 전국 원본 처리 시 메모리·실행시간을 측정해 스트리밍/배치 처리와 엔진 변경 여부를 판단한다.
