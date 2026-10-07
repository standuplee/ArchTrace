import csv
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

import pyarrow as pa
from pyiceberg.expressions import And, EqualTo, In

SCHEMA = pa.schema(
    [
        ("mgm_bldrgst_pk", pa.string()),
        ("sigungu_cd", pa.string()),
        ("pnu", pa.string()),
        ("main_purpose_cd", pa.string()),
        ("total_area", pa.decimal128(18, 4)),
        ("approval_date", pa.date32()),
        ("snapshot_ym", pa.string()),
        ("source_sha256", pa.string()),
        ("raw_uri", pa.string()),
        ("manifest_uri", pa.string()),
        ("is_synthetic", pa.bool_()),
    ]
)
TABLE = "bronze.synthetic_bldrgst_title"
FIELDS = {
    "mgmBldrgstPk",
    "sigunguCd",
    "pnu",
    "mainPurpsCd",
    "totArea",
    "useAprDay",
}


def validate_snapshot(snapshot: str):
    if not re.fullmatch(r"[0-9]{6}", snapshot):
        raise ValueError("snapshot must be YYYYMM")
    datetime.strptime(snapshot, "%Y%m")


def parse_fixture(body: bytes, manifest: dict, regions: set[str]) -> pa.Table:
    """Explicit synthetic CSV contract. Not a parser for unverified HUB files."""
    validate_snapshot(manifest["snapshot_ym"])
    reader = csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
    if set(reader.fieldnames or []) != FIELDS:
        raise ValueError("Unexpected synthetic fixture columns")
    rows, seen = [], set()
    for line, row in enumerate(reader, 2):
        if row["sigunguCd"] not in regions:
            continue
        pk = row["mgmBldrgstPk"]
        if not pk or pk in seen:
            raise ValueError(f"Line {line}: missing or duplicate building key")
        seen.add(pk)
        pnu = row["pnu"]
        if not re.fullmatch(r"[0-9]{19}", pnu) or not pnu.startswith(row["sigunguCd"]):
            raise ValueError(f"Line {line}: invalid PNU")
        try:
            area = Decimal(row["totArea"])
            if not area.is_finite() or area < 0 or area != area.quantize(Decimal("0.0001")):
                raise ValueError("Area must be nonnegative with at most four decimal places")
            date = (
                datetime.strptime(row["useAprDay"], "%Y%m%d").date() if row["useAprDay"] else None
            )
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"Line {line}: invalid area/date") from exc
        rows.append(
            {
                "mgm_bldrgst_pk": pk,
                "sigungu_cd": row["sigunguCd"],
                "pnu": pnu,
                "main_purpose_cd": row["mainPurpsCd"],
                "total_area": area,
                "approval_date": date,
                "snapshot_ym": manifest["snapshot_ym"],
                "source_sha256": manifest["sha256"],
                "raw_uri": manifest["raw_uri"],
                "manifest_uri": manifest["manifest_uri"],
                "is_synthetic": True,
            }
        )
    if not rows:
        raise ValueError("No rows for selected regions; refusing to erase a snapshot")
    return pa.Table.from_pylist(rows, schema=SCHEMA)


def replace_snapshot(cat, data: pa.Table, snapshot: str, regions: set[str]):
    cat.create_namespace_if_not_exists("bronze")
    table = cat.create_table_if_not_exists(TABLE, schema=SCHEMA, properties={"format-version": "2"})
    if table.spec().is_unpartitioned():
        with table.update_spec() as update:
            update.add_identity("snapshot_ym")
    # Restrict replacement to selected month AND regions, preserving other inputs.
    table.overwrite(
        data, overwrite_filter=And(EqualTo("snapshot_ym", snapshot), In("sigungu_cd", regions))
    )
    return table
