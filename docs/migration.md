# Migration Guide

This guide covers migrating to django-fsm-rx from other FSM packages.

django-fsm-rx provides full backwards compatibility with django-fsm, django-fsm-2, django-fsm-admin, and django-fsm-log. Your existing code will work with deprecation warnings guiding you to update imports.

## Quick Migration Check

### Management Command

Run the built-in migration check command to find deprecated imports in your project:

```bash
python manage.py check_fsm_migration
```

This scans your codebase and shows exactly what imports need updating:

```
Files affected: 3
Deprecated imports found: 5

myapp/models.py:
  Line 1:
    - from django_fsm import FSMField, transition
    + from django_fsm_rx import FSMField, transition

myapp/admin.py:
  Line 2:
    - from django_fsm_admin.mixins import FSMTransitionMixin
    + from django_fsm_rx.admin import FSMAdminMixin
```

### Command Options

| Option | Description |
|--------|-------------|
| `--path /path/to/scan` | Scan a specific directory (default: BASE_DIR) |
| `--exclude migrations,tests` | Comma-separated patterns to exclude |
| `--verbose` | Show detailed migration notes |
| `--json` | Output as JSON for CI/automation |

### JSON Output for CI

For CI integration, use JSON output:

```bash
python manage.py check_fsm_migration --json > migration_report.json
```

Example JSON output:

```json
{
  "is_fully_migrated": false,
  "files_affected": ["myapp/models.py", "myapp/admin.py"],
  "deprecated_imports": [
    {
      "file": "myapp/models.py",
      "line": 1,
      "old": "from django_fsm import FSMField",
      "new": "from django_fsm_rx import FSMField",
      "notes": "Direct replacement, API identical"
    }
  ],
  "warnings": [],
  "suggested_changes": {
    "from django_fsm import FSMField": "from django_fsm_rx import FSMField"
  }
}
```

## From django-fsm-2

[django-fsm-2](https://github.com/django-commons/django-fsm-2) is a maintained fork of django-fsm under Django Commons. Migration is straightforward since django-fsm-rx maintains API compatibility.

### Step 1: Install the new package

```bash
pip uninstall django-fsm-2
pip install django-fsm-rx
```

### Step 2: Update INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    ...,
    'django_fsm_rx',
    ...,
]
```

### Step 3: Run migrations

```bash
python manage.py migrate django_fsm_rx
```

This creates the `FSMTransitionLog` table for audit logging.

### Step 4: Update imports (recommended)

Your existing imports will continue to work with a deprecation warning:

```python
# Old (still works, shows deprecation warning)
from django_fsm_2 import FSMField, transition

# New (recommended)
from django_fsm_rx import FSMField, transition
```

### API Compatibility

All core APIs from django-fsm-2 are fully compatible:

| Feature | Status | Notes |
|---------|--------|-------|
| `FSMField`, `FSMIntegerField`, `FSMKeyField` | Identical | |
| `@transition` decorator | Compatible | New optional params: `on_success`, `on_commit`, `atomic` |
| `can_proceed()`, `has_transition_perm()` | Identical | |
| `ConcurrentTransitionMixin`, `FSMModelMixin` | Identical | |
| `RETURN_VALUE`, `GET_STATE` | Identical | |
| `pre_transition`, `post_transition` signals | Identical | |
| Wildcard sources (`*`, `+`) | Identical | |
| Prefix wildcards (`WRK-*`) | **New** | Matches `WRK-REP-PRG`, `WRK-INS-PRG`, etc. |

### New Features

django-fsm-rx adds these optional features:

- **Automatic audit logging** - All transitions logged to `FSMTransitionLog`
- **`on_success` callback** - Runs inside transaction, rolls back together
- **`on_commit` callback** - Runs after commit (for emails, external APIs)
- **`atomic=True` default** - Transitions wrapped in `transaction.atomic()`

### Opting out of new defaults

To get behavior identical to django-fsm-2:

```python
# settings.py
DJANGO_FSM_RX = {
    'AUDIT_LOG': False,  # Disable audit logging
    'ATOMIC': False,     # Disable transaction wrapping (not recommended)
}
```

## From django-fsm

[django-fsm](https://github.com/viewflow/django-fsm) is the original FSM package by Mikhail Podgurskiy (now archived).

```bash
pip uninstall django-fsm
pip install django-fsm-rx
```

Follow the same steps as "From django-fsm-2" above. Your `from django_fsm import ...` imports will also continue to work with a deprecation warning.

## From django-fsm-log

[django-fsm-log](https://github.com/jazzband/django-fsm-log) provides transition logging for django-fsm. django-fsm-rx includes built-in audit logging that replaces django-fsm-log.

### Your Data is Automatically Migrated

```{important}
**Your existing transition logs are automatically migrated!** When you run `python manage.py migrate django_fsm_rx`, any data in your `django_fsm_log_statelog` table is copied to the new `django_fsm_rx_fsmtransitionlog` table.
```

### Step 1: Install django-fsm-rx

```bash
pip uninstall django-fsm-log
pip install django-fsm-rx
```

### Step 2: Update INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    ...,
    'django_fsm_rx',  # This is all you need
    # 'django_fsm_log',  # Remove - no longer needed
    ...,
]
```

