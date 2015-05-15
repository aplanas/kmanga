from django import template

register = template.Library()


@register.filter(name='is_subscribed')
def is_subscribed(value, arg):
    return value.is_subscribed(arg)
