"""
Fixture brand messages to test the agent against.

PLACEHOLDER — one example to show the shape. Add more as you go.

Aim for a spread that exercises each recommendation:
    - a clean, well-specified offer            -> ACCEPT
    - a vague offer missing pay or usage terms -> INVESTIGATE
    - gifting-only with heavy deliverables     -> DECLINE
"""

SAMPLES = [
    """Hi! We love your content and would like to send you our new serum.
    We'd need 1 TikTok and 2 IG stories within two weeks. Let us know!""",
]

# TODO: add an ACCEPT-shaped sample (clear fee, clear deliverables, clear deadline)
# TODO: add a red-flag sample (perpetual usage rights, exclusivity, unpaid)
