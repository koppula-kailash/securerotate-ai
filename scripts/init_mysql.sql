-- Initialization script for MySQL Docker container
CREATE DATABASE IF NOT EXISTS securerotate_db;
CREATE DATABASE IF NOT EXISTS target_demo_db;

-- Create demo target database user for rotation demo
CREATE USER IF NOT EXISTS 'demo_user'@'%' IDENTIFIED BY 'DemoPass123!';
GRANT ALL PRIVILEGES ON target_demo_db.* TO 'demo_user'@'%';

CREATE USER IF NOT EXISTS 'demo_user'@'localhost' IDENTIFIED BY 'DemoPass123!';
GRANT ALL PRIVILEGES ON target_demo_db.* TO 'demo_user'@'localhost';

FLUSH PRIVILEGES;
