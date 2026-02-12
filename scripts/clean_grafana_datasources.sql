-- Clean Grafana datasources from PostgreSQL
-- This allows re-provisioning from files

-- Show current datasources
SELECT id, org_id, name, type, uid, created, updated
FROM data_source
ORDER BY id;

-- Delete all datasources (will be re-provisioned from config/datasources.yaml)
DELETE FROM data_source;

-- Verify deletion
SELECT COUNT(*) as "Remaining Datasources" FROM data_source;
