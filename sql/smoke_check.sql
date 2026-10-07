-- Synthetic fixtures only. These are not real buildings or historical observations.
SELECT snapshot_ym, count(*) AS buildings, sum(total_area) AS area
FROM iceberg.bronze.synthetic_bldrgst_title
GROUP BY snapshot_ym ORDER BY snapshot_ym;

SELECT mgm_bldrgst_pk, pnu, approval_date, total_area, raw_uri, manifest_uri
FROM iceberg.bronze.synthetic_bldrgst_title
ORDER BY snapshot_ym, mgm_bldrgst_pk;

SELECT * FROM iceberg.bronze."synthetic_bldrgst_title$snapshots";
