"""
Tests for Transition __eq__ and __hash__ behavior.

Ported from django-fsm-2 to ensure parity. Verifies that:
- Transition equals its name string but not a different Transition with the
  same name but different method identity.
- Transitions with the same name from different models are not equal and
  have different hashes.
"""

from __future__ import annotations

from django.db import models

from django_fsm_rx import Transition


def test_transition_eq_matches_name_and_transition() -> None:
    def publish() -> None:
        pass

    transition = Transition(
        method=publish,
        source="new",
        target="published",
        on_error=None,
        conditions=[],
        permission=None,
        custom={},
    )

    def other() -> None:
        pass

    other.__name__ = "publish"
    other_transition = Transition(
        method=other,
        source="new",
        target="published",
        on_error=None,
        conditions=[],
        permission=None,
        custom={},
    )

    assert transition == "publish"
    assert transition != other_transition
    assert transition != "other"
    assert transition != object()


def test_transition_same_name_different_models_not_equal() -> None:
    class First(models.Model):
        class Meta:
            app_label = "testapp"

        def publish(self) -> None:
            pass

    class Second(models.Model):
        class Meta:
            app_label = "testapp"

        def publish(self) -> None:
            pass

    first_transition = Transition(
        method=First.publish,
        source="new",
        target="published",
        on_error=None,
        conditions=[],
        permission=None,
        custom={},
    )
    second_transition = Transition(
        method=Second.publish,
        source="new",
        target="published",
        on_error=None,
        conditions=[],
        permission=None,
        custom={},
    )

    assert first_transition != second_transition
    assert hash(first_transition) != hash(second_transition)
