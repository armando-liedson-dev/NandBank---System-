from __future__ import annotations
import os
import psycopg
from psycopg.rows import dict_row

def connect(db_host=None, autocommit=True):
    host = db_host or os.getenv('DB_HOST','db-global')
    return psycopg.connect(
        host=host, port=5432,
        dbname=os.getenv('POSTGRES_DB','globalscale'),
        user=os.getenv('POSTGRES_USER','globalscale'),
        password=os.environ['PG_PASSWORD'],
        sslmode='verify-full',sslrootcert='/certs/ca.crt',
        connect_timeout=6,autocommit=autocommit,row_factory=dict_row)

def one(query, args=(),db_host=None):
    with connect(db_host) as c:
        return c.execute(query,args).fetchone()

def all_rows(query,args=(),db_host=None):
    with connect(db_host) as c:
        return c.execute(query,args).fetchall()
