-- Mirror of Alembic revision 20261101_0001 (for ops reference).
-- Prefer: cd services/health-api && alembic upgrade head

CREATE TYPE organization_type AS ENUM ('hospital', 'clinic', 'lab', 'other');
CREATE TYPE user_role AS ENUM ('patient', 'staff', 'admin');

CREATE TABLE organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    org_type organization_type NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(320) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX ix_users_email ON users (email);
