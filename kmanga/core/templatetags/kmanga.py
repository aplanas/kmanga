from django import template

from core.models import Result

register = template.Library()


@register.filter(name='is_subscribed')
def is_subscribed(value, arg):
    return value.is_subscribed(arg)


@register.filter(name='subscription')
def subscription(value, arg):
    return value.subscription(arg)


@register.filter(name='subscription_pk')
def subscription_pk(value, arg):
    return subscription(value, arg)[0].pk


@register.filter(name='result')
def result(value, arg):
    return Result.objects.filter(subscription=value, issue=arg).first()
