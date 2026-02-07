"""
Tests for migration utilities and backwards compatibility shims.

These tests verify:
- Migration utility functions work correctly
- Import scanning finds deprecated imports
- Model validation works correctly
- Backwards compatibility shims work for all packages
"""

from __future__ import annotations

import sys
import tempfile
import warnings
from pathlib import Path

import pytest
from django.db import models

from django_fsm_rx import FSMField
from django_fsm_rx import FSMModelMixin
from django_fsm_rx import transition
from django_fsm_rx.migration import IMPORT_MAPPINGS
from django_fsm_rx.migration import MigrationReport
from django_fsm_rx.migration import get_import_replacements
from django_fsm_rx.migration import scan_imports_in_directory
from django_fsm_rx.migration import scan_imports_in_file
from django_fsm_rx.migration import validate_model_fsm_compatibility


class TestMigrationReport:
    """Tests for MigrationReport class."""

    def test_empty_report_is_fully_migrated(self):
        """Empty report should indicate full migration."""
        report = MigrationReport()
        assert report.is_fully_migrated is True
        assert len(report.deprecated_imports) == 0

    def test_report_with_deprecated_import(self):
        """Report with deprecated import is not fully migrated."""
        report = MigrationReport()
        report.add_deprecated_import(
            file_path="test.py",
            line_number=1,
            old_import="from django_fsm import FSMField",
            new_import="from django_fsm_rx import FSMField",
            notes="Direct replacement",
        )
        assert report.is_fully_migrated is False
        assert len(report.deprecated_imports) == 1
        assert "test.py" in report.files_affected

    def test_report_str_empty(self):
        """Test string representation of empty report."""
        report = MigrationReport()
        report_str = str(report)
        assert "Migration complete" in report_str

    def test_report_str_with_issues(self):
        """Test string representation of report with issues."""
        report = MigrationReport()
        report.add_deprecated_import(
            file_path="models.py",
            line_number=5,
            old_import="from django_fsm import FSMField",
            new_import="from django_fsm_rx import FSMField",
            notes="API identical",
        )
        report_str = str(report)
        assert "Files affected: 1" in report_str
        assert "models.py:5" in report_str
        assert "django_fsm" in report_str

    def test_add_warning(self):
        """Test adding warnings to report."""
        report = MigrationReport()
        report.add_warning("Test warning message")
        assert "Test warning message" in report.warnings


class TestImportMappings:
    """Tests for import mappings."""

    def test_import_mappings_exist(self):
        """Import mappings should be populated."""
        assert len(IMPORT_MAPPINGS) > 0

    def test_django_fsm_mappings_exist(self):
        """Mappings for django_fsm should exist."""
        django_fsm_mappings = [m for m in IMPORT_MAPPINGS if m["old_module"] == "django_fsm"]
        assert len(django_fsm_mappings) > 0
        # Check for key symbols
        names = [m["old_name"] for m in django_fsm_mappings]
        assert "FSMField" in names
        assert "transition" in names
        assert "can_proceed" in names

    def test_django_fsm_2_mappings_exist(self):
        """Mappings for django_fsm_2 should exist."""
        django_fsm_2_mappings = [m for m in IMPORT_MAPPINGS if m["old_module"] == "django_fsm_2"]
        assert len(django_fsm_2_mappings) > 0

    def test_django_fsm_admin_mappings_exist(self):
        """Mappings for django_fsm_admin should exist."""
        admin_mappings = [m for m in IMPORT_MAPPINGS if "django_fsm_admin" in m["old_module"]]
        assert len(admin_mappings) > 0
        # Check FSMTransitionMixin mapping
        mixin_mappings = [m for m in admin_mappings if m["old_name"] == "FSMTransitionMixin"]
        assert len(mixin_mappings) > 0

    def test_django_fsm_log_mappings_exist(self):
        """Mappings for django_fsm_log should exist."""
        log_mappings = [m for m in IMPORT_MAPPINGS if "django_fsm_log" in m["old_module"]]
        assert len(log_mappings) > 0
        # Check key mappings
        names = [m["old_name"] for m in log_mappings]
        assert "StateLog" in names
        assert "fsm_log_by" in names

    def test_get_import_replacements(self):
        """Test get_import_replacements returns valid dict."""
        replacements = get_import_replacements()
        assert isinstance(replacements, dict)
        assert len(replacements) > 0

        # Check specific replacement
        key = "from django_fsm import FSMField"
        assert key in replacements
        assert replacements[key] == "from django_fsm_rx import FSMField"


