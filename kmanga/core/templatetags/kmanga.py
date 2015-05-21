from django import template

register = template.Library()


@register.filter(name='is_subscribed')
def is_subscribed(value, arg):
    return value.is_subscribed(arg)


@register.filter(name='subscription')
def subscription(value, arg):
    return value.subscription(arg)


@register.filter(name='subscription')
def subscription_pk(value, arg):
    return subscription(value, arg)[0].pk


@register.filter(name='is_sent')
def is_sent(value, arg):
    return value.is_sent(arg)


@register.filter(name='history')
def history(value, arg):
    return value.history(arg)
