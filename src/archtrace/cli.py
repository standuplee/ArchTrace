import argparse
import hashlib
import json
from pathlib import Path

from trino.dbapi import connect

from archtrace.catalog import catalog
from archtrace.config import Settings, region_codes
from archtrace.ingestion import TABLE, parse_fixture, replace_snapshot, validate_snapshot
from archtrace.storage import archive, client, ensure_buckets, read_raw


def query(settings: Settings, sql: str):
    conn = connect(host=settings.trino_host, port=settings.trino_port, user="archtrace")
    try:
        return conn.cursor().execute(sql).fetchall()
    finally:
        conn.close()


def fingerprint(settings: Settings):
    rows = query(settings, f"SELECT * FROM iceberg.{TABLE} ORDER BY snapshot_ym, mgm_bldrgst_pk")
    return {
        "rows": len(rows),
        "sha256": hashlib.sha256(json.dumps(rows, default=str).encode()).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description="ArchTrace week-one synthetic smoke pipeline")
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest-fixture")
    ingest.add_argument("path", type=Path)
    ingest.add_argument("--snapshot", required=True)
    ingest.add_argument("--regions", type=Path, default=Path("configs/regions.yaml"))
    commands.add_parser("fingerprint")
    commands.add_parser("verify-raw")
    args = parser.parse_args()
    settings = Settings.load()
    if args.command == "ingest-fixture":
        validate_snapshot(args.snapshot)
        regions = region_codes(args.regions)
        s3 = client(settings)
        ensure_buckets(s3)
        manifest = archive(s3, args.path, args.snapshot)
        data = parse_fixture(read_raw(s3, manifest), manifest, regions)
        table = replace_snapshot(catalog(settings), data, args.snapshot, regions)
        print(
            json.dumps(
                {
                    "rows_written": data.num_rows,
                    "table": TABLE,
                    "snapshot_id": table.current_snapshot().snapshot_id,
                    "manifest_uri": manifest["manifest_uri"],
                }
            )
        )
    elif args.command == "fingerprint":
        print(json.dumps(fingerprint(settings)))
    else:
        s3 = client(settings)
        refs = query(settings, f"SELECT DISTINCT manifest_uri FROM iceberg.{TABLE}")
        for (uri,) in refs:
            manifest = json.loads(
                s3.get_object(
                    Bucket="raw",
                    Key=uri.removeprefix("s3://raw/"),
                )["Body"].read()
            )
            read_raw(s3, manifest)
        print(json.dumps({"verified_manifests": len(refs)}))
