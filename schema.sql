CREATE TABLE IF NOT EXISTS users (
 id VARCHAR(36) PRIMARY KEY, username VARCHAR(80) NOT NULL UNIQUE,
 name VARCHAR(120) NOT NULL, role VARCHAR(24) NOT NULL, password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS catalogs (
 id VARCHAR(36) PRIMARY KEY, kind VARCHAR(32) NOT NULL, label VARCHAR(120) NOT NULL,
 UNIQUE(kind, label)
);
CREATE TABLE IF NOT EXISTS applications (
 id VARCHAR(36) PRIMARY KEY, run VARCHAR(32) NOT NULL, names VARCHAR(100) NOT NULL,
 surnames VARCHAR(100) NOT NULL, birth VARCHAR(10) NOT NULL, guardian VARCHAR(120) NOT NULL,
 phone VARCHAR(32) NOT NULL, email VARCHAR(120) NOT NULL, address VARCHAR(200) NOT NULL,
 region VARCHAR(100) NOT NULL, commune VARCHAR(100) NOT NULL,
 status VARCHAR(24) NOT NULL, reason TEXT NOT NULL, created_at VARCHAR(30) NOT NULL
);
CREATE TABLE IF NOT EXISTS beneficiaries (
 id VARCHAR(36) PRIMARY KEY, application_id VARCHAR(36) NOT NULL UNIQUE,
 run VARCHAR(32) NOT NULL, active_run VARCHAR(32) UNIQUE,
 names VARCHAR(100) NOT NULL, surnames VARCHAR(100) NOT NULL, birth VARCHAR(10) NOT NULL,
 guardian VARCHAR(120) NOT NULL, phone VARCHAR(32) NOT NULL, email VARCHAR(120) NOT NULL,
 address VARCHAR(200) NOT NULL, region VARCHAR(100) NOT NULL, commune VARCHAR(100) NOT NULL,
 diagnosis_id VARCHAR(36), insurance_id VARCHAR(36), electro INTEGER NOT NULL DEFAULT 0,
 status VARCHAR(24) NOT NULL, close_reason TEXT NOT NULL, created_at VARCHAR(30) NOT NULL,
 version INTEGER NOT NULL DEFAULT 1,
 FOREIGN KEY(application_id) REFERENCES applications(id),
 FOREIGN KEY(diagnosis_id) REFERENCES catalogs(id), FOREIGN KEY(insurance_id) REFERENCES catalogs(id)
);
CREATE TABLE IF NOT EXISTS documents (
 id VARCHAR(36) PRIMARY KEY, application_id VARCHAR(36), beneficiary_id VARCHAR(36),
 name VARCHAR(200) NOT NULL, path VARCHAR(80) NOT NULL, size_bytes INTEGER NOT NULL,
 sha256 VARCHAR(64) NOT NULL, created_at VARCHAR(30) NOT NULL,
 FOREIGN KEY(application_id) REFERENCES applications(id), FOREIGN KEY(beneficiary_id) REFERENCES beneficiaries(id)
);
CREATE TABLE IF NOT EXISTS appointments (
 id VARCHAR(36) PRIMARY KEY, beneficiary_id VARCHAR(36) NOT NULL, professional_id VARCHAR(36) NOT NULL,
 scheduled_at VARCHAR(30) NOT NULL, modality VARCHAR(32) NOT NULL, status VARCHAR(24) NOT NULL,
 specialty_id VARCHAR(36), evolution TEXT NOT NULL, procedures TEXT NOT NULL,
 recommendations TEXT NOT NULL, absence_id VARCHAR(36), completed_at VARCHAR(30),
 FOREIGN KEY(beneficiary_id) REFERENCES beneficiaries(id), FOREIGN KEY(professional_id) REFERENCES users(id),
 FOREIGN KEY(specialty_id) REFERENCES catalogs(id), FOREIGN KEY(absence_id) REFERENCES catalogs(id)
);
CREATE TABLE IF NOT EXISTS items (
 id VARCHAR(36) PRIMARY KEY, name VARCHAR(120) NOT NULL UNIQUE, unit VARCHAR(32) NOT NULL,
 stock INTEGER NOT NULL CHECK(stock >= 0)
);
CREATE TABLE IF NOT EXISTS aids (
 id VARCHAR(36) PRIMARY KEY, beneficiary_id VARCHAR(36) NOT NULL, item_id VARCHAR(36) NOT NULL,
 quantity INTEGER NOT NULL CHECK(quantity > 0), status VARCHAR(24) NOT NULL,
 created_at VARCHAR(30) NOT NULL, delivered_at VARCHAR(30),
 FOREIGN KEY(beneficiary_id) REFERENCES beneficiaries(id), FOREIGN KEY(item_id) REFERENCES items(id)
);
CREATE TABLE IF NOT EXISTS movements (
 id VARCHAR(36) PRIMARY KEY, item_id VARCHAR(36) NOT NULL, aid_id VARCHAR(36) UNIQUE,
 quantity INTEGER NOT NULL, kind VARCHAR(24) NOT NULL, note TEXT NOT NULL,
 actor_id VARCHAR(36) NOT NULL, created_at VARCHAR(30) NOT NULL,
 FOREIGN KEY(item_id) REFERENCES items(id), FOREIGN KEY(aid_id) REFERENCES aids(id),
 FOREIGN KEY(actor_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS notifications (
 id VARCHAR(36) PRIMARY KEY, role VARCHAR(24) NOT NULL, message TEXT NOT NULL,
 entity_id VARCHAR(36) NOT NULL, created_at VARCHAR(30) NOT NULL
);
CREATE TABLE IF NOT EXISTS notification_reads (
 notification_id VARCHAR(36) NOT NULL, user_id VARCHAR(36) NOT NULL,
 PRIMARY KEY(notification_id,user_id),
 FOREIGN KEY(notification_id) REFERENCES notifications(id), FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS audit (
 id VARCHAR(36) PRIMARY KEY, actor_id VARCHAR(36), action VARCHAR(80) NOT NULL,
 entity_id VARCHAR(36) NOT NULL, before_json TEXT NOT NULL, after_json TEXT NOT NULL,
 created_at VARCHAR(30) NOT NULL, FOREIGN KEY(actor_id) REFERENCES users(id)
);
