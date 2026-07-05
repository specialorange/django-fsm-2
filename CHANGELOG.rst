Changelog
=========

django-fsm-rx 5.2.0 2026-07-05
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **BREAKING**: Remove the unused ``transition`` parameter from ``State.get_state``
  (and its ``RETURN_VALUE`` / ``GET_STATE`` subclasses). The signature is now
  ``get_state(model, result, args=(), kwargs=None)``. Code that subclasses ``State``
  and overrides ``get_state``, or that calls it directly, must drop the ``transition``
  argument. Ported from upstream django-fsm-2 (#136).
- Use ``isinstance(next_state, State)`` instead of a ``hasattr`` duck-type check when
  resolving dynamic target states.
- Add exported ``ANY_STATE`` (``"*"``) and ``ANY_OTHER_STATE`` (``"+"``) constants and
  use them in place of bare string literals in the transition-matching logic. Ported
  from upstream django-fsm-2 (#123).
- Fix: ``pre_transition`` / ``post_transition`` are now ``ModelSignal`` instances
  (previously plain ``Signal``). Receivers can now be connected with a lazy string
  sender such as ``"app_label.ModelName"`` -- matching Django's built-in model signals.
  Previously such receivers were silently never called. Ported from upstream
  django-fsm-2.


django-fsm-rx 5.1.8 2026-01-18
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Add AppConfig with explicit default_auto_field to prevent warnings in user projects


django-fsm-rx 5.1.7 2026-01-18
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Add automatic data migration from django_fsm_log to django_fsm_rx
- Add StateLog compatibility alias (points to FSMTransitionLog)
- Migration is idempotent and preserves old table data


django-fsm-rx 5.1.3 2026-01-18
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Add bump_version utility script for release automation
- Add bump_version Django management command
- Add releasing documentation (docs/releasing.md)
- Automates version updates, changelog entries, git commits, tags, and pushing


django-fsm-rx 5.1.2 2026-01-18
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Add migration utilities module (django_fsm_rx.migration)
- Add check_fsm_migration management command for scanning deprecated imports
- Add backwards compatibility shims for django-fsm-admin (django_fsm_admin package)
- Add backwards compatibility shims for django-fsm-log decorators
- Add comprehensive migration documentation
- Add 51 new tests for migration utilities and management commands


django-fsm-rx 5.1.1 2025-01-15
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Add GenericForeignKey shim for django-fsm-log compatibility
- Improve admin integration with FSMAdminMixin
- Add tests and documentation for admin features


django-fsm-rx 5.1.0 2025-01-14
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Add django-fsm-log integration with FSMTransitionLog model
- Add by and description fields for transition logging
- Fix star imports by removing FSMTransitionLog from __all__ to prevent AppRegistryNotReady error


django-fsm-rx 5.0.2 2025-01-13
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Update author to specialorange
- Update package defaults and migrations
- Add Read the Docs configuration
- Ruff install on tests and formatting fixes


django-fsm-rx 5.0.1 2025-01-12
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Fix PyPI URLs in release workflow
- Add migration guide for FSMField conversions
- Fix coverage measurement for django_fsm_rx package
- Fix Django 6.0+ _do_update signature change (use *args for positional arguments)
- Add Codecov coverage badge to README
- Add PyPI version badge to README
- Address linting issues and add typos config


django-fsm-rx 5.0.0 2025-01-12
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Rebranded to django-fsm-rx (RX = Remanufactured)
- New independent fork combining core FSM, admin integration, and logging
- Backwards compatible imports from django_fsm and django_fsm_2 (with deprecation warnings)
- Separated from Django Commons and Jazzband for independent governance
