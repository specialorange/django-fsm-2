"""Regression tests for the State.get_state() signature.

Upstream django-fsm-2 (#136) removed the misleading, always-unused
``transition`` parameter from ``State.get_state``. These tests pin the
new signature: ``get_state(model, result, args=..., kwargs=...)``.
"""

from __future__ import annotations

import inspect

from django.db import models
from django.test import TestCase

from django_fsm_rx import GET_STATE
from django_fsm_rx import RETURN_VALUE
from django_fsm_rx import FSMField
from django_fsm_rx import State
from django_fsm_rx import transition


class SignatureModel(models.Model):
    state = FSMField(default="new")

    @transition(field=state, source="new", target=RETURN_VALUE("a", "b"))
    def to_return_value(self, pick_a=True):
        return "a" if pick_a else "b"

    @transition(
        field=state,
        source="a",
        target=GET_STATE(
            lambda self, nxt: nxt,
            states=["c", "d"],
        ),
    )
    def to_get_state(self, nxt):
        pass

    class Meta:
        app_label = "testapp"


class StateSignatureTest(TestCase):
    def test_base_state_get_state_has_no_transition_param(self):
        params = list(inspect.signature(State.get_state).parameters)
        # self, model, result, args, kwargs -- no "transition"
        self.assertNotIn("transition", params)
        self.assertEqual(params, ["self", "model", "result", "args", "kwargs"])

    def test_return_value_get_state_callable_without_transition(self):
        rv = RETURN_VALUE("a", "b")
        # New calling convention: (model, result, ...) with no transition arg.
        self.assertEqual(rv.get_state(model=None, result="a"), "a")

    def test_get_state_callable_without_transition(self):
        instance = SignatureModel(state="a")
        gs = GET_STATE(lambda self, nxt: nxt, states=["c", "d"])
        self.assertEqual(
            gs.get_state(instance, result=None, args=("c",), kwargs={}),
            "c",
        )

    def test_return_value_transition_still_works_end_to_end(self):
        instance = SignatureModel()
        instance.to_return_value(pick_a=False)
        self.assertEqual(instance.state, "b")

    def test_get_state_transition_still_works_end_to_end(self):
        instance = SignatureModel(state="a")
        instance.to_get_state(nxt="d")
        self.assertEqual(instance.state, "d")