```{note}
You do **NOT** need to add `django_fsm_log` to INSTALLED_APPS. The compatibility shim is built into django-fsm-rx - just add `django_fsm_rx` and your existing `from django_fsm_log.models import StateLog` imports will continue to work automatically.
```

### Step 3: Run migrations

```bash
python manage.py migrate django_fsm_rx
```

This:
1. Creates the new `FSMTransitionLog` table
2. **Automatically copies** all data from `django_fsm_log_statelog` to the new table

### Step 4: Update imports (recommended)

Your existing imports will continue to work via the compatibility shim:

```python
# Old (still works via compatibility shim)
from django_fsm_log.models import StateLog

# New (recommended)
from django_fsm_rx import FSMTransitionLog
```

`StateLog` is an alias to `FSMTransitionLog` - they are the same model.

### Step 5: Clean up old table (optional)

After verifying your data was migrated successfully, you can delete the old table:

```python
# First, verify data was migrated
from django_fsm_rx import FSMTransitionLog
print(f"FSMTransitionLog has {FSMTransitionLog.objects.count()} records")
```

```{warning}
**Do not delete the old table until you have verified the migration.** The migration is safe to run multiple times (it skips already-migrated records), so you can re-run it if needed.
```

To delete the old table after verification:

```sql
-- Only run after verifying migration!
DROP TABLE IF EXISTS django_fsm_log_statelog;
```

### Field Mapping

| django-fsm-log `StateLog` | django-fsm-rx `FSMTransitionLog` |
|---------------------------|----------------------------------|
| `content_type` | `content_type` |
| `object_id` (PositiveIntegerField) | `object_id` (TextField) |
| `transition` | `transition_name` |
| `source_state` | `source_state` |
| `state` | `target_state` |
| `timestamp` | `timestamp` |
| `by` | `by` |
| `description` | `description` |

```{note}
**Backwards compatibility:** The old field names (`state` and `transition`) work automatically via property aliases. Existing code using `log.state` or `log.transition` will continue to work without modification.
```

### Decorators

The `@fsm_log_by` and `@fsm_log_description` decorators are available for compatibility:

```python
from django_fsm_rx.log import fsm_log_by, fsm_log_description

@fsm_log_by
@fsm_log_description
@transition(field=state, source='draft', target='published')
def publish(self, by=None, description=None):
    pass
```

However, with audit logging enabled (default), you may not need these decorators - transitions are automatically logged.

### Differences from django-fsm-log

| Feature | django-fsm-log | django-fsm-rx |
|---------|----------------|---------------|
| Model name | `StateLog` | `FSMTransitionLog` (with `StateLog` shim) |
| Table | `django_fsm_log_statelog` | `django_fsm_rx_fsmtransitionlog` |
| StateLog shim | N/A | Reads from original table (no migration needed) |
| Requires INSTALLED_APPS | Yes | No (for shim), Yes (for new model) |
| Automatic logging | Via signal | Via `AUDIT_LOG` setting (default: True) |
| Log modes | Signal only | `transaction` (default) or `signal` |

