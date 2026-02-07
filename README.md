# Django FSM RX - Remanufactured Finite State Machine

[![PyPI version](https://img.shields.io/pypi/v/django-fsm-rx.svg?cache_bust=1)](https://pypi.org/project/django-fsm-rx/)
[![Documentation](https://readthedocs.org/projects/django-fsm-rx/badge/?version=latest)](https://django-fsm-rx.readthedocs.io/en/latest/?badge=latest)
[![CI tests](https://github.com/specialorange/django-fsm-rx/actions/workflows/test.yml/badge.svg)](https://github.com/specialorange/django-fsm-rx/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/specialorange/django-fsm-rx/branch/main/graph/badge.svg)](https://codecov.io/gh/specialorange/django-fsm-rx)
[![MIT License](https://img.shields.io/static/v1?label=License&message=MIT&color=informational&style=plastic)](https://github.com/specialorange/django-fsm-rx/LICENSE)

Django-fsm-rx adds simple declarative state management for Django models.

**[Full Documentation](https://django-fsm-rx.readthedocs.io)** | [PyPI](https://pypi.org/project/django-fsm-rx/) | [GitHub](https://github.com/specialorange/django-fsm-rx)

## What does RX mean?

**RX = Remanufactured**

In the automotive and mechanic shop world, "RX" commonly denotes a remanufactured part - rebuilt to meet or exceed original specifications, often with improvements. This project follows that philosophy: taking the battle-tested django-fsm codebase and remanufacturing it with modern enhancements.

## About This Project

Django FSM RX is an independent fork that combines the best features from the django-fsm ecosystem:

- **Core FSM functionality** from the original [django-fsm](https://github.com/viewflow/django-fsm) by Mikhail Podgurskiy
- **Admin integration** inspired by [django-fsm-admin](https://github.com/gadventures/django-fsm-admin) and [django-fsm-2-admin](https://github.com/coral-li/django-fsm-2-admin)
- **Transition logging** inspired by [django-fsm-log](https://github.com/gizmag/django-fsm-log)
- **Full type hints** for modern Python development

This is a new independent branch, separate from both [Django Commons](https://github.com/django-commons) and [Jazzband](https://github.com/jazzband). The goal is to provide a unified, actively maintained package that combines all essential FSM features in one place.

### Why a new fork?

The original django-fsm was archived after 2 years without releases. While django-fsm-2 under Django Commons continued maintenance, this project takes a different approach by:

1. **Combining features** - Admin, logging, and core FSM in one package
2. **Independent governance** - Not tied to any organization's processes
3. **Opinionated defaults** - Built for mechanic shop / automotive industry workflows

## Installation

```bash
pip install django-fsm-rx
```

Add to your Django settings:

```python
INSTALLED_APPS = [
    ...,
    'django_fsm_rx',
    ...,
]
```

Then run migrations to create the audit log table:

```bash
python manage.py migrate django_fsm_rx
```

## Configuration

Django FSM RX works out of the box with sensible defaults. All settings are optional:

```python
# settings.py
DJANGO_FSM_RX = {
    'ATOMIC': True,                    # Wrap transitions in database transactions
    'AUDIT_LOG': True,                 # Enable automatic audit logging
    'AUDIT_LOG_MODE': 'transaction',   # 'transaction' or 'signal'
    'AUDIT_LOG_MODEL': None,           # Custom audit log model (dotted path)
    'PROTECTED_FIELDS': False,         # Default for FSMField protected parameter
}
```

### Settings Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `ATOMIC` | `True` | Wrap transitions in `transaction.atomic()`. Ensures state changes and related DB operations roll back together on failure. |
| `AUDIT_LOG` | `True` | Automatically log all state transitions to `FSMTransitionLog`. |
| `AUDIT_LOG_MODE` | `'transaction'` | `'transaction'`: Log inside atomic block (rolls back with transition). `'signal'`: Log via `post_transition` signal (persists even if later code fails). |
| `AUDIT_LOG_MODEL` | `None` | Use a custom model for audit logs (e.g., `'myapp.TransitionLog'`). Must have compatible fields. |
| `PROTECTED_FIELDS` | `False` | Default value for `protected` parameter on `FSMField`. When `True`, direct field assignment raises an exception. |

### Audit Log Modes

**Transaction mode** (default, recommended):
```python
DJANGO_FSM_RX = {
    'AUDIT_LOG_MODE': 'transaction',  # Audit log rolls back if transition fails
}
```
The audit log is created inside the atomic transaction. If anything fails after the transition, both the state change and the audit log roll back together.

**Signal mode**:
```python
DJANGO_FSM_RX = {
    'AUDIT_LOG_MODE': 'signal',  # Audit log persists even if later code fails
}
```
The audit log is created via the `post_transition` signal, after the transition completes. Use this if you want audit logs even when subsequent operations fail.

### Disabling Features

```python
# Disable audit logging entirely
DJANGO_FSM_RX = {
    'AUDIT_LOG': False,
}

# Disable atomic transactions (not recommended)
DJANGO_FSM_RX = {
    'ATOMIC': False,
}
```

### Custom Audit Log Model

To use your own audit log model:

```python
# settings.py
DJANGO_FSM_RX = {
    'AUDIT_LOG_MODEL': 'myapp.TransitionLog',
}

# myapp/models.py
from django.db import models
from django.contrib.contenttypes.models import ContentType

class TransitionLog(models.Model):
    # Required fields
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.TextField()
    transition_name = models.CharField(max_length=255)
    source_state = models.CharField(max_length=255)
    target_state = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Add your custom fields
    user = models.ForeignKey('auth.User', null=True, on_delete=models.SET_NULL)
    notes = models.TextField(blank=True)
```

## Quick Start

### Option 1: Method on Model

Define transitions as methods on your model:

```python
from django.db import models
from django_fsm_rx import FSMField, transition

class RepairOrder(models.Model):
    state = FSMField(default='intake')

    @transition(field=state, source='intake', target='diagnosis')
    def begin_diagnosis(self):
        """Vehicle moved to diagnostic bay."""
        pass

    @transition(field=state, source='diagnosis', target='awaiting_approval')
    def submit_estimate(self):
        """Estimate ready for customer approval."""
        pass

    @transition(field=state, source='awaiting_approval', target='in_progress')
    def approve_repair(self):
        """Customer approved the repair."""
        pass

    @transition(field=state, source='in_progress', target='complete')
    def complete_repair(self):
        """Repair finished, ready for pickup."""
        pass
```

```python
order = RepairOrder()
order.begin_diagnosis()
order.save()  # State change is not persisted until save()
```

### Option 2: Decorator with Callbacks

Use optional callbacks for side effects like audit logging and notifications:

```python
from django.db import models
from django_fsm_rx import FSMField, transition

def example_log_transition(instance, source, target, **kwargs):
    """Runs immediately - part of the atomic transaction."""
    AuditLog.objects.create(
        order=instance,
        from_state=source,
        to_state=target,
    )

def example_notify_customer(instance, source, target, **kwargs):
    """Runs after commit - safe for external side effects."""
    from django.core.mail import send_mail
    send_mail(
        subject=f"Your repair order status: {target}",
        message=f"Order #{instance.id} is now {target}.",
        from_email="shop@example.com",
        recipient_list=[instance.customer_email],
    )

class RepairOrder(models.Model):
    state = FSMField(default='intake')
    customer_email = models.EmailField()

    @transition(
        field=state,
        source='in_progress',
        target='complete',
        on_success=example_log_transition,  # default: None
        on_commit=example_notify_customer,   # default: None
        # atomic=True is the default
    )
    def complete_repair(self):
        """Repair finished, ready for pickup."""
        self.completed_at = timezone.now()
        self.save()
```

```python
order = RepairOrder.objects.get(id=1)
order.complete_repair()  # Logs audit, then emails customer after commit
```

All callback parameters are optional - use only what you need:

```python
# Just on_success (for DB operations that should roll back together)
@transition(field=state, source='new', target='done', on_success=example_log_transition)

# Just on_commit (for external notifications after commit)
@transition(field=state, source='new', target='done', on_commit=example_notify_customer)

# Neither (simple state change, still atomic by default)
@transition(field=state, source='new', target='done')
```

## Migration Guide

django-fsm-rx provides full backwards compatibility with django-fsm, django-fsm-2, django-fsm-admin, and django-fsm-log. Your existing code will work with deprecation warnings guiding you to update imports.

### Quick Migration Check

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

Additional options:
- `--path /path/to/scan` - Scan a specific directory
- `--exclude migrations,tests` - Exclude directories
- `--verbose` - Show migration notes
- `--json` - Output as JSON

### From [django-fsm-2](https://github.com/django-commons/django-fsm-2) or [django-fsm](https://github.com/viewflow/django-fsm)

#### Step 1: Install the new package

```bash
# Uninstall old package
# django-fsm
pip uninstall django-fsm
# or django-fsm-2
pip uninstall django-fsm-2
# Install new package
pip install django-fsm-rx
```

#### Step 2: Update INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    ...,
    'django_fsm_rx',
    ...,
]
```

#### Step 3: Run migrations

```bash
python manage.py migrate django_fsm_rx
```

This creates the `FSMTransitionLog` table for audit logging.

#### Step 4: Update imports (recommended)

Your existing imports will continue to work with a deprecation warning:

```python
# Old (still works, shows deprecation warning)
from django_fsm_2 import FSMField, transition

# New (recommended)
from django_fsm_rx import FSMField, transition
```

#### API Compatibility

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

#### New Features

django-fsm-rx adds these optional features:

- **Automatic audit logging** - All transitions logged to `FSMTransitionLog`
- **`on_success` callback** - Runs inside transaction, rolls back together
- **`on_commit` callback** - Runs after commit (for emails, external APIs)
- **`atomic=True` default** - Transitions wrapped in `transaction.atomic()`

#### Opting out of new defaults

To get behavior identical to django-fsm-2:

```python
# settings.py
DJANGO_FSM_RX = {
    'AUDIT_LOG': False,  # Disable audit logging (skip Step 3)
    'ATOMIC': False,     # Disable transaction wrapping (not recommended)
}
```

### From django-fsm

```bash
pip uninstall django-fsm
pip install django-fsm-rx
```

Follow the same steps as "From django-fsm-2" above. Your `from django_fsm import ...` imports will also continue to work with a deprecation warning.

### From [django-fsm-log](https://github.com/jazzband/django-fsm-log)

django-fsm-rx includes built-in audit logging that replaces django-fsm-log. **Your existing data is automatically migrated** when you run migrations.

#### Step 1: Install django-fsm-rx

```bash
pip uninstall django-fsm-log
pip install django-fsm-rx
```

#### Step 2: Update INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    ...,
    'django_fsm_rx',  # This is all you need
    # 'django_fsm_log',  # Remove - no longer needed
    ...,
]
```

**Note:** You do NOT need to add `django_fsm_log` to INSTALLED_APPS. The compatibility shim is built into django-fsm-rx.

#### Step 3: Run migrations

```bash
python manage.py migrate django_fsm_rx
```

This:
1. Creates the new `FSMTransitionLog` table
2. **Automatically copies** all data from `django_fsm_log_statelog` to the new table
3. **Does NOT delete** the old table - your original data remains safe

#### Step 4: Update imports (recommended)

Your existing imports will continue to work:

```python
# Old (still works via compatibility shim)
from django_fsm_log.models import StateLog

# New (recommended)
from django_fsm_rx import FSMTransitionLog
```

`StateLog` is an alias to `FSMTransitionLog` - they are the same model.

#### Step 5: Clean up (optional)

After verifying migration, you can delete the old table:

```sql
-- Only after verifying data migrated correctly!
DROP TABLE IF EXISTS django_fsm_log_statelog;
```

#### Decorators

The `@fsm_log_by` and `@fsm_log_description` decorators are available:

```python
from django_fsm_rx.log import fsm_log_by, fsm_log_description

@fsm_log_by
@fsm_log_description
@transition(field=state, source='draft', target='published')
def publish(self, by=None, description=None):
    pass
```

However, with audit logging enabled (default), you may not need these decorators - transitions are automatically logged.

### From [django-fsm-admin](https://github.com/gadventures/django-fsm-admin)

#### Step 1: Install django-fsm-rx

```bash
pip uninstall django-fsm-admin
pip install django-fsm-rx
```

#### Step 2: Update imports

```python
# Old (still works via compatibility shim with deprecation warning)
from django_fsm_admin.mixins import FSMTransitionMixin

# New (recommended)
from django_fsm_rx.admin import FSMAdminMixin
```

Note: `FSMTransitionMixin` is aliased to `FSMAdminMixin` for backwards compatibility.

### Programmatic Migration Utilities

For automated migration or CI integration, use the migration utilities programmatically:

```python
from django_fsm_rx.migration import (
    scan_imports_in_directory,
    validate_model_fsm_compatibility,
    get_import_replacements,
)

# Scan a directory for deprecated imports
report = scan_imports_in_directory('/path/to/project')
print(f"Files to update: {len(report.files_affected)}")
for item in report.deprecated_imports:
    print(f"{item['file']}:{item['line']}: {item['old']} -> {item['new']}")

# Validate a model's FSM configuration
from myapp.models import Order
warnings = validate_model_fsm_compatibility(Order)
for warning in warnings:
    print(f"Warning: {warning}")

# Get all import replacements as a dict
replacements = get_import_replacements()
# {'from django_fsm import FSMField': 'from django_fsm_rx import FSMField', ...}
```

## Documentation

For complete documentation, visit **[django-fsm-rx.readthedocs.io](https://django-fsm-rx.readthedocs.io)**

### Topics covered in the full documentation:

- **[Configuration](https://django-fsm-rx.readthedocs.io/en/latest/configuration.html)** - Settings for `ATOMIC`, `AUDIT_LOG`, `AUDIT_LOG_MODE`, custom models
- **[Basic Usage](https://django-fsm-rx.readthedocs.io/en/latest/usage.html)** - Transitions, conditions, protected fields
- **[Source State Options](https://django-fsm-rx.readthedocs.io/en/latest/usage.html#source-state-options)** - Wildcards (`*`, `+`), multiple sources
- **[Dynamic Targets](https://django-fsm-rx.readthedocs.io/en/latest/usage.html#dynamic-target-state)** - `RETURN_VALUE` and `GET_STATE`
- **[Permissions](https://django-fsm-rx.readthedocs.io/en/latest/usage.html#permissions)** - String-based and callable permissions
- **[Signals](https://django-fsm-rx.readthedocs.io/en/latest/usage.html#signals)** - `pre_transition` and `post_transition`
- **[Optimistic Locking](https://django-fsm-rx.readthedocs.io/en/latest/usage.html#optimistic-locking)** - `ConcurrentTransitionMixin`
- **[Field Types](https://django-fsm-rx.readthedocs.io/en/latest/usage.html#integer-states)** - `FSMField`, `FSMIntegerField`, `FSMKeyField`
- **[Admin Integration](https://django-fsm-rx.readthedocs.io/en/latest/admin.html)** - `FSMAdminMixin`, `FSMTransitionLogInline`, `FSMCascadeWidget`
- **[Contributing](https://django-fsm-rx.readthedocs.io/en/latest/contributing.html)** - Development setup, testing, code style

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed instructions on:

- Development setup with uv or pip
- Code style and linting
- Type checking with mypy
- Pre-commit hooks
- Pull request guidelines

## Credits

- **Mikhail Podgurskiy** - Original django-fsm creator
- **Django Commons** - django-fsm-2 maintenance
- **Jazzband** - Original community support
- All contributors to the django-fsm ecosystem

## License

MIT License - see [LICENSE](LICENSE) for details.
