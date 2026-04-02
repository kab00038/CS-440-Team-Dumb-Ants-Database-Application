SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS "maintenance_log";
DROP TABLE IF EXISTS "server";
DROP TABLE IF EXISTS "workstation";
DROP TABLE IF EXISTS "network_device";
DROP TABLE IF EXISTS "managed_assets";
DROP TABLE IF EXISTS "technician";
DROP TABLE IF EXISTS "location";
DROP TABLE IF EXISTS "department";

SET FOREIGN_KEY_CHECKS = 1;

-- create tables in opposite order of drop statements (department, location, technician, etc.)