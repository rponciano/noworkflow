# Copyright (c) 2016 Universidade Federal Fluminense (UFF)
# Copyright (c) 2016 Polytechnic Institute of New York University.
# This file is part of noWorkflow.
# Please, consult the license terms in the LICENSE file.
"""Object Model"""
from __future__ import (absolute_import, print_function,
                        division, unicode_literals)

from sqlalchemy import Column, Integer, Text
from sqlalchemy import ForeignKeyConstraint, CheckConstraint

from ..persistence import persistence
from .model import Model


class Object(Model, persistence.base):
    """Object Table
    Store function calls, global variables and arguments
    from definition provenance
    """
    __tablename__ = "object"
    __table_args__ = (
        ForeignKeyConstraint(["function_def_id"], ["function_def.id"],
                             ondelete="CASCADE"),
        {"sqlite_autoincrement": True},
    )
    function_def_id = Column(Integer, index=True)
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    type = Column(
        Text,
        CheckConstraint("type IN ('GLOBAL', 'ARGUMENT', 'FUNCTION_CALL')"))

    # function_def: FunctionDef.objects backref

    DEFAULT = {}
    REPLACE = {}

    @classmethod
    def to_prolog_fact(cls):
        """Return prolog comment"""
        return textwrap.dedent("""
            %
            % FACT: object(trial_id, function_def_id, id, name, type).
            %
            """)

    @classmethod
    def to_prolog_dynamic(cls):
        """Return prolog dynamic clause"""
        return ":- dynamic(object/5)."

    @classmethod
    def to_prolog_retract(cls, trial_id):
        """Return prolog retract for trial"""
        return "retract(object({}, _, _, _, _))".format(trial_id)

    def to_prolog(self):
        """Convert to prolog fact"""
        return (
            "object("
            "{o.trial_id}, {o.function_def_id}, {o.id}, {o.name!r}, "
            "{o.type})."
        ).format(o=self)

    def __repr__(self):
        return (
            "Object({0.trial_id}, {0.function_def_id}, "
            "{0.id}, {0.name}, {0.type})"
        ).format(self)