class TestScanImportsInFile:
    """Tests for scan_imports_in_file function."""

    def test_scan_nonexistent_file(self):
        """Scanning nonexistent file should add warning."""
        report = scan_imports_in_file("/nonexistent/path/file.py")
        assert len(report.warnings) == 1
        assert "not found" in report.warnings[0]

    def test_scan_non_python_file(self):
        """Scanning non-Python file should return empty report."""
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            f.write("from django_fsm import FSMField")
            f.flush()
            report = scan_imports_in_file(f.name)
            # Non-.py files should be skipped
            assert report.is_fully_migrated

    def test_scan_file_with_deprecated_import(self):
        """Scanning file with deprecated import should find it."""
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("from django_fsm import FSMField, transition\n")
            f.write("from django.db import models\n")
            f.flush()

            report = scan_imports_in_file(f.name)
            assert report.is_fully_migrated is False
            assert len(report.deprecated_imports) >= 1

    def test_scan_file_with_clean_imports(self):
        """Scanning file with modern imports should be clean."""
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("from django_fsm_rx import FSMField, transition\n")
            f.write("from django.db import models\n")
            f.flush()

            report = scan_imports_in_file(f.name)
            assert report.is_fully_migrated is True

    def test_scan_file_with_comment(self):
        """Scanning should ignore commented imports."""
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("# from django_fsm import FSMField\n")
            f.write("from django_fsm_rx import FSMField\n")
            f.flush()

            report = scan_imports_in_file(f.name)
            assert report.is_fully_migrated is True

    def test_scan_file_with_django_fsm_admin_import(self):
        """Scanning should detect django_fsm_admin imports."""
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("from django_fsm_admin.mixins import FSMTransitionMixin\n")
            f.flush()

            report = scan_imports_in_file(f.name)
            assert report.is_fully_migrated is False
            assert any("FSMTransitionMixin" in imp["old"] for imp in report.deprecated_imports)

    def test_scan_file_with_django_fsm_log_import(self):
        """Scanning should detect django_fsm_log imports."""
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("from django_fsm_log.models import StateLog\n")
            f.flush()

            report = scan_imports_in_file(f.name)
            assert report.is_fully_migrated is False
            assert any("StateLog" in imp["old"] for imp in report.deprecated_imports)


class TestScanImportsInDirectory:
    """Tests for scan_imports_in_directory function."""

    def test_scan_nonexistent_directory(self):
        """Scanning nonexistent directory should add warning."""
        report = scan_imports_in_directory("/nonexistent/directory")
        assert len(report.warnings) == 1
        assert "not found" in report.warnings[0]

    def test_scan_directory_with_mixed_files(self):
        """Scanning directory should find deprecated imports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file with deprecated import
            deprecated_file = Path(tmpdir) / "models.py"
            deprecated_file.write_text("from django_fsm import FSMField\n")

            # Create clean file
            clean_file = Path(tmpdir) / "views.py"
            clean_file.write_text("from django_fsm_rx import FSMField\n")

            report = scan_imports_in_directory(tmpdir)
            assert report.is_fully_migrated is False
            assert str(deprecated_file) in report.files_affected
            assert str(clean_file) not in report.files_affected

    def test_scan_directory_excludes_patterns(self):
        """Scanning should exclude specified patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file in excluded directory
            migrations_dir = Path(tmpdir) / "migrations"
            migrations_dir.mkdir()
            excluded_file = migrations_dir / "0001_initial.py"
            excluded_file.write_text("from django_fsm import FSMField\n")

            report = scan_imports_in_directory(tmpdir, exclude_patterns=["migrations"])
            assert report.is_fully_migrated is True


