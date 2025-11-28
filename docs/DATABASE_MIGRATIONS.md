# Database Migrations Guide

Professional database schema management with Alembic and Flask-Migrate.

## Overview

The application uses **Alembic** (via Flask-Migrate) for version-controlled database schema management. This enables:

- **Incremental Updates**: Apply schema changes without recreating tables
- **Rollback Capability**: Revert problematic migrations
- **Team Collaboration**: Share schema changes through version control
- **Production Safety**: Review and test migrations before applying
- **Audit Trail**: Track all schema modifications over time

## Quick Start

### Development Workflow

```bash
# 1. Modify models in app/models.py
# Example: Add new field to User model
class User(db.Model):
    phone_number = mapped_column(String(20), nullable=True)

# 2. Generate migration automatically
flask db migrate -m "Add phone_number to User model"

# 3. Review generated migration in migrations/versions/
cat migrations/versions/<revision_id>_add_phone_number.py

# 4. Apply migration
flask db upgrade

# 5. Verify changes
flask db current
```

### Production Deployment

```bash
# 1. Pull latest code with migrations
git pull origin main

# 2. Apply pending migrations
docker-compose -f docker-compose.prod.yml exec app flask db upgrade

# 3. Verify migration status
docker-compose -f docker-compose.prod.yml exec app flask db current

# 4. Check application logs
docker-compose -f docker-compose.prod.yml logs app
```

## Flask-Migrate Commands

Flask-Migrate provides the `flask db` command group for migration management.

### Core Commands

#### Initialize Migrations (One-Time Setup)

```bash
flask db init
```

Creates `migrations/` directory with Alembic configuration. **Already done** for this project.

#### Generate Migration

```bash
# Auto-generate from model changes
flask db migrate -m "Description of changes"

# Examples:
flask db migrate -m "Add email verification fields"
flask db migrate -m "Create orders table"
flask db migrate -m "Add index on user email"
```

**How it works:**
1. Compares current models (`app/models.py`) with database schema
2. Generates Python script in `migrations/versions/`
3. Creates `upgrade()` and `downgrade()` functions
4. **IMPORTANT**: Always review generated migration before applying!

#### Apply Migrations

```bash
# Apply all pending migrations
flask db upgrade

# Apply specific number of upgrades
flask db upgrade +2  # Apply next 2 migrations

# Upgrade to specific revision
flask db upgrade <revision_id>

# Upgrade to latest (same as flask db upgrade)
flask db upgrade head
```

#### Rollback Migrations

```bash
# Rollback last migration
flask db downgrade

# Rollback specific number of migrations
flask db downgrade -2

# Rollback to specific revision
flask db downgrade <revision_id>

# Rollback all migrations (dangerous!)
flask db downgrade base
```

#### View Migration Status

```bash
# Show current migration version
flask db current

# Show migration history
flask db history

# Show detailed history with revision IDs
flask db history --verbose

# Show pending migrations
flask db heads
```

### Advanced Commands

#### Create Empty Migration

```bash
# For manual migrations (data migrations, complex changes)
flask db revision -m "Custom data migration"
```

#### Stamp Database

```bash
# Mark database as having specific migration applied (without running it)
# Useful for existing databases created with db.create_all()
flask db stamp head

# Stamp specific revision
flask db stamp <revision_id>
```

#### Show SQL

```bash
# Show SQL that would be executed (doesn't apply changes)
flask db upgrade --sql

# Show SQL for downgrade
flask db downgrade --sql
```

## Migration File Structure

### Directory Layout

```
migrations/
├── alembic.ini          # Alembic configuration
├── env.py               # Migration environment setup
├── README               # Auto-generated readme
├── script.py.mako       # Template for new migrations
└── versions/            # Migration scripts
    ├── 9931cedf8cd2_initial_migration.py
    ├── a3b2c1d4e5f6_add_user_phone.py
    └── b7c8d9e0f1a2_create_orders_table.py
```

### Migration Script Anatomy

```python
"""Add phone number to User model

Revision ID: a3b2c1d4e5f6
Revises: 9931cedf8cd2
Create Date: 2025-01-27 14:30:00.123456
"""
from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision = 'a3b2c1d4e5f6'
down_revision = '9931cedf8cd2'  # Previous migration
branch_labels = None
depends_on = None

def upgrade():
    """Apply schema changes."""
    op.add_column('users',
        sa.Column('phone_number', sa.String(length=20), nullable=True)
    )
    op.create_index('ix_users_phone', 'users', ['phone_number'])

def downgrade():
    """Revert schema changes."""
    op.drop_index('ix_users_phone', table_name='users')
    op.drop_column('users', 'phone_number')
```

