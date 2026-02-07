"""
Built-in audit log model for FSM transitions.

This model is always defined and migrations are created when 'django_fsm_rx'
is in INSTALLED_APPS.

Users who want to use a custom audit log model can set:
    DJANGO_FSM_RX = {
        'AUDIT_LOG_MODEL': 'myapp.TransitionLog',
    }
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from django.utils import timezone


class FSMTransitionLog(models.Model):
    """
    Default audit log model for FSM transitions.

    This model logs all state transitions with:
    - The model type and instance ID
    - Transition name (method name)
    - Source and target states
    - Timestamp
    - User who triggered the transition (optional)
    - Description (optional)

    To use this model, ensure 'django_fsm_rx' is in INSTALLED_APPS
    and run migrations.
    """

    content_type = models.ForeignKey(
        "contenttypes.ContentType",
        on_delete=models.CASCADE,
        help_text="The model type that was transitioned",
    )
    object_id = models.TextField(
        help_text="Primary key of the transitioned object",
    )
    content_object = GenericForeignKey("content_type", "object_id")
    transition_name = models.CharField(
        max_length=255,
        help_text="Name of the transition method",
    )
    source_state = models.CharField(
        max_length=255,
        help_text="State before transition",
    )
    target_state = models.CharField(
        max_length=255,
        help_text="State after transition",
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text="When the transition occurred",
    )
    by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="User who triggered the transition",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Optional description of the transition",
    )

    class Meta:
        app_label = "django_fsm_rx"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["-timestamp"]),
        ]

    def __str__(self) -> str:
        return f"{self.content_type} #{self.object_id}: {self.source_state} -> {self.target_state}"

    # Backwards compatibility aliases for django-fsm-log's StateLog field names
    @property
    def state(self) -> str:
        """Backwards compatibility alias for target_state (django-fsm-log compatibility)."""
        return self.target_state

    @state.setter
    def state(self, value: str) -> None:
        """Backwards compatibility setter for target_state."""
        self.target_state = value

    @property
    def transition(self) -> str:
        """Backwards compatibility alias for transition_name (django-fsm-log compatibility)."""
        return self.transition_name

    @transition.setter
    def transition(self, value: str) -> None:
        """Backwards compatibility setter for transition_name."""
        self.transition_name = value