class TestValidateModelFSMCompatibility:
    """Tests for validate_model_fsm_compatibility function."""

    def test_validate_model_without_fsm_fields(self):
        """Model without FSM fields should warn."""

        class PlainModel(models.Model):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "testapp"

        warnings_list = validate_model_fsm_compatibility(PlainModel)
        assert len(warnings_list) == 1
        assert "no FSM fields" in warnings_list[0]

    def test_validate_model_with_fsm_field(self):
        """Model with properly configured FSM field should pass."""

        class ValidModel(models.Model):
            state = FSMField(default="new")

            @transition(field=state, source="new", target="done")
            def finish(self):
                pass

            class Meta:
                app_label = "testapp"

        warnings_list = validate_model_fsm_compatibility(ValidModel)
        assert len(warnings_list) == 0

    def test_validate_model_with_protected_field_no_mixin(self):
        """Protected field without FSMModelMixin should warn."""

        class ProtectedNoMixin(models.Model):
            state = FSMField(default="new", protected=True)

            @transition(field=state, source="new", target="done")
            def finish(self):
                pass

            class Meta:
                app_label = "testapp"

        warnings_list = validate_model_fsm_compatibility(ProtectedNoMixin)
        assert len(warnings_list) == 1
        assert "FSMModelMixin" in warnings_list[0]

    def test_validate_model_with_protected_field_and_mixin(self):
        """Protected field with FSMModelMixin should pass."""

        class ProtectedWithMixin(FSMModelMixin, models.Model):
            state = FSMField(default="new", protected=True)

            @transition(field=state, source="new", target="done")
            def finish(self):
                pass

            class Meta:
                app_label = "testapp"

        warnings_list = validate_model_fsm_compatibility(ProtectedWithMixin)
        assert len(warnings_list) == 0


class TestDjangoFSMShimBackwardsCompatibility:
    """Tests for django_fsm backwards compatibility shim."""

    def test_django_fsm_imports_work(self):
        """Imports from django_fsm should work with deprecation warning."""
        # Clear cached import
        if "django_fsm" in sys.modules:
            del sys.modules["django_fsm"]

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            import django_fsm

            # Should have deprecation warning
            assert any(issubclass(x.category, DeprecationWarning) for x in w)

            # Core symbols should be available
            assert hasattr(django_fsm, "FSMField")
            assert hasattr(django_fsm, "FSMIntegerField")
            assert hasattr(django_fsm, "transition")
            assert hasattr(django_fsm, "can_proceed")
            assert hasattr(django_fsm, "TransitionNotAllowed")

    def test_django_fsm_signals_work(self):
        """Imports from django_fsm.signals should work."""
        # Note: The main django_fsm import already triggers warning
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            import django_fsm

            assert hasattr(django_fsm, "FSMField")


class TestDjangoFSM2ShimBackwardsCompatibility:
    """Tests for django_fsm_2 backwards compatibility shim."""

    def test_django_fsm_2_imports_work(self):
        """Imports from django_fsm_2 should work with deprecation warning."""
        # Clear cached import
        if "django_fsm_2" in sys.modules:
            del sys.modules["django_fsm_2"]

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            import django_fsm_2

            # Should have deprecation warning
            assert any(issubclass(x.category, DeprecationWarning) for x in w)

            # Core symbols should be available
            assert hasattr(django_fsm_2, "FSMField")
            assert hasattr(django_fsm_2, "transition")
            assert hasattr(django_fsm_2, "can_proceed")


