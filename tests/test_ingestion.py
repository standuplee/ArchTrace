from decimal import Decimal
from pathlib import Path

import pytest

from archtrace.ingestion import parse_fixture, validate_snapshot

BODY = Path("tests/fixtures/title_202601.csv").read_bytes()
MANIFEST = {
    "snapshot_ym": "202601",
    "sha256": "fixture",
    "raw_uri": "s3://raw/fixture",
    "manifest_uri": "s3://raw/manifest",
}


def test_identifiers_decimal_date_and_region():
    rows = parse_fixture(BODY, MANIFEST, {"11440"}).to_pylist()
    assert len(rows) == 2
    assert rows[0]["mgm_bldrgst_pk"] == "000001"
    assert rows[0]["total_area"] == Decimal("120.1250")
    assert str(rows[0]["approval_date"]) == "2000-01-01"
    assert rows[0]["is_synthetic"] is True


@pytest.mark.parametrize("snapshot", ["202613", "202600", "20261", "../../", "２０２６０１"])
def test_invalid_snapshot(snapshot):
    with pytest.raises(ValueError):
        validate_snapshot(snapshot)


@pytest.mark.parametrize(
    "old,new",
    [
        (b"000002", b"000001"),
        (b"1144010100100010000", b"11440"),
        (b"20000101", b"20000230"),
        (b"120.1250", b"NaN"),
        (b"120.1250", b"-1"),
        (b"120.1250", b"120.12345"),
    ],
)
def test_bad_rows_are_rejected(old, new):
    with pytest.raises(ValueError):
        parse_fixture(BODY.replace(old, new), MANIFEST, {"11440"})


def test_empty_region_does_not_erase_existing_snapshot():
    with pytest.raises(ValueError, match="No rows"):
        parse_fixture(BODY, MANIFEST, {"99999"})
