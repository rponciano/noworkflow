# Copyright (c) 2016 Universidade Federal Fluminense (UFF)
# Copyright (c) 2016 Polytechnic Institute of New York University.
# This file is part of noWorkflow.
# Please, consult the license terms in the LICENSE file.
"""Slicing Dependency Model"""
from __future__ import (absolute_import, print_function,
                        division, unicode_literals)

from sqlalchemy import Column, Integer, Text
from sqlalchemy import PrimaryKeyConstraint, ForeignKeyConstraint

from ..persistence import persistence
from .model import Model


class SlicingDependency(Model, persistence.base):
    """Slicing Dependency Table
    Store slicing dependencies between variables from execution provenance
    """
    __tablename__ = "slicing_dependency"
    __table_args__ = (
        PrimaryKeyConstraint("trial_id", "id"),
        ForeignKeyConstraint(["trial_id"],
                             ["trial.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["trial_id", "dependent_activation_id"],
                             ["function_activation.trial_id",
                              "function_activation.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["trial_id", "supplier_activation_id"],
                             ["function_activation.trial_id",
                              "function_activation.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["trial_id",
                              "dependent_activation_id",
                              "dependent"],
                             ["slicing_variable.trial_id",
                              "slicing_variable.activation_id",
                              "slicing_variable.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["trial_id",
                              "supplier_activation_id",
                              "supplier"],
                             ["slicing_variable.trial_id",
                              "slicing_variable.activation_id",
                              "slicing_variable.id"], ondelete="CASCADE"),
    )
    trial_id = Column(Integer, index=True)
    id = Column(Integer, index=True)
    dependent_activation_id = Column(Integer, index=True)
    dependent_id = Column("dependent", Integer, index=True)
    supplier_activation_id = Column(Integer, index=True)
    supplier_id = Column("supplier", Integer, index=True)

    # trial: Trial backref
    # dependent_activation: Activation.slicing_dependents backref
    # supplier_activation: Activation.slicing_suppliers backref
    # dependent: SlicingVariable.suppliers_dependencies backref
    # supplier: SlicingVariable.dependents_dependencies backref

    DEFAULT = {}
    REPLACE = {}

    @classmethod
    def to_prolog_fact(cls):
        return textwrap.dedent("""
            %
            % FACT: dependency(trial_id, id, dependent_activation_id, dependent_id, supplier_activation_id, supplier_id).
            %
            """)

    @classmethod
    def to_prolog_dynamic(cls):
        return ":- dynamic(dependency/6)."

    @classmethod
    def to_prolog_retract(cls, trial_id):
        return "retract(usage({}, _, _, _, _, _))".format(trial_id)

    def to_prolog(self):
        return (
            "dependency("
            "{d.trial_id}, {d.id}, "
            "{d.dependent_activation_id}, {d.dependent_id}, "
            "{d.supplier_activation_id}, {d.supplier_id})."
        ).format(d=self)

    def __str__(self):
        return "{0.dependent} <- {0.supplier}".format(self)

    def __repr__(self):
        return (
            "SlicingDependency({0.trial_id}, {0.id}, "
            "{0.dependent}, {0.supplier})"
        ).format(self)
