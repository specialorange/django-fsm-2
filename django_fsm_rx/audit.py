"""
Automatic audit logging for FSM transitions.

This module provides automatic transition logging with two modes:

1. **Transaction mode** (default): Audit log is created inside the atomic transaction,
   so it rolls back if the transition fails. This is the recommended mode.

2. **Signal mode**: Audit log is created via post_transition signal, decoupled from
   the transition. Use this if you want audit logs even for failed transactions.

Usage:
    # settings.py - Default behavior (transaction-based audit logging)
    INSTALLED_APPS = [
        ...
        'django_fsm_rx',
    ]
    # Run: python manage.py migrate django_fsm_rx

    # settings.py - Use signal-based audit logging
    DJANGO_FSM_RX = {
        'AUDIT_LOG_MODE': 'signal',
    }

    # settings.py - Disable audit logging
    DJANGO_FSM_RX = {
        'AUDIT_LOG': False,
    }

    # settings.py - Use custom audit log model
    DJANGO_FSM_RX = {
        'AUDIT_LOG_MODEL': 'myapp.TransitionLog',
    }
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import Any

from django.apps import apps
from django.db import models
from django.dispatch import receiver

from django_fsm_rx.conf import fsm_rx_settings
from django_fsm_rx.signals import post_transition

if TYPE_CHECKING:
    from django.db.models import Model

logger = logging.getLogger(__name__)


def get_audit_log_model() -> type[models.Model] | None:
    """
    Get the configured audit log model.

    Returns the custom model if AUDIT_LOG_MODEL is set, otherwise returns
    the default FSMTransitionLog model.

    Returns:
        The audit log model class, or None if audit logging is disabled.
    """
    if not fsm_rx_settings.AUDIT_LOG:
        return None

    custom_model = fsm_rx_settings.AUDIT_LOG_MODEL
    if custom_model:
        try:
            return apps.get_model(custom_model)
        except LookupError:
            logger.error(f"AUDIT_LOG_MODEL '{custom_model}' not found. Audit logging disabled.")
            return None

    # Use built-in model
    try:
        return apps.get_model("django_fsm_rx", "FSMTransitionLog")
    except LookupError:
        logger.warning(
            "FSMTransitionLog model not found. "
            "Ensure 'django_fsm_rx' is in INSTALLED_APPS and migrations have been run, "
            "or set AUDIT_LOG_MODEL to use a custom model."
        )
        return None


def create_audit_log(
    instance: Model,
    transition_name: str,
    source_state: str,
    target_state: str,
    **kwargs: Any,
) -> models.Model | None:
    """
    Create an audit log entry for a transition.

    Args:
        instance: The model instance that transitioned
        transition_name: Name of the transition method
        source_state: State before transition
        target_state: State after transition
        **kwargs: Additional fields to set on the log entry

    Returns:
        The created log entry, or None if audit logging is disabled
    """
    model = get_audit_log_model()
    if model is None:
        return None

    # Import ContentType lazily to avoid AppRegistryNotReady during module import
    from django.contrib.contenttypes.models import ContentType

    content_type = ContentType.objects.get_for_model(instance)

    log_data = {
        "content_type": content_type,
        "object_id": str(instance.pk) if instance.pk else "",
        "transition_name": transition_name,
        "source_state": str(source_state) if source_state else "",
        "target_state": str(target_state) if target_state else "",
    }

    # Allow custom models to accept additional fields
    model_fields = {f.name for f in model._meta.get_fields()}
    log_data.update({k: v for k, v in kwargs.items() if k in model_fields})

    return model.objects.create(**log_data)


def _create_audit_log_safe(
    instance: Model,
    transition_name: str,
    source_state: str,
    target_state: str,
    **kwargs: Any,
) -> None:
    """
    Create audit log with exception handling.

    This wrapper catches exceptions to prevent audit logging failures
    from breaking transitions.
    """
    try:
        create_audit_log(
            instance=instance,
            transition_name=transition_name,
            source_state=source_state,
            target_state=target_state,
            **kwargs,
        )
    except Exception as e:
        logger.exception(f"Failed to create audit log for {type(instance).__name__}.{transition_name}: {e}")


def transaction_audit_callback(
    instance: Model,
    source: str,
    target: str,
    **kwargs: Any,
) -> None:
    """
    Callback for transaction-mode audit logging.

    This is called internally by the transition decorator when AUDIT_LOG_MODE='transaction'.
    It runs inside the atomic block, so the audit log rolls back if the transition fails.
    """
    if not fsm_rx_settings.AUDIT_LOG:
        return

    if fsm_rx_settings.AUDIT_LOG_MODE != "transaction":
        return

    # Get transition name from kwargs if available
    transition_name = kwargs.get("transition_name", "unknown")

    # Read log metadata set by fsm_log_by/fsm_log_description decorators
    extra = {}
    log_by = getattr(instance, "_fsm_log_by", None)
    if log_by is not None:
        extra["by"] = log_by
    log_description = getattr(instance, "_fsm_log_description", None)
    if log_description is not None:
        extra["description"] = log_description

    _create_audit_log_safe(
        instance=instance,
        transition_name=transition_name,
        source_state=source,
        target_state=target,
        **extra,
    )


@receiver(post_transition)
def signal_audit_log(
    sender: type[Model],
    instance: Model,
    name: str,
    source: str,
    target: str,
    **kwargs: Any,
) -> None:
    """
    Signal receiver for signal-mode audit logging.

    Only active when AUDIT_LOG=True and AUDIT_LOG_MODE='signal'.
    This runs after the transition completes, outside the atomic block.
    """
    if not fsm_rx_settings.AUDIT_LOG:
        return

    if fsm_rx_settings.AUDIT_LOG_MODE != "signal":
        return

    # Read log metadata set by fsm_log_by/fsm_log_description decorators
    extra = {}
    log_by = getattr(instance, "_fsm_log_by", None)
    if log_by is not None:
        extra["by"] = log_by
    log_description = getattr(instance, "_fsm_log_description", None)
    if log_description is not None:
        extra["description"] = log_description

    _create_audit_log_safe(
        instance=instance,
        transition_name=name,
        source_state=source,
        target_state=target,
        **extra,
    )
