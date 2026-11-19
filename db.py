"""Repository: SQL parametrizado, transacciones y adaptador SQLite / MySQL."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class Database:
    def __init__(self, path, engine=None):
        self.path = str(path)
        self.engine = engine or os.getenv('DB_ENGINE', 'sqlite')
        if self.engine not in ('sqlite', 'mysql'):
            raise ValueError('DB_ENGINE debe ser sqlite o mysql')

    def connect(self):
        if self.engine == 'mysql':
            import pymysql
            return pymysql.connect(host=os.getenv('DB_HOST', 'localhost'),
                user=os.getenv('DB_USER', 'fdpus_app'), password=os.environ['DB_PASSWORD'],
                database=os.getenv('DB_NAME', 'fdpus'), charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor, autocommit=False)
        con = sqlite3.connect(self.path, timeout=20)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        return con

    @contextmanager
    def transaction(self):
        con = self.connect()
        try:
            if self.engine == 'sqlite':
                con.execute('BEGIN IMMEDIATE')
            else:
                con.begin()
            yield Session(con, self.engine)
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def initialize(self):
        with self.transaction() as s:
            for statement in Path(__file__).with_name('schema.sql').read_text(encoding='utf-8').split(';'):
                if statement.strip():
                    s.execute(statement)


class Session:
    def __init__(self, con, engine):
        self.con, self.engine = con, engine

    def execute(self, sql, args=()):
        cursor = self.con.cursor()
        cursor.execute(sql.replace('?', '%s') if self.engine == 'mysql' else sql, args)
        return cursor

    def all(self, sql, args=()):
        return [dict(r) for r in self.execute(sql, args).fetchall()]

    def one(self, sql, args=()):
        row = self.execute(sql, args).fetchone()
        return dict(row) if row else None

    def insert(self, table, data):
        keys = list(data)
        self.execute(f'INSERT INTO {table} ({",".join(keys)}) VALUES ({",".join("?" for _ in keys)})', list(data.values()))
