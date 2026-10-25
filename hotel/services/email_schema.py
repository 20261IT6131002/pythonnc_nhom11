"""Non-destructive additive migration for existing GrandStay MySQL databases.

SQLAlchemy create_all() cannot add columns to an existing users table.
Call migrate_email_columns() before create_all() at CLI application entrypoints.
"""
from sqlalchemy import inspect


def migrate_email_columns(engine):
    with engine.begin() as conn:
        inspector = inspect(conn)
        if 'users' not in inspector.get_table_names():
            return
        columns = {column['name'] for column in inspector.get_columns('users')}
        if 'email' not in columns:
            conn.exec_driver_sql('ALTER TABLE users ADD COLUMN email VARCHAR(255) NULL')
        if 'email_verified_at' not in columns:
            conn.exec_driver_sql('ALTER TABLE users ADD COLUMN email_verified_at DATETIME NULL')
        if 'phone' not in columns:
            conn.exec_driver_sql('ALTER TABLE users ADD COLUMN phone VARCHAR(25) NULL')
        if 'must_change_password' not in columns:
            conn.exec_driver_sql('ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0')
        if 'temporary_password_expires_at' not in columns:
            conn.exec_driver_sql('ALTER TABLE users ADD COLUMN temporary_password_expires_at DATETIME NULL')
        if 'archived_at' not in columns:
            conn.exec_driver_sql('ALTER TABLE users ADD COLUMN archived_at DATETIME NULL')
        if 'failed_login_attempts' not in columns:
            conn.exec_driver_sql('ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER NOT NULL DEFAULT 0')
        if 'login_blocked_until' not in columns:
            conn.exec_driver_sql('ALTER TABLE users ADD COLUMN login_blocked_until DATETIME NULL')
        inspector = inspect(conn)
        indexed = any('email' in index.get('column_names', [])
                      for index in inspector.get_indexes('users'))
        unique = any('email' in constraint.get('column_names', [])
                     for constraint in inspector.get_unique_constraints('users'))
        if not (indexed or unique):
            conn.exec_driver_sql('CREATE UNIQUE INDEX ix_users_email ON users (email)')
        indexed_phone = any('phone' in index.get('column_names', [])
                            for index in inspector.get_indexes('users'))
        unique_phone = any('phone' in constraint.get('column_names', [])
                           for constraint in inspector.get_unique_constraints('users'))
        if not (indexed_phone or unique_phone):
            conn.exec_driver_sql('CREATE UNIQUE INDEX ix_users_phone ON users (phone)')

        # A booking always keeps its existing customer_id; historic guests can
        # later be linked to an account only after manual approval.
        if 'customers' in inspector.get_table_names():
            customer_columns = {column['name'] for column in inspector.get_columns('customers')}
            if 'user_id' not in customer_columns:
                conn.exec_driver_sql('ALTER TABLE customers ADD COLUMN user_id INTEGER NULL')
            inspector = inspect(conn)
            user_index = any('user_id' in index.get('column_names', [])
                             for index in inspector.get_indexes('customers'))
            if not user_index:
                conn.exec_driver_sql('CREATE INDEX ix_customers_user_id ON customers (user_id)')
