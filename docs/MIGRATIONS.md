"""
Alembic Database Migration Guide
=================================

This project uses Alembic for database schema migrations with async SQLAlchemy support.

## Quick Start

### Create a new migration
```bash
# Auto-generate migration from model changes
python -m alembic revision --autogenerate -m "Add new table"

# Create empty migration (for data migrations)
python -m alembic revision -m "Migrate user data"
```

### Apply migrations
```bash
# Upgrade to latest
python -m alembic upgrade head

# Upgrade by 1 version
python -m alembic upgrade +1

# Downgrade by 1 version
python -m alembic downgrade -1

# Downgrade to specific version
python -m alembic downgrade abc123
```

### Check migration status
```bash
# Show current version
python -m alembic current

# Show migration history
python -m alembic history --verbose

# Show pending migrations
python -m alembic history --verbose | grep "^ -> "
```

## Migration Best Practices

### 1. Always review auto-generated migrations
Auto-generate creates migrations but may miss:
- Index changes
- Constraint changes  
- Data type modifications
- Column renames (shows as drop + add)

### 2. Test migrations in both directions
```bash
# Test upgrade
python -m alembic upgrade head

# Test downgrade
python -m alembic downgrade -1

# Test upgrade again
python -m alembic upgrade head
```

### 3. Use data migrations for complex changes
For renaming columns or restructuring data:
```python
from alembic import op
from sqlalchemy import text

def upgrade():
    # Create new column
    op.add_column('users', sa.Column('full_name', sa.String(255)))
    
    # Migrate data
    connection = op.get_bind()
    connection.execute(
        text("UPDATE users SET full_name = first_name || ' ' || last_name")
    )
    
    # Drop old columns
    op.drop_column('users', 'first_name')
    op.drop_column('users', 'last_name')
```

### 4. Handle async engines
Our env.py supports both sync and async:
```python
# Sync migrations (default)
python -m alembic upgrade head

# Async support is built-in via run_async in env.py
```

## Production Deployment

### Pre-deployment checklist
1. ✅ All migrations tested locally
2. ✅ Database backup created
3. ✅ Migrations reviewed by team
4. ✅ Rollback plan documented

### Zero-downtime migrations
For large tables or production systems:

1. **Add new column (nullable)**
```python
op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=True))
```

2. **Deploy application code** (uses old + new column)

3. **Backfill data**
```python
connection.execute(text("UPDATE users SET email_verified = true WHERE email IS NOT NULL"))
```

4. **Make column non-nullable**
```python
op.alter_column('users', 'email_verified', nullable=False)
```

5. **Deploy application code** (uses only new column)

6. **Remove old column**
```python
op.drop_column('users', 'old_email_status')
```

## Common Operations

### Add a table
```python
def upgrade():
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('price', sa.Numeric(10, 2)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('idx_products_name', 'products', ['name'])
```

### Add a column
```python
def upgrade():
    op.add_column('users', sa.Column('phone', sa.String(20), nullable=True))
```

### Add an index
```python
def upgrade():
    op.create_index('idx_users_email', 'users', ['email'], unique=True)
```

### Add a foreign key
```python
def upgrade():
    op.create_foreign_key(
        'fk_orders_user_id',
        'orders',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
```

## Troubleshooting

### "Target database is not up to date"
Database has pending migrations. Run:
```bash
python -m alembic upgrade head
```

### "Can't locate revision"
Migration files out of sync. Check:
```bash
python -m alembic history
python -m alembic current
```

### Import errors in migrations
Ensure models are imported correctly in alembic/env.py:
```python
from src.database.models import Base
```

### Circular import errors
Keep migration logic simple. Avoid importing application code.

## Environment Variables

```bash
# PostgreSQL (production)
DATABASE_URL=postgresql://user:pass@localhost/dbname

# PostgreSQL (async)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname

# SQLite (development)
DATABASE_URL=sqlite:///./app.db
```

## Testing Migrations

See tests/test_migrations.py for automated migration tests.

## Additional Resources

- Alembic docs: https://alembic.sqlalchemy.org/
- SQLAlchemy async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- Migration patterns: https://alembic.sqlalchemy.org/en/latest/cookbook.html
