CREATE VIEW clean_permits AS
SELECT
    id,
    city,
    permit_number,
    CASE
        WHEN permit_type IN (
            'ANNUAL FACILITY',
            'BOILER',
            'LANDSCAPING',
            'SHOP DRAWINGS - OTHER',
            'COOKIE CUTTER',
            'Low Voltage Stickers',
            'grade or quarry or fill or excavate'
        ) THEN 'OTHER'
        ELSE REPLACE(permit_type, '–', '-')
    END AS permit_type,
    work_category,
    description,
    CASE WHEN cost <= 0 THEN NULL ELSE cost END AS cost,
    applied_date,
    issued_date,
    wait_days,
    status
FROM permits
WHERE wait_days >= 0
  AND wait_days <= 1460
  AND permit_type NOT IN (
    'BUILDING RECERTIFICATION/MILESTONE INSPECTION',
    'PERMIT - REINSTATE REVOKED PMT',
    'Concurrency Case'
  );