class TestDjangoFSMAdminShimBackwardsCompatibility:
    """Tests for django_fsm_admin backwards compatibility shim."""

    def test_django_fsm_admin_imports_work(self):
        """Imports from django_fsm_admin should work with deprecation warning."""
        # Clear cached imports
        for mod in list(sys.modules.keys()):
            if "django_fsm_admin" in mod:
                del sys.modules[mod]

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            import django_fsm_admin

            # Should have deprecation warning
            assert any(issubclass(x.category, DeprecationWarning) for x in w)

            # FSMTransitionMixin should be available
            assert hasattr(django_fsm_admin, "FSMTransitionMixin")
            assert hasattr(django_fsm_admin, "FSMAdminMixin")

    def test_django_fsm_admin_mixins_imports_work(self):
        """Imports from django_fsm_admin.mixins should work."""
        # Clear cached imports
        for mod in list(sys.modules.keys()):
            if "django_fsm_admin" in mod:
                del sys.modules[mod]

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from django_fsm_admin.mixins import FSMTransitionMixin

            # Should have deprecation warning
            assert any(issubclass(x.category, DeprecationWarning) for x in w)

            # FSMTransitionMixin should be the same as FSMAdminMixin
            from django_fsm_rx.admin import FSMAdminMixin

            assert FSMTransitionMixin is FSMAdminMixin


class TestDjangoFSMLogShimBackwardsCompatibility:
    """Tests for django_fsm_log backwards compatibility shim."""

    def test_django_fsm_log_models_import_works(self):
        """Imports from django_fsm_log.models should work."""
        from django_fsm_log.models import StateLog
        from django_fsm_rx import FSMTransitionLog

        # StateLog is an alias to FSMTransitionLog
        assert StateLog is FSMTransitionLog

    def test_state_log_field_aliases_work(self):
        """StateLog field aliases (state, transition) should work for backwards compatibility."""
        from django_fsm_log.models import StateLog

        # Create an unsaved instance to test field access
        log = StateLog(
            transition_name="publish",
            source_state="draft",
            target_state="published",
        )

        # Old field names should work via property aliases
        assert log.state == "published"  # alias for target_state
        assert log.transition == "publish"  # alias for transition_name

        # Setters should also work
        log.state = "archived"
        assert log.target_state == "archived"

        log.transition = "archive"
        assert log.transition_name == "archive"

    def test_django_fsm_log_decorators_import_works(self):
        """Imports from django_fsm_log.decorators should work."""
        # Clear cached imports
        for mod in list(sys.modules.keys()):
            if "django_fsm_log" in mod:
                del sys.modules[mod]

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from django_fsm_log.decorators import fsm_log_by
            from django_fsm_log.decorators import fsm_log_description

            # Should have deprecation warning
            assert any(issubclass(x.category, DeprecationWarning) for x in w)

            # Decorators should be callable
            assert callable(fsm_log_by)
            assert callable(fsm_log_description)

    def test_django_fsm_log_main_import_works(self):
        """Imports from django_fsm_log should work."""
        # Clear cached imports
        for mod in list(sys.modules.keys()):
            if "django_fsm_log" in mod:
                del sys.modules[mod]

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            import django_fsm_log

            # Should have deprecation warning
            assert any(issubclass(x.category, DeprecationWarning) for x in w)

            # Decorators should be available
            assert hasattr(django_fsm_log, "fsm_log_by")
            assert hasattr(django_fsm_log, "fsm_log_description")


