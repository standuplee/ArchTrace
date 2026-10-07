"""Run against the local Compose stack; uses only the synthetic table."""

import argparse
import json
import subprocess
import time
from decimal import Decimal
from pathlib import Path
from urllib.request import urlopen

from archtrace.catalog import catalog
from archtrace.cli import fingerprint, query
from archtrace.config import Settings
from archtrace.ingestion import TABLE, parse_fixture, replace_snapshot
from archtrace.storage import archive, client, ensure_buckets, read_raw


def wait_ready(settings):
    for url in (
        f"{settings.catalog_uri}/v1/config",
        f"http://{settings.trino_host}:{settings.trino_port}/v1/info",
    ):
        deadline = time.monotonic() + 180
        while True:
            try:
                with urlopen(url, timeout=3) as response:
                    info = json.load(response)
                if info.get("starting", False):
                    raise RuntimeError("Trino starting")
                break
            except Exception:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(2)


def run(restart=False):
    settings = Settings.load()
    wait_ready(settings)
    s3 = client(settings)
    ensure_buckets(s3)
    cat = catalog(settings)
    manifests = []
    for month in ("202601", "202602"):
        manifest = archive(s3, Path(f"tests/fixtures/title_{month}.csv"), month)
        data = parse_fixture(read_raw(s3, manifest), manifest, {"11440"})
        replace_snapshot(cat, data, month, {"11440"})
        manifests.append(manifest)
    expected = query(
        settings,
        f"""
        SELECT snapshot_ym, count(*), sum(total_area) FROM iceberg.{TABLE}
        WHERE snapshot_ym IN ('202601', '202602') AND sigungu_cd = '11440'
        GROUP BY snapshot_ym ORDER BY snapshot_ym
    """,
    )
    assert expected == [["202601", 2, Decimal("370.1250")], ["202602", 3, Decimal("499.1250")]], (
        expected
    )
    before = fingerprint(settings)
    for month, original in zip(("202601", "202602"), manifests, strict=True):
        manifest = archive(s3, Path(f"tests/fixtures/title_{month}.csv"), month)
        assert manifest == original, "Manifest changed on rerun"
        replace_snapshot(
            cat, parse_fixture(read_raw(s3, manifest), manifest, {"11440"}), month, {"11440"}
        )
    assert fingerprint(settings) == before, "Rows changed on rerun"
    # Replace January with a smaller complete fixture, then restore it. February must survive.
    january = parse_fixture(read_raw(s3, manifests[0]), manifests[0], {"11440"})
    replace_snapshot(cat, january.slice(0, 1), "202601", {"11440"})
    counts = query(
        settings,
        f"SELECT snapshot_ym, count(*) FROM iceberg.{TABLE} "
        "GROUP BY snapshot_ym ORDER BY snapshot_ym",
    )
    assert counts == [["202601", 1], ["202602", 3]], counts
    replace_snapshot(cat, january, "202601", {"11440"})
    assert fingerprint(settings) == before
    for manifest in manifests:
        read_raw(s3, manifest)
    if restart:
        subprocess.run(["docker", "compose", "restart"], check=True)
        wait_ready(settings)
        assert fingerprint(settings) == before, "Rows changed after restart"
        for manifest in manifests:
            read_raw(s3, manifest)
    result = {
        "fingerprint": before,
        "monthly_totals": expected,
        "idempotency": "passed",
        "partition_replacement": "passed",
        "raw_checksums": "passed",
        "restart": "passed" if restart else "not run",
    }
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/smoke-result.json").write_text(json.dumps(result, default=str, indent=2))
    print(json.dumps(result, default=str, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--restart", action="store_true")
    run(parser.parse_args().restart)
