"""
Regression tests for audit log metadata passthrough.

These tests verify that _fsm_log_by and _fsm_log_description set by the
fsm_log_by/fsm_log_description decorators are correctly passed through to
the audit log callbacks in both transaction and signal modes.

Regression: Prior to the fix, transaction_audit_callback and signal_audit_log
did not read _fsm_log_by/_fsm_log_description from the instance, so the
'by' and 'description' fields were never populated in FSMTransitionLog entries.
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django.db import models
from django.test import override_settings

from django_fsm_rx import FSMField
from django_fsm_rx import transition
from django_fsm_rx.conf import fsm_rx_settings
from django_fsm_rx.log import fsm_log_by
from django_fsm_rx.log import fsm_log_context
from django_fsm_rx.log import fsm_log_description


@contextmanager
def override_fsm_settings(**kwargs):
    """Context manager that overrides Django settings and clears the FSM settings cache."""
    with override_settings(DJANGO_FSM_RX=kwargs):
        fsm_rx_settings.clear_cache()
        try:
            yield
        finally:
            fsm_rx_settings.clear_cache()


# =============================================================================
# Test Models
# =============================================================================


class LogMetadataModel(models.Model):
    """Model with fsm_log_by and fsm_log_description decorators for testing audit passthrough."""

    state = FSMField(default="new")

    @fsm_log_by
    @fsm_log_description
    @transition(field=state, source="new", target="active")
    def activate(self, by=None, description=None):
        pass

    @fsm_log_by
    @transition(field=state, source="active", target="complete")
    def complete(self, by=None):
        pass

    @fsm_log_description
    @transition(field=state, source="*", target="cancelled")
    def cancel(self, description=None):
        pass

    @transition(field=state, source="new", target="skipped")
    def skip(self):
        """Transition with no log decorators."""
        pass

    class Meta:
        app_label = "tests"


# =============================================================================
# Transaction Mode: _fsm_log_by / _fsm_log_description passthrough
# =============================================================================


class TestTransactionModeLogMetadata:
    """Verify transaction_audit_callback reads _fsm_log_by and _fsm_log_description from the instance."""

    def test_by_passed_to_audit_log(self):
        """_fsm_log_by should be passed as 'by' kwarg to _create_audit_log_safe."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="transaction"):
            model = LogMetadataModel()
            mock_user = MagicMock()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.activate(by=mock_user)

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["by"] == mock_user

    def test_description_passed_to_audit_log(self):
        """_fsm_log_description should be passed as 'description' kwarg to _create_audit_log_safe."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="transaction"):
            model = LogMetadataModel()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.activate(description="Activating for test")

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["description"] == "Activating for test"

    def test_both_by_and_description_passed(self):
        """Both _fsm_log_by and _fsm_log_description should be passed together."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="transaction"):
            model = LogMetadataModel()
            mock_user = MagicMock()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.activate(by=mock_user, description="Full metadata")

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["by"] == mock_user
                assert call_kwargs["description"] == "Full metadata"
                assert call_kwargs["source_state"] == "new"
                assert call_kwargs["target_state"] == "active"

    def test_no_metadata_when_not_provided(self):
        """When no by/description provided, they should not appear in audit kwargs."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="transaction"):
            model = LogMetadataModel()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.activate()

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert "by" not in call_kwargs
                assert "description" not in call_kwargs

    def test_only_by_decorator(self):
        """Transition with only @fsm_log_by should only pass 'by'."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="transaction"):
            model = LogMetadataModel()
            model.state = "active"
            mock_user = MagicMock()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.complete(by=mock_user)

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["by"] == mock_user
                assert "description" not in call_kwargs

    def test_only_description_decorator(self):
        """Transition with only @fsm_log_description should only pass 'description'."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="transaction"):
            model = LogMetadataModel()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.cancel(description="Cancelled by admin")

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["description"] == "Cancelled by admin"
                assert "by" not in call_kwargs

    def test_no_decorators_no_metadata(self):
        """Transition without log decorators should have no metadata."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="transaction"):
            model = LogMetadataModel()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.skip()

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert "by" not in call_kwargs
                assert "description" not in call_kwargs


# =============================================================================
# Signal Mode: _fsm_log_by / _fsm_log_description passthrough
# =============================================================================


class TestSignalModeLogMetadata:
    """Verify signal_audit_log reads _fsm_log_by and _fsm_log_description from the instance."""

    def test_by_passed_to_audit_log(self):
        """_fsm_log_by should be passed as 'by' kwarg in signal mode."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="signal"):
            model = LogMetadataModel()
            mock_user = MagicMock()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.activate(by=mock_user)

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["by"] == mock_user

    def test_description_passed_to_audit_log(self):
        """_fsm_log_description should be passed as 'description' kwarg in signal mode."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="signal"):
            model = LogMetadataModel()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.activate(description="Signal mode test")

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["description"] == "Signal mode test"

    def test_both_by_and_description_passed(self):
        """Both metadata fields should be passed in signal mode."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="signal"):
            model = LogMetadataModel()
            mock_user = MagicMock()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.activate(by=mock_user, description="Signal full metadata")

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["by"] == mock_user
                assert call_kwargs["description"] == "Signal full metadata"

    def test_no_metadata_when_not_provided(self):
        """When no by/description provided in signal mode, they should not appear."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="signal"):
            model = LogMetadataModel()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.activate()

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert "by" not in call_kwargs
                assert "description" not in call_kwargs


