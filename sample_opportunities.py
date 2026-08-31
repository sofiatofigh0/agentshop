"""
Fixture brand messages to test the agent against.

Three examples, one per recommendation path:
    STRONG_PAID_OFFER   clear fee, clear deliverables, clear deadline
    AMBIGUOUS_GIFTING   gifting only, most of the important details missing
    CONCERNING_RIGHTS   paid, but the usage rights and exclusivity are the problem
"""

STRONG_PAID_OFFER = """
Subject: Lumen Skincare x you - paid partnership for our June serum launch

Hi Maya,

I'm Priya Raghavan, influencer marketing lead at Lumen Skincare. We've been
following your skin barrier content for a while and would love to bring you into
the launch of our Ceramide Repair Serum.

Here's what we have in mind:

- 1 Instagram Reel (45-60 sec) + 2 Instagram Stories with a swipe-up
- Flat fee: $3,500 USD, paid net 30 after the post goes live
- Usage: organic only, on your handles. We'd like the option to repost the Reel
  to our own grid for 30 days, credited to you.
- Live date: Thursday, June 12. Draft for our review by June 5.
- Product ships within 3 business days of a signed agreement.

We'll send a standard agreement and a PO once you confirm. Happy to talk through
the creative brief on a quick call if that's easier.

Best,
Priya Raghavan
Lumen Skincare
priya@lumenskincare.com
"""

AMBIGUOUS_GIFTING = """
hey!! love your page :)

we're a small wellness brand and we're building out our creator community for
the rest of the year. we'd love to send you a PR box with a few of our
bestsellers!

all we ask is that you post about it! we're looking for authentic content, so
whatever feels natural to you. this is a great opportunity for exposure - a lot
of our creators have really grown from working with us, and if this goes well
there's definitely potential for paid stuff down the line.

let me know your address and we can get this out to you asap!

xx
Team Wellthy
"""

CONCERNING_RIGHTS = """
Subject: Collaboration Opportunity - Q3 Campaign

Hello,

We're reaching out on behalf of our client to invite you to participate in their
Q3 campaign. Please find the terms below.

Deliverables: 2 TikTok videos, 3 Instagram Reels, 5 Instagram Stories, and 1
YouTube integration (60+ seconds). Revisions as needed until approved.

Compensation: $800 total.

Usage: Client receives a perpetual, worldwide, irrevocable, royalty-free license
to use, edit, and sublicense all content across all media now known or hereafter
devised, including paid social, connected TV, and out-of-home, with no additional
compensation. Client may also run the content through your handles via
whitelisting for the duration of the campaign and thereafter.

Exclusivity: Creator agrees not to promote, mention, or appear alongside any
competing product in the beauty, wellness, supplement, or personal care
categories for 12 months from the first post date.

We'd need everything delivered by the end of next week. Please confirm ASAP as we
have limited slots remaining and are speaking with several other creators.

Regards,
Campaign Team
"""

SAMPLES = [STRONG_PAID_OFFER, AMBIGUOUS_GIFTING, CONCERNING_RIGHTS]
