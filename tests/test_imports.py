"""
Tests for import behavior and backwards compatibility.

These tests verify:
- Star imports work without triggering AppRegistryNotReady
- FSMTransitionLog can be imported after Django setup
- Backwards compatibility shims work correctly
- All expected symbols are exported
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


class TestCleanImportWithoutDjangoStubs:
    """Adapted from django-fsm-2 (#113).

    Verify the package imports cleanly in a fresh interpreter with settings
    merely ``configure()``-d and no ``DJANGO_SETTINGS_MODULE`` -- i.e. without
    the django-stubs runtime monkeypatch that pytest-django applies in-process.
    This guards against relying on that monkeypatch at import time.

    Note: ``django_fsm_rx.admin`` is intentionally NOT covered here. Unlike
    upstream, our admin module exposes a contenttypes-based
    ``FSMTransitionLogInline`` and therefore imports ``contenttypes`` at module
    load, which requires the app registry to be ready. Admin modules are only
    imported after ``django.setup()``, so this is an accepted divergence.
    """

    def _run_import(self, module: str) -> subprocess.CompletedProcess[str]:
        project_root = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env.pop("DJANGO_SETTINGS_MODULE", None)
        python_path = env.get("PYTHONPATH")
        env["PYTHONPATH"] = f"{project_root}{os.pathsep}{python_path}" if python_path else str(project_root)
        code = f"from django.conf import settings; settings.configure(SECRET_KEY='test', USE_I18N=False); import {module}"
        return subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            check=False,
            cwd=project_root,
            env=env,
            text=True,
        )

    def test_main_module_imports_without_django_stubs_monkeypatch(self):
        result = self._run_import("django_fsm_rx")
        assert result.returncode == 0, result.stderr


class TestStarImport:
    """Tests for star import behavior."""

    def test_star_import_does_not_include_fsm_transition_log(self):
        """Star import should not include FSMTransitionLog (requires Django apps ready)."""
        import django_fsm_rx

        # FSMTransitionLog should NOT be in __all__ to avoid AppRegistryNotReady
        assert "FSMTransitionLog" not in django_fsm_rx.__all__

    def test_star_import_includes_core_symbols(self):
        """Star import should include all core FSM symbols."""
        import django_fsm_rx

        expected_symbols = [
            "TransitionNotAllowed",
            "ConcurrentTransition",
            "InvalidResultState",
            "FSMFieldMixin",
            "FSMField",
            "FSMIntegerField",
            "FSMKeyField",
            "FSMModelMixin",
            "ConcurrentTransitionMixin",
            "transition",
            "can_proceed",
            "has_transition_perm",
            "GET_STATE",
            "RETURN_VALUE",
            "State",
            "Transition",
            "TransitionCallback",
            "FSMMeta",
            "fsm_rx_settings",
            "create_audit_log",
            "get_audit_log_model",
        ]

        for symbol in expected_symbols:
            assert symbol in django_fsm_rx.__all__, f"{symbol} missing from __all__"

    def test_star_import_works_in_subprocess(self):
        """Star import should work in a fresh Python process without Django setup."""
        # This tests that the import doesn't crash before Django is configured
        code = "from django_fsm_rx import *; print('OK')"
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Star import failed: {result.stderr}"
        assert "OK" in result.stdout


class TestFSMTransitionLogImport:
    """Tests for FSMTransitionLog lazy import behavior."""

    def test_fsm_transition_log_accessible_via_getattr(self):
        """FSMTransitionLog should be accessible after Django apps are ready."""
        # Django is already set up by pytest-django
        from django_fsm_rx import FSMTransitionLog

        assert FSMTransitionLog is not None
        assert FSMTransitionLog._meta.model_name == "fsmtransitionlog"

    def test_fsm_transition_log_has_expected_fields(self):
        """FSMTransitionLog should have the expected fields."""
        from django_fsm_rx import FSMTransitionLog

        field_names = {f.name for f in FSMTransitionLog._meta.get_fields()}

        expected_fields = {
            "id",
            "content_type",
            "object_id",
            "transition_name",
            "source_state",
            "target_state",
            "timestamp",
            "by",  # User who triggered the transition
            "description",  # Optional description
        }

        for field in expected_fields:
            assert field in field_names, f"Missing field: {field}"

    def test_fsm_transition_log_import_before_django_setup_fails(self):
        """Importing FSMTransitionLog before Django setup should fail gracefully."""
        # Test in subprocess to ensure clean state
        code = """
import sys
# Don't set up Django
try:
    from django_fsm_rx import FSMTransitionLog
    print("UNEXPECTED_SUCCESS")
except Exception as e:
    print(f"EXPECTED_ERROR: {type(e).__name__}")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
        )
        # Should fail with AppRegistryNotReady or similar
        assert "UNEXPECTED_SUCCESS" not in result.stdout, "Import should have failed"