# =============================================================================
# fsm_log_context passthrough
# =============================================================================


class TestLogContextAuditPassthrough:
    """Verify fsm_log_context metadata is passed through to audit callbacks."""

    def test_context_by_passed_to_transaction_audit(self):
        """fsm_log_context(by=user) should result in 'by' in audit log."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="transaction"):
            model = LogMetadataModel()
            mock_user = MagicMock()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                with fsm_log_context(model, by=mock_user):
                    model.skip()

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["by"] == mock_user

    def test_context_description_passed_to_transaction_audit(self):
        """fsm_log_context(description=...) should result in 'description' in audit log."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="transaction"):
            model = LogMetadataModel()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                with fsm_log_context(model, description="Context description"):
                    model.skip()

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["description"] == "Context description"

    def test_context_both_passed_to_signal_audit(self):
        """fsm_log_context with both args should pass both in signal mode."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="signal"):
            model = LogMetadataModel()
            mock_user = MagicMock()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                with fsm_log_context(model, by=mock_user, description="Both in signal"):
                    model.skip()

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["by"] == mock_user
                assert call_kwargs["description"] == "Both in signal"


# =============================================================================
# Parametrized: both modes x various metadata combinations
# =============================================================================


class TestAuditLogMetadataParametrized:
    """Parametrized tests covering both audit modes with various metadata combinations."""

    @pytest.mark.parametrize("audit_mode", ["transaction", "signal"])
    def test_by_only(self, audit_mode):
        """'by' metadata should be passed in both audit modes."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE=audit_mode):
            model = LogMetadataModel()
            mock_user = MagicMock()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.activate(by=mock_user)

                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["by"] == mock_user

    @pytest.mark.parametrize("audit_mode", ["transaction", "signal"])
    def test_description_only(self, audit_mode):
        """'description' metadata should be passed in both audit modes."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE=audit_mode):
            model = LogMetadataModel()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.activate(description="Test desc")

                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["description"] == "Test desc"

    @pytest.mark.parametrize("audit_mode", ["transaction", "signal"])
    def test_no_metadata(self, audit_mode):
        """No metadata should be passed when neither by nor description provided."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE=audit_mode):
            model = LogMetadataModel()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.activate()

                call_kwargs = mock_create.call_args[1]
                assert "by" not in call_kwargs
                assert "description" not in call_kwargs

    @pytest.mark.parametrize("audit_mode", ["transaction", "signal"])
    def test_disabled_audit_no_call(self, audit_mode):
        """When audit logging is disabled, _create_audit_log_safe should not be called."""
        with override_fsm_settings(AUDIT_LOG=False, AUDIT_LOG_MODE=audit_mode):
            model = LogMetadataModel()
            mock_user = MagicMock()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.activate(by=mock_user, description="Should not log")

                mock_create.assert_not_called()

    @pytest.mark.parametrize("audit_mode", ["transaction", "signal"])
    def test_metadata_cleared_after_transition(self, audit_mode):
        """_fsm_log_by and _fsm_log_description should be cleaned up after transition."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE=audit_mode):
            model = LogMetadataModel()
            mock_user = MagicMock()

            with patch("django_fsm_rx.audit._create_audit_log_safe"):
                model.activate(by=mock_user, description="Temp metadata")

            assert not hasattr(model, "_fsm_log_by")
            assert not hasattr(model, "_fsm_log_description")


# =============================================================================
# Custom _fsm_log_* attributes (extensibility)
# =============================================================================


class TestCustomFSMLogAttributes:
    """Verify that any _fsm_log_* attribute is picked up, not just by/description."""

    @pytest.mark.parametrize("audit_mode", ["transaction", "signal"])
    def test_custom_fsm_log_attribute_passed(self, audit_mode):
        """Custom _fsm_log_* attributes should be passed through to audit log."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE=audit_mode):
            model = LogMetadataModel()
            # Manually set a custom _fsm_log_* attribute (as a custom decorator would)
            model._fsm_log_reason = "compliance check"

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.skip()

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["reason"] == "compliance check"

            # Clean up
            if hasattr(model, "_fsm_log_reason"):
                delattr(model, "_fsm_log_reason")

    @pytest.mark.parametrize("audit_mode", ["transaction", "signal"])
    def test_multiple_custom_attributes_passed(self, audit_mode):
        """Multiple custom _fsm_log_* attributes should all be passed."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE=audit_mode):
            model = LogMetadataModel()
            model._fsm_log_ip_address = "192.168.1.1"
            model._fsm_log_request_id = "abc-123"

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.skip()

                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["ip_address"] == "192.168.1.1"
                assert call_kwargs["request_id"] == "abc-123"

            # Clean up
            for attr in ("_fsm_log_ip_address", "_fsm_log_request_id"):
                if hasattr(model, attr):
                    delattr(model, attr)

    @pytest.mark.parametrize("audit_mode", ["transaction", "signal"])
    def test_none_valued_custom_attributes_excluded(self, audit_mode):
        """_fsm_log_* attributes with None value should not be passed."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE=audit_mode):
            model = LogMetadataModel()
            model._fsm_log_optional = None

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.skip()

                call_kwargs = mock_create.call_args[1]
                assert "optional" not in call_kwargs

            # Clean up
            if hasattr(model, "_fsm_log_optional"):
                delattr(model, "_fsm_log_optional")