## From django-fsm-admin / django-fsm-2-admin

[django-fsm-admin](https://github.com/gadventures/django-fsm-admin) and [django-fsm-2-admin](https://github.com/coral-li/django-fsm-2-admin) provide Django admin integration for django-fsm and django-fsm-2 respectively. django-fsm-rx includes built-in admin support.

### Step 1: Install django-fsm-rx

```bash
pip uninstall django-fsm-admin  # or django-fsm-2-admin
pip install django-fsm-rx
```

### Step 2: Update admin imports

```python
# Old (django-fsm-admin or django-fsm-2-admin)
from fsm_admin.mixins import FSMTransitionMixin

# New
from django_fsm_rx.admin import FSMAdminMixin
# Or use the compatibility alias:
from django_fsm_rx.admin import FSMTransitionMixin  # Alias for FSMAdminMixin
```

### Step 3: Update admin classes

```python
from django.contrib import admin
from django_fsm_rx.admin import FSMAdminMixin

@admin.register(BlogPost)
class BlogPostAdmin(FSMAdminMixin, admin.ModelAdmin):
    fsm_fields = ['state']  # List your FSM fields
    list_display = ['title', 'state']
```

### Admin Features

django-fsm-rx's admin integration provides:

- **Transition buttons** - Execute transitions from the change form
- **Custom labels** - Use `custom={'label': 'Publish'}` on transitions
- **Form support** - Transitions with forms via `custom={'form': MyForm}`
- **Visibility control** - Hide transitions with `custom={'admin': False}`
- **FSM_ADMIN_FORCE_PERMIT** - Require explicit `custom={'admin': True}`

See the [Admin Integration](admin.md) guide for full documentation.

## Compatibility Shims

django-fsm-rx provides backwards compatibility shims for seamless migration:

| Import Path | Status | Notes |
|-------------|--------|-------|
| `from django_fsm import ...` | Works with deprecation warning | Shim for django-fsm |
| `from django_fsm_2 import ...` | Works with deprecation warning | Shim for django-fsm-2 |
| `from django_fsm_log.models import StateLog` | Works (alias to FSMTransitionLog) | Shim for django-fsm-log |
| `from django_fsm_rx.admin import FSMTransitionMixin` | Works (alias to FSMAdminMixin) | Shim for django-fsm-admin |

These shims allow gradual migration - update imports at your own pace.

**Note:** The shims for `django_fsm` and `django_fsm_2` are full package shims included in the django-fsm-rx distribution. The `django_fsm_log` shim provides `StateLog` as an alias. The `FSMTransitionMixin` alias is for django-fsm-admin/django-fsm-2-admin compatibility (these were separate packages, not part of django-fsm-2 core).

## Programmatic Migration Utilities

For automated migration, CI integration, or custom tooling, use the migration utilities programmatically:

### Scanning for Deprecated Imports

```python
from django_fsm_rx.migration import (
    scan_imports_in_file,
    scan_imports_in_directory,
    MigrationReport,
)

# Scan a single file
report = scan_imports_in_file('myapp/models.py')

# Scan a directory (recursive)
report = scan_imports_in_directory(
    '/path/to/project',
    exclude_patterns=['migrations', '__pycache__', 'venv']
)

# Check results
if report.is_fully_migrated:
    print("No deprecated imports found!")
else:
    print(f"Files to update: {len(report.files_affected)}")
    for item in report.deprecated_imports:
        print(f"  {item['file']}:{item['line']}")
        print(f"    OLD: {item['old']}")
        print(f"    NEW: {item['new']}")
        if item['notes']:
            print(f"    NOTE: {item['notes']}")
```

### Model Validation

Validate that a model's FSM configuration is compatible:

```python
from django_fsm_rx.migration import validate_model_fsm_compatibility
from myapp.models import Order

warnings = validate_model_fsm_compatibility(Order)
for warning in warnings:
    print(f"Warning: {warning}")
```

This checks for:
- FSM fields are properly configured
- Transitions have the correct decorator metadata
- Protected fields have `FSMModelMixin` if needed

### Import Mappings

Get all import replacements as a dictionary:

```python
from django_fsm_rx.migration import get_import_replacements, IMPORT_MAPPINGS

# Get simple old->new mapping
replacements = get_import_replacements()
print(replacements['from django_fsm import FSMField'])
# Output: 'from django_fsm_rx import FSMField'

# Access detailed mappings with notes
for mapping in IMPORT_MAPPINGS:
    print(f"{mapping['old_module']}.{mapping['old_name']}")
    print(f"  -> {mapping['new_module']}.{mapping['new_name']}")
    print(f"  Note: {mapping['notes']}")
```

### Check Migration Status from Django Settings

```python
from django_fsm_rx.migration import check_migration_status

# Automatically finds BASE_DIR from Django settings
report = check_migration_status()
print(report)  # Human-readable report
```

### Using in CI/CD

Create a custom management command or script:

```python
# scripts/check_migration.py
import sys
from django_fsm_rx.migration import run_migration_check_command

if __name__ == '__main__':
    # Returns 0 if fully migrated, 1 if migration needed
    sys.exit(run_migration_check_command())
```

Or use the management command in CI:

```yaml
# .github/workflows/test.yml
- name: Check FSM migration
  run: python manage.py check_fsm_migration --json
```

## Complete Import Reference

### Core FSM (django-fsm / django-fsm-2)

| Old Import | New Import |
|------------|------------|
| `from django_fsm import FSMField` | `from django_fsm_rx import FSMField` |
| `from django_fsm import FSMIntegerField` | `from django_fsm_rx import FSMIntegerField` |
| `from django_fsm import FSMKeyField` | `from django_fsm_rx import FSMKeyField` |
| `from django_fsm import transition` | `from django_fsm_rx import transition` |
| `from django_fsm import can_proceed` | `from django_fsm_rx import can_proceed` |
| `from django_fsm import has_transition_perm` | `from django_fsm_rx import has_transition_perm` |
| `from django_fsm import TransitionNotAllowed` | `from django_fsm_rx import TransitionNotAllowed` |
| `from django_fsm import ConcurrentTransition` | `from django_fsm_rx import ConcurrentTransition` |
| `from django_fsm import ConcurrentTransitionMixin` | `from django_fsm_rx import ConcurrentTransitionMixin` |
| `from django_fsm import FSMModelMixin` | `from django_fsm_rx import FSMModelMixin` |
| `from django_fsm import RETURN_VALUE` | `from django_fsm_rx import RETURN_VALUE` |
| `from django_fsm import GET_STATE` | `from django_fsm_rx import GET_STATE` |
| `from django_fsm.signals import pre_transition` | `from django_fsm_rx.signals import pre_transition` |
| `from django_fsm.signals import post_transition` | `from django_fsm_rx.signals import post_transition` |

### Admin (django-fsm-admin)

| Old Import | New Import |
|------------|------------|
| `from django_fsm_admin.mixins import FSMTransitionMixin` | `from django_fsm_rx.admin import FSMAdminMixin` |
| `from django_fsm_admin import FSMTransitionMixin` | `from django_fsm_rx.admin import FSMAdminMixin` |

### Logging (django-fsm-log)

| Old Import | New Import |
|------------|------------|
| `from django_fsm_log.models import StateLog` | `from django_fsm_rx import FSMTransitionLog` |
| `from django_fsm_log.decorators import fsm_log_by` | `from django_fsm_rx.log import fsm_log_by` |
| `from django_fsm_log.decorators import fsm_log_description` | `from django_fsm_rx.log import fsm_log_description` |
| `from django_fsm_log import fsm_log_by` | `from django_fsm_rx.log import fsm_log_by` |
