---
title: Privacy
description: What this site stores about a visit, what it does not, and who else sees one.
---

There are no accounts here, no forms, no comments and no newsletter, so there is
nothing this site asks you for. What follows is what happens anyway.

## Nothing is kept in your browser

No cookies. No localStorage, no sessionStorage, no storage of any other kind.
There is no consent banner on this site because nothing here is written to your
machine to ask you about.

## Page views are counted

This site counts page views with [GoatCounter](https://www.goatcounter.com/).
Every page fetches a one-pixel image from their server. The path of the page is
in the address of that image and is what gets counted; the request also carries,
as any request to any server does, your IP address, the User-Agent your browser
sends, this site's name as the referring page, and the handful of hints a
browser volunteers about itself — which come to its name, its major version and
your operating system.

Of those, nothing is kept as it arrives. The address is used to guess a country
and then discarded; the User-Agent is reduced to the name of a browser and the
name of an operating system. No cookie is set and nothing is written to your
browser. GoatCounter does hold your address and User-Agent together in memory
for up to eight hours, so that several pages read in one sitting count as one
visit rather than several; what it stores in their place is a random string, and
nothing follows you from here to anywhere else. Their own account of all this is
at [GoatCounter's privacy policy](https://www.goatcounter.com/help/privacy).

Counting with an image rather than with their script is why these pages still
run no JavaScript. It costs them the information only a script could read —
GoatCounter records no referring page and no screen size from a pixel — and
that suits me.

Blocking requests to `goatcounter.com` stops it. Nothing else on the page
changes.

## The host sees every request

The pages are served by GitHub Pages, so fetching one tells GitHub your IP
address and the User-Agent your browser sends — the way asking any server for a
file tells that server who asked. What GitHub does with that is theirs to
describe, in the [GitHub Privacy
Statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement).

## Search runs on your machine

The search page is the only page here that runs JavaScript. It uses
[Pagefind](https://pagefind.app/), which publishes the index as ordinary files
alongside the pages. Your query is matched in your browser and is never sent
anywhere. The host still sees which parts of that index your browser asks for,
which narrows what you might have searched for without revealing it.

## Reaching me

Anything about this page, or about the site, goes through the advisory form
named in [`/.well-known/security.txt`](/.well-known/security.txt).
