uv : INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
At line:1 char:68
+ ... m\backend"; uv run alembic upgrade base:head --sql > migration.sql 2> ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (INFO  [alembic....PostgresqlImpl.:String) [], Remot 
   eException
    + FullyQualifiedErrorId : NativeCommandError
 
BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

n.
-- Running upgrade  -> 001_enable_vector

CREATE EXTENSION IF NOT EXISTS vector;

INSERT INTO alembic_version (version_num) VALUES ('001_enable_vector') RETURNING alembic_version.version_num;

Create video_vectors table.
-- Running upgrade 001_enable_vector -> 002_create_video_vectors

CREATE TABLE video_vectors (
    id SERIAL NOT NULL, 
    title TEXT NOT NULL, 
    channel TEXT, 
    channel_url TEXT, 
    url TEXT, 
    watched_at TIMESTAMP WITHOUT TIME ZONE, 
    category TEXT, 
    keywords VARCHAR[], 
    duration INTEGER, 
    is_shorts BOOLEAN, 
    embedding VECTOR(1536), 
    PRIMARY KEY (id), 
    UNIQUE (url)
);

UPDATE alembic_version SET version_num='002_create_video_vectors' WHERE alembic_version.version_num = '001_enable_vector';

sers table
-- Running upgrade 002_create_video_vectors -> f69c983981da

CREATE TABLE users (
    id SERIAL NOT NULL, 
    google_id VARCHAR(128) NOT NULL, 
    email VARCHAR(256) NOT NULL, 
    name VARCHAR(256) NOT NULL, 
    picture TEXT, 
    access_token TEXT, 
    refresh_token TEXT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (email)
);

CREATE UNIQUE INDEX ix_users_google_id ON users (google_id);

ALTER TABLE video_vectors ALTER COLUMN keywords TYPE VARCHAR[];

UPDATE alembic_version SET version_num='f69c983981da' WHERE alembic_version.version_num = '002_create_video_vectors';

COMMIT;