**Key Components:**
- `revision`: Unique ID for this migration
- `down_revision`: Previous migration (creates dependency chain)
- `upgrade()`: Forward migration (apply changes)
- `downgrade()`: Reverse migration (rollback changes)

## Common Migration Patterns

### Add Column

```python
def upgrade():
    op.add_column('users',
        sa.Column('bio', sa.Text(), nullable=True)
    )

def downgrade():
    op.drop_column('users', 'bio')
```

### Modify Column

```python
def upgrade():
    # Change column type
    op.alter_column('users', 'username',
        existing_type=sa.String(50),
        type_=sa.String(100),
        nullable=False
    )

def downgrade():
    op.alter_column('users', 'username',
        existing_type=sa.String(100),
        type_=sa.String(50),
        nullable=False
    )
```

### Add Index

```python
def upgrade():
    op.create_index('ix_users_created_at', 'users', ['created_at'])

def downgrade():
    op.drop_index('ix_users_created_at', table_name='users')
```

### Create Table

```python
def upgrade():
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('total', sa.Numeric(10, 2), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'])
    )
    op.create_index('ix_orders_user_id', 'orders', ['user_id'])

def downgrade():
    op.drop_index('ix_orders_user_id', table_name='orders')
    op.drop_table('orders')
```

### Data Migration

```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

def upgrade():
    # Create temporary table representation
    users = table('users',
        column('id', sa.Integer),
        column('role', sa.String)
    )

    # Update existing data
    op.execute(
        users.update().where(users.c.role == 'user').values(role='viewer')
    )

def downgrade():
    users = table('users',
        column('id', sa.Integer),
        column('role', sa.String)
    )

    op.execute(
        users.update().where(users.c.role == 'viewer').values(role='user')
    )
```

## Environment-Specific Behavior

### Development

**Auto-Creation Enabled:**
```bash
# Tables auto-created on app start
python run.py

# >> System: Database tables auto-created (development mode)
```

**Migration Workflow:**
```bash
# 1. Modify models
# 2. Generate migration
flask db migrate -m "Add feature X"

# 3. Apply migration
flask db upgrade

# 4. Test changes
pytest
```

### Production

**Migration-Only Mode:**
```bash
# Tables NOT auto-created
docker-compose -f docker-compose.prod.yml up -d

# >> System: Production mode - using Alembic migrations
# >> System: Run 'flask db upgrade' to apply pending migrations
```

**Deployment Workflow:**
```bash
# 1. Review migration in staging
git diff migrations/versions/

# 2. Test migration in staging
docker-compose exec app-staging flask db upgrade

# 3. Deploy to production
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml exec app flask db upgrade

# 4. Verify
docker-compose -f docker-compose.prod.yml exec app flask db current
```

## Migration Best Practices

### 1. Always Review Auto-Generated Migrations

```bash
# Generate migration
flask db migrate -m "Add user settings"

# REVIEW before applying!
cat migrations/versions/<revision_id>_add_user_settings.py

# Check for:
# - Correct column types
# - Proper NULL/NOT NULL constraints
# - Missing indexes
# - Data loss operations (DROP COLUMN, etc.)
```

### 2. Test Migrations in Development First

```bash
# Apply migration
flask db upgrade

# Run tests
pytest

# If something wrong, rollback
flask db downgrade

# Fix migration, then retry
```

### 3. Make Migrations Reversible

**Bad:**
```python
def downgrade():
    pass  # Can't rollback!
```

**Good:**
```python
def downgrade():
    op.drop_column('users', 'phone_number')
```

### 4. Use Descriptive Messages

**Bad:**
```bash
flask db migrate -m "update"
flask db migrate -m "fix"
```

**Good:**
```bash
flask db migrate -m "Add email verification fields to User model"
flask db migrate -m "Create orders table with foreign key to users"
```

### 5. Batch Migrations for Performance

**Inefficient:**
```python
# 3 separate migrations
op.add_column('users', sa.Column('field1', ...))
op.add_column('users', sa.Column('field2', ...))
op.add_column('users', sa.Column('field3', ...))
```

