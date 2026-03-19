"""
Django template tags for PBAC.

Usage::

    {% load pbac_tags %}

    {% can "documents:read" resource_type="document" resource_id=doc.pk %}
        <a href="{{ doc.get_absolute_url }}">Read</a>
    {% endcan %}

    {% cannot "documents:delete" resource_type="document" resource_id=doc.pk %}
        <span class="disabled">Delete (no permission)</span>
    {% endcannot %}

    {# Store result in a variable #}
    {% can "documents:edit" resource_type="document" resource_id=doc.pk as can_edit %}
    {% if can_edit %}...{% endif %}
"""
from __future__ import annotations

import logging
from typing import Any

from django import template
from django.template.context import RequestContext


logger = logging.getLogger(__name__)
register = template.Library()


class PBACCheckNode(template.Node):
    """Template node for {% can %} / {% cannot %} tags."""

    def __init__(
        self,
        action: str,
        resource_type_expr: template.FilterExpression,
        resource_id_expr: template.FilterExpression | None,
        nodelist_true: template.NodeList,
        nodelist_false: template.NodeList,
        invert: bool = False,
        as_var: str | None = None,
    ) -> None:
        self.action = action
        self.resource_type_expr = resource_type_expr
        self.resource_id_expr = resource_id_expr
        self.nodelist_true = nodelist_true
        self.nodelist_false = nodelist_false
        self.invert = invert
        self.as_var = as_var

    def render(self, context: template.Context) -> str:
        resource_type = self.resource_type_expr.resolve(context)
        resource_id = (
            str(self.resource_id_expr.resolve(context))
            if self.resource_id_expr
            else None
        )

        is_permitted = self._evaluate(context, resource_type, resource_id)

        if self.as_var:
            context[self.as_var] = is_permitted
            return ""

        if self.invert:
            is_permitted = not is_permitted

        if is_permitted:
            return self.nodelist_true.render(context)
        elif self.nodelist_false:
            return self.nodelist_false.render(context)
        return ""

    def _evaluate(
        self, context: template.Context, resource_type: str, resource_id: str | None
    ) -> bool:
        try:
            from django_pbac.engine import pbac_engine
            from django_pbac.core.models import Resource, PolicyRequest, Context as PBACContext

            request = context.get("request")

            subject = (
                getattr(request, "pbac_subject", None)
                if request
                else None
            )
            pbac_context = (
                getattr(request, "pbac_context", None)
                if request
                else None
            ) or PBACContext()

            if subject is None:
                if request:
                    subject = pbac_engine.build_subject(request)
                else:
                    from django_pbac.core.models import Subject
                    from django_pbac.core.types import SubjectType

                    subject = Subject(id="anonymous", type=SubjectType.ANONYMOUS)

            resource = Resource(type=str(resource_type), id=resource_id)
            policy_request = PolicyRequest(
                subject=subject,
                action=self.action,
                resource=resource,
                context=pbac_context,
            )

            decision = pbac_engine.evaluate(policy_request)
            return decision.is_permit

        except Exception as exc:  # noqa: BLE001
            logger.warning("PBAC template tag evaluation error: %s", exc)
            return False


def _parse_pbac_tag(
    parser: template.base.Parser,
    token: template.base.Token,
    invert: bool = False,
    end_tag: str = "endcan",
) -> PBACCheckNode:
    bits = token.split_contents()
    tag_name = bits[0]

    if len(bits) < 2:
        raise template.TemplateSyntaxError(
            f"{tag_name!r} requires at least one argument: the action string."
        )

    action = bits[1].strip("\"'")
    resource_type_expr = None
    resource_id_expr = None
    as_var = None

    i = 2
    while i < len(bits):
        bit = bits[i]
        if bit == "as" and i + 1 < len(bits):
            as_var = bits[i + 1]
            i += 2
        elif bit.startswith("resource_type="):
            resource_type_expr = parser.compile_filter(bit.split("=", 1)[1])
            i += 1
        elif bit.startswith("resource_id="):
            resource_id_expr = parser.compile_filter(bit.split("=", 1)[1])
            i += 1
        else:
            i += 1

    if resource_type_expr is None:
        raise template.TemplateSyntaxError(
            f"{tag_name!r} requires resource_type= keyword argument."
        )

    nodelist_true = parser.parse((f"else_{end_tag}", end_tag))
    token2 = parser.next_token()

    if token2.contents == f"else_{end_tag}":
        nodelist_false = parser.parse((end_tag,))
        parser.delete_first_token()
    else:
        nodelist_false = template.NodeList()

    return PBACCheckNode(
        action=action,
        resource_type_expr=resource_type_expr,
        resource_id_expr=resource_id_expr,
        nodelist_true=nodelist_true,
        nodelist_false=nodelist_false,
        invert=invert,
        as_var=as_var,
    )


@register.tag("can")
def do_can(parser: template.base.Parser, token: template.base.Token) -> PBACCheckNode:
    """
    Render block if the current user has PERMIT for the given action/resource.

    Usage::

        {% can "documents:read" resource_type="document" resource_id=doc.pk %}
            You can read this document.
        {% else_can %}
            You cannot read this document.
        {% endcan %}
    """
    return _parse_pbac_tag(parser, token, invert=False, end_tag="endcan")


@register.tag("cannot")
def do_cannot(
    parser: template.base.Parser, token: template.base.Token
) -> PBACCheckNode:
    """
    Render block if the current user does NOT have PERMIT.

    Usage::

        {% cannot "documents:delete" resource_type="document" resource_id=doc.pk %}
            Delete button hidden.
        {% endcannot %}
    """
    return _parse_pbac_tag(parser, token, invert=True, end_tag="endcannot")
