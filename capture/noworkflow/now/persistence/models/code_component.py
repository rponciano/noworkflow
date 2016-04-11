# Copyright (c) 2016 Universidade Federal Fluminense (UFF)
# Copyright (c) 2016 Polytechnic Institute of New York University.
# This file is part of noWorkflow.
# Please, consult the license terms in the LICENSE file.
"""Code Component Definition Model"""
from __future__ import (absolute_import, print_function,
                        division, unicode_literals)

from sqlalchemy import Column, Integer, Text
from sqlalchemy import PrimaryKeyConstraint, ForeignKeyConstraint
from sqlalchemy import CheckConstraint
from sqlalchemy.orm import remote, foreign

from ...utils.prolog import PrologDescription, PrologTrial, PrologAttribute
from ...utils.prolog import PrologRepr

from .base import AlchemyProxy, proxy_class, query_one_property
from .base import backref_one, one, many_viewonly_ref

from .code_block import CodeBlock


@proxy_class
class CodeComponent(AlchemyProxy):
    """Represent a code component definition
    It can be any component in the source code, including the script itself,
    class definitions, function definitions, arguments, variables, function
    calls, and others


    Doctest:
    >>> from noworkflow.now.persistence.models import Trial
    >>> from noworkflow.tests.helpers.models import erase_db, new_trial
    >>> from noworkflow.tests.helpers.models import blocks
    >>> from noworkflow.tests.helpers.models import component_params
    >>> from noworkflow.tests.helpers.models import evaluation_params
    >>> from noworkflow.tests.helpers.models import block_params
    >>> erase_db()
    >>> trial = Trial(new_trial(status="finished"))
    >>> from noworkflow.tests.helpers.models import components, evaluations
    >>> id_ = components.add(*component_params(
    ...     name="function", type_="function_def", mode="w",
    ...     first_char_line=1, first_char_column=0,
    ...     last_char_line=2, last_char_column= 8,
    ...     container_id=trial.main_id))
    >>> activation = list(trial.activations)[0]
    >>> eval_id = evaluations.add(*evaluation_params(id_, activation.id))
    >>> components.fast_store(trial.id)
    >>> evaluations.fast_store(trial.id)


    Load CodeComponent object by (trial_id, id):
    >>> code_component = CodeComponent((trial.id, id_))
    >>> code_component  # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    code_component(..., ..., 'function', 'function_def', 'w', 1, 0, 2, 8, ...).

    Load CodeComponent evaluations:
    >>> evaluations = list(code_component.evaluations)
    >>> evaluations  # doctest: +ELLIPSIS
    [evaluation(...).]

    Load CodeComponent container:
    >>> container = code_component.container
    >>> container.id == trial.main_id
    True

    Load CodeComponent trial:
    >>> component_trial = code_component.trial
    >>> component_trial.id == trial.id
    True

    If component is not a block, this_block is None:
    >>> code_component.this_block

    Otherwise, this_block is the corresponding block
    >>> _ = blocks.add(*block_params(id_))
    >>> blocks.fast_store(trial.id)
    >>> code_component.this_block  # doctest: +ELLIPSIS
    code_block(...).
    """

    __tablename__ = "code_component"
    __table_args__ = (
        PrimaryKeyConstraint("trial_id", "id"),
        ForeignKeyConstraint(["trial_id"], ["trial.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["trial_id", "container_id"],
                             ["code_block.trial_id", "code_block.id"],
                             ondelete="CASCADE", use_alter=True),
    )
    trial_id = Column(Integer, index=True)
    id = Column(Integer, index=True)                                             # pylint: disable=invalid-name
    name = Column(Text)
    type = Column(Text)  # ToDo: CheckConstraint?
    mode = Column(Text, CheckConstraint("mode IN ('r', 'w', 'd')"))
    first_char_line = Column(Integer)
    first_char_column = Column(Integer)
    last_char_line = Column(Integer)
    last_char_column = Column(Integer)
    container_id = Column(Integer, index=True)

    evaluations = many_viewonly_ref("code_component", "Evaluation")

    this_block = one(
        "CodeBlock", backref="this_component",
        primaryjoin=((foreign(id) == remote(CodeBlock.m.id)) &
                     (foreign(trial_id) == remote(CodeBlock.m.trial_id))))
    container = one(
        "CodeBlock", backref="components",
        viewonly=True,
        primaryjoin=((foreign(container_id) == remote(CodeBlock.m.id)) &
                     (foreign(trial_id) == remote(CodeBlock.m.trial_id))))

    trial = backref_one("trial")  # Trial.code_components

    prolog_description = PrologDescription("code_component", (
        PrologTrial("trial_id", link="trial.id"),
        PrologAttribute("id"),
        PrologRepr("name"),
        PrologRepr("type"),
        PrologRepr("mode"),
        PrologAttribute("first_char_line"),
        PrologAttribute("first_char_column"),
        PrologAttribute("last_char_line"),
        PrologAttribute("last_char_column"),
        PrologAttribute("container_id", link="code_component.id"),
    ), description=(
        "informs that in a given trial (*TrialId*),\n"
        "a code component (*Id*) with *Name*\n"
        "of *Type* is (r)ead/(w)rittem/(d)eleted (*Mode*).\n"
        "Its first char is at [*FirstCharLine*, *FirstCharColumn*],\n"
        "and it last char is at [*LastCharLine*, *LastCharColumn*].\n"
        "This component is part of a given code block (*ContainerId*)."
    ))

    @query_one_property
    def first_evaluation(self):
        """Return first evaluation of this component


        Doctest:
        >>> from noworkflow.now.persistence.models import Trial
        >>> from noworkflow.tests.helpers.models import erase_db, new_trial
        >>> from noworkflow.tests.helpers.models import components, evaluations
        >>> from noworkflow.tests.helpers.models import component_params
        >>> from noworkflow.tests.helpers.models import evaluation_params
        >>> erase_db()
        >>> trial = Trial(new_trial(status="finished"))
        >>> id_ = components.add(*component_params())
        >>> activation = list(trial.activations)[0]
        >>> eval_id1 = evaluations.add(*evaluation_params(
        ...     id_, activation.id, minute=40))
        >>> eval_id2 = evaluations.add(*evaluation_params(
        ...     id_, activation.id, minute=41))
        >>> components.fast_store(trial.id)
        >>> evaluations.fast_store(trial.id)
        >>> code_component = CodeComponent((trial.id, id_))

        Return first evaluation:
        >>> evaluation = code_component.first_evaluation
        >>> evaluation  # doctest: +ELLIPSIS
        evaluation(...).
        >>> evaluation.id == eval_id1
        True
        """
        from .evaluation import Evaluation
        return self.evaluations.order_by(Evaluation.m.moment).first()