**Efficient:**
```python
# Single migration with all changes
op.add_column('users', sa.Column('field1', ...))
op.add_column('users', sa.Column('field2', ...))
op.add_column('users', sa.Column('field3', ...))
```

### 6. Handle Data Carefully

```python
def upgrade():
    # 1. Add column as nullable
    op.add_column('users', sa.Column('status', sa.String(20), nullable=True))

    # 2. Populate with default data
    op.execute("UPDATE users SET status = 'active' WHERE status IS NULL")

    # 3. Make NOT NULL
    op.alter_column('users', 'status', nullable=False)

def downgrade():
    op.drop_column('users', 'status')
```

## Troubleshooting

### Issue: "Target database is not up to date"

**Diagnosis:**
```bash
flask db current
# Shows: <nothing> or old revision

flask db heads
# Shows: <latest revision>
```

**Solution:**
```bash
# Apply pending migrations
flask db upgrade

# Verify
flask db current
```

### Issue: "Can't locate revision identified by '<revision_id>'"

**Cause:** Migration file missing or revision chain broken.

**Solution:**
```bash
# Check migration files exist
ls migrations/versions/

# Verify revision chain
flask db history

# If migration missing, recreate or restore from git
git checkout migrations/versions/<revision_id>_*.py
```

### Issue: "Table already exists"

**Cause:** Database created with `db.create_all()`, not migrations.

**Solution:**
```bash
# Mark database as migrated (without running migrations)
flask db stamp head

# Verify
flask db current
```

### Issue: Migration conflict in team environment

**Scenario:**
```
Alice creates migration A (rev: aaa)
Bob creates migration B (rev: bbb)
Both based on same parent revision
```

**Solution:**
```bash
# 1. Pull latest migrations
git pull

# 2. Create merge migration
flask db merge -m "Merge migrations A and B" aaa bbb

# 3. Apply merge migration
flask db upgrade
```

### Issue: Failed migration (partial apply)

**Symptoms:**
```
Error: ...
Migration partially applied, database in inconsistent state
```

**Solution:**
```bash
# 1. Check current state
flask db current

# 2. Manually fix database (if needed)
psql -d privasee_users -c "DROP TABLE IF EXISTS broken_table;"

# 3. Downgrade to last known good state
flask db downgrade <previous_revision>

# 4. Fix migration script
# Edit migrations/versions/<bad_revision>_*.py

# 5. Retry
flask db upgrade
```

## Production Deployment Checklist

### Pre-Deployment

- [ ] Review migration SQL: `flask db upgrade --sql`
- [ ] Test migration in staging environment
- [ ] Verify rollback works: `flask db downgrade --sql`
- [ ] Check for data loss operations (DROP, ALTER TYPE, etc.)
- [ ] Estimate migration duration (for large tables)
- [ ] Plan maintenance window if needed

### During Deployment

```bash
# 1. Backup database
docker-compose -f docker-compose.prod.yml exec db \
  pg_dump -U privasee privasee_users > backup_pre_migration.sql

# 2. Apply migration
docker-compose -f docker-compose.prod.yml exec app flask db upgrade

# 3. Verify success
docker-compose -f docker-compose.prod.yml exec app flask db current

# 4. Test application
curl https://your-domain.com/health

# 5. Monitor logs
docker-compose -f docker-compose.prod.yml logs -f app
```

### Post-Deployment

- [ ] Verify migration applied: `flask db current`
- [ ] Run smoke tests on critical endpoints
- [ ] Check application logs for errors
- [ ] Monitor database performance metrics
- [ ] Keep backup for 24-48 hours

### Rollback Procedure (if needed)

```bash
# 1. Stop application
docker-compose -f docker-compose.prod.yml stop app

# 2. Restore database from backup
docker-compose -f docker-compose.prod.yml exec db \
  psql -U privasee privasee_users < backup_pre_migration.sql

# 3. Start application with old code
git checkout <previous_commit>
docker-compose -f docker-compose.prod.yml up -d app

# 4. Verify
curl https://your-domain.com/health
```

## References

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Flask-Migrate Documentation](https://flask-migrate.readthedocs.io/)
- [SQLAlchemy Core Operations](https://docs.sqlalchemy.org/en/20/core/dml.html)
- [Alembic Cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html)
