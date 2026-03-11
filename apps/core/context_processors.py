"""JDS Context Processors"""


def subscription_context(request):
    """Fügt Abo-Infos zu allen Templates hinzu"""
    if request.user.is_authenticated:
        subscription = request.user.get_subscription()
        return {
            'subscription': subscription,
            'plan': subscription.plan,
            'remaining_messages': subscription.get_remaining_messages(),
        }
    return {'plan': 'anonymous'}