class TestBackwardsCompatibilityShims:
    """Tests for backwards compatibility with django_fsm and django_fsm_2."""

    def test_django_fsm_shim_exports_all_symbols(self):
        """django_fsm shim should export all symbols from django_fsm_rx."""
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            import django_fsm

        # Core symbols should be available
        assert hasattr(django_fsm, "FSMField")
        assert hasattr(django_fsm, "transition")
        assert hasattr(django_fsm, "can_proceed")
        assert hasattr(django_fsm, "TransitionNotAllowed")

    def test_django_fsm_shim_shows_deprecation_warning(self):
        """django_fsm shim should show deprecation warning."""
        # Clear any cached import
        import sys
        import warnings

        if "django_fsm" in sys.modules:
            del sys.modules["django_fsm"]

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            import django_fsm  # noqa: F401

            # Check for deprecation warning
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1
            assert "django_fsm_rx" in str(deprecation_warnings[0].message)

    def test_django_fsm_2_shim_exports_all_symbols(self):
        """django_fsm_2 shim should export all symbols from django_fsm_rx."""
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            import django_fsm_2

        # Core symbols should be available
        assert hasattr(django_fsm_2, "FSMField")
        assert hasattr(django_fsm_2, "transition")
        assert hasattr(django_fsm_2, "can_proceed")
        assert hasattr(django_fsm_2, "TransitionNotAllowed")

    def test_django_fsm_2_shim_shows_deprecation_warning(self):
        """django_fsm_2 shim should show deprecation warning."""
        # Clear any cached import
        import sys
        import warnings

        if "django_fsm_2" in sys.modules:
            del sys.modules["django_fsm_2"]

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            import django_fsm_2  # noqa: F401

            # Check for deprecation warning
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1
            assert "django_fsm_rx" in str(deprecation_warnings[0].message)


class TestAuditLoggingExports:
    """Tests for audit logging function exports."""

    def test_create_audit_log_exported(self):
        """create_audit_log should be importable from django_fsm_rx."""
        from django_fsm_rx import create_audit_log

        assert callable(create_audit_log)

    def test_get_audit_log_model_exported(self):
        """get_audit_log_model should be importable from django_fsm_rx."""
        from django_fsm_rx import get_audit_log_model

        assert callable(get_audit_log_model)

    def test_audit_functions_in_all(self):
        """Audit functions should be in __all__."""
        import django_fsm_rx

        assert "create_audit_log" in django_fsm_rx.__all__
        assert "get_audit_log_model" in django_fsm_rx.__all__


class TestSettingsExport:
    """Tests for settings export."""

    def test_fsm_rx_settings_exported(self):
        """fsm_rx_settings should be importable from django_fsm_rx."""
        from django_fsm_rx import fsm_rx_settings

        assert fsm_rx_settings is not None
        assert hasattr(fsm_rx_settings, "ATOMIC")
        assert hasattr(fsm_rx_settings, "AUDIT_LOG")
        assert hasattr(fsm_rx_settings, "AUDIT_LOG_MODE")


class TestDjangoFSMLogShim:
    """Tests for django_fsm_log backwards compatibility shim."""

    def test_state_log_is_alias_to_fsm_transition_log(self):
        """StateLog should be an alias to FSMTransitionLog."""
        from django_fsm_log.models import StateLog
        from django_fsm_rx import FSMTransitionLog

        assert StateLog is FSMTransitionLog

    def test_state_log_uses_django_fsm_rx_app_label(self):
        """StateLog should use django_fsm_rx app_label (no separate app needed)."""
        from django_fsm_log.models import StateLog

        # StateLog is an alias, so it uses the same app_label as FSMTransitionLog
        assert StateLog._meta.app_label == "django_fsm_rx"

    def test_django_fsm_log_does_not_need_installed_apps(self):
        """django_fsm_log should work without being in INSTALLED_APPS."""
        # This test verifies that importing from django_fsm_log.models works
        # without django_fsm_log being in INSTALLED_APPS (only django_fsm_rx needed)
        from django_fsm_log.models import StateLog

        # The model should be fully functional
        assert StateLog._meta.model_name == "fsmtransitionlog"
        assert StateLog._meta.db_table == "django_fsm_rx_fsmtransitionlog"