class TestMigrationAPICompatibility:
    """Tests verifying API compatibility between old and new packages."""

    def test_fsm_field_api_compatibility(self):
        """FSMField API should be compatible."""
        from django_fsm_rx import FSMField as NewFSMField

        # Create field with same parameters as old package
        field = NewFSMField(default="new", protected=True)

        assert field.protected is True
        assert hasattr(field, "transitions")

    def test_transition_decorator_api_compatibility(self):
        """@transition decorator API should be compatible."""
        from django_fsm_rx import FSMField
        from django_fsm_rx import transition

        class TransitionDecoratorTestModel(models.Model):
            state = FSMField(default="new")

            # Old-style transition (should still work)
            @transition(field=state, source="new", target="done")
            def finish(self):
                pass

            # With conditions (should still work)
            def is_valid(self):
                return True

            @transition(field=state, source="done", target="archived", conditions=[is_valid])
            def archive(self):
                pass

            class Meta:
                app_label = "testapp"

        obj = TransitionDecoratorTestModel()
        assert obj.state == "new"
        obj.finish()
        assert obj.state == "done"

    def test_can_proceed_api_compatibility(self):
        """can_proceed API should be compatible."""
        from django_fsm_rx import FSMField
        from django_fsm_rx import can_proceed
        from django_fsm_rx import transition

        class CanProceedTestModel(models.Model):
            state = FSMField(default="new")

            @transition(field=state, source="new", target="done")
            def finish(self):
                pass

            class Meta:
                app_label = "testapp"

        obj = CanProceedTestModel()
        assert can_proceed(obj.finish) is True

        obj.finish()
        assert can_proceed(obj.finish) is False

    def test_transition_not_allowed_api_compatibility(self):
        """TransitionNotAllowed exception should be compatible."""
        from django_fsm_rx import FSMField
        from django_fsm_rx import TransitionNotAllowed
        from django_fsm_rx import transition

        class TransitionNotAllowedTestModel(models.Model):
            state = FSMField(default="new")

            @transition(field=state, source="pending", target="done")
            def finish(self):
                pass

            class Meta:
                app_label = "testapp"

        obj = TransitionNotAllowedTestModel()
        with pytest.raises(TransitionNotAllowed):
            obj.finish()


class TestNewFeatures:
    """Tests for new features in django-fsm-rx not in original packages."""

    def test_on_success_callback(self):
        """on_success callback should work."""
        callback_called = []

        def on_success_callback(instance, source, target, **kwargs):
            callback_called.append((source, target))

        class OnSuccessCallbackTestModel(models.Model):
            state = FSMField(default="new")

            @transition(field=state, source="new", target="done", on_success=on_success_callback)
            def finish(self):
                pass

            class Meta:
                app_label = "testapp"

        obj = OnSuccessCallbackTestModel()
        obj.finish()

        assert len(callback_called) == 1
        assert callback_called[0] == ("new", "done")

    def test_prefix_wildcard_source(self):
        """Prefix wildcard source (WRK-*) should work."""

        class PrefixWildcardTestModel(models.Model):
            state = FSMField(default="WRK-REP-PRG")

            @transition(field=state, source="WRK-*", target="DONE")
            def finish(self):
                pass

            class Meta:
                app_label = "testapp"

        obj = PrefixWildcardTestModel()
        assert obj.state == "WRK-REP-PRG"
        obj.finish()
        assert obj.state == "DONE"

        # Test another WRK- state
        obj2 = PrefixWildcardTestModel()
        obj2.state = "WRK-INS-PRG"
        obj2.finish()
        assert obj2.state == "DONE"

    def test_fsm_transition_log_model_exists(self):
        """FSMTransitionLog model should exist and be usable."""
        from django_fsm_rx import FSMTransitionLog

        assert FSMTransitionLog is not None
        assert FSMTransitionLog._meta.model_name == "fsmtransitionlog"

        # Check fields
        field_names = {f.name for f in FSMTransitionLog._meta.get_fields()}
        assert "content_type" in field_names
        assert "object_id" in field_names
        assert "transition_name" in field_names
        assert "source_state" in field_names
        assert "target_state" in field_names
        assert "timestamp" in field_names


class TestMigrationModule:
    """Tests for the migration module itself."""

    def test_migration_module_exports(self):
        """Migration module should export expected symbols."""
        from django_fsm_rx import migration

        assert hasattr(migration, "check_migration_status")
        assert hasattr(migration, "MigrationReport")
        assert hasattr(migration, "scan_imports_in_file")
        assert hasattr(migration, "scan_imports_in_directory")
        assert hasattr(migration, "get_import_replacements")
        assert hasattr(migration, "validate_model_fsm_compatibility")
        assert hasattr(migration, "IMPORT_MAPPINGS")

    def test_run_migration_check_command_function_exists(self):
        """run_migration_check_command should exist."""
        from django_fsm_rx.migration import run_migration_check_command

        assert callable(run_migration_check_command)
