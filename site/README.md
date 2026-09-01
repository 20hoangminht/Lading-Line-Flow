# The public site

One static page, no build step, no framework, no external requests. Deployed to Cloudflare Pages on
the free tier.

## Before it goes live — three placeholders to replace

| Placeholder | Where | Replace with |
|---|---|---|
| `REPLACE_WITH_FORM_ENDPOINT` | the `<form action="…">` | Your form endpoint. See below. |
| `REPLACE@ladingline.com` | footer | The real address |
| `REPLACE` (phone) | footer | The real number |

## The form

The page is a fake-door test: the form is the measurement. Two options, both free to start.

**Simplest — a form service.** Sign up for Tally, Formspree or Basin. Each gives you a URL. Paste it
into `action=`. Submissions land in your inbox and a dashboard. Free tiers cover 50–100 a month,
which is more than this list will produce.

**Better later — a Cloudflare Worker** writing to a KV store or straight to email. No third party in
the path, no monthly fee, and it keeps prospect data out of another vendor's system. Worth doing once
volume justifies it.

## Deploying

1. Log in to Cloudflare. Add `ladingline.com` as a site if it is not there — Cloudflare will give you
   two nameservers to set at your registrar. That change takes a few hours to propagate.
2. **Workers &amp; Pages → Create → Pages → Connect to Git.** Choose this repository.
3. Build settings: **framework preset `None`**, **build command blank**, **output directory `site`**.
4. Deploy. You get a `*.pages.dev` URL immediately.
5. **Custom domains → Set up a custom domain →** `ladingline.com` and `www.ladingline.com`.
   Cloudflare adds the DNS records and issues the certificate itself.

Every push to `main` redeploys. Pull request branches get their own preview URL, so a change can be
looked at before it goes live.

## What this page is and is not for

It will not bring you traffic this year. A new domain takes three to six months to rank for anything
competitive, and there is no shortcut. Its jobs are narrower and both matter now:

1. **Credibility.** Every prospect who gets a cold email looks you up. A page with published pricing
   and a plain explanation of where their data lives answers the two questions they were going to ask
   on the call.
2. **The fake door.** The calculator collects the two numbers that qualify a deal — documents a month
   and minutes a document — from anyone who lands, whether or not they ever reply to an email.

## Claims discipline

No case studies, no client names, no testimonials, no logos — there are none. No accuracy percentage
that has not been measured on that client's documents. No ISF references: that is a United States
requirement and using it in Australian material marks you as someone who does not know the trade.
Every number on the page is either a published list price, the visitor's own arithmetic, or a modelled
example that says so.
