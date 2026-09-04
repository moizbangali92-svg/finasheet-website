#!/usr/bin/env python3
"""Generate our-team.html from team/employees.json.

The page lives at the site root, not under /team/, for two reasons: the cloned
site header uses relative hrefs (href="vat-filing-uae"), which from a
subdirectory would resolve to /team/vat-filing-uae and break every nav link;
and team/ already holds the individual cards, so /team would be ambiguous.

Unlike the cards, this page IS indexable. The cards themselves are
noindex,follow, so they contribute nothing to Google's understanding of who
works here - this page is what carries the Person entities.

Everything comes from employees.json. Nothing about a person is invented: a
missing field is omitted rather than filled in. Add a "bio" to an entry and it
appears; leave it out and it does not.

Usage:  python scripts/build-team-page.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://finasheet.com"
DATA = os.path.join(ROOT, "team", "employees.json")
SHELL = os.path.join(ROOT, "vat-filing-uae.html")   # header/footer donor
OUT = os.path.join(ROOT, "our-team.html")
URL = f"{SITE}/our-team"

TITLE = "Our Team &mdash; The People Behind Finasheet"
DESC = ("Meet the Finasheet team. Business development and client support for UAE "
        "accounting, VAT and corporate tax, with a digital contact card for each "
        "person.")

ICON_CARD = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
             'stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" '
             'height="16" rx="2"/><circle cx="8" cy="10" r="2"/><path d="M14 9h4M14 13h4M6 15h6"/>'
             '</svg>')


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def initials(name):
    parts = [p for p in re.split(r"\s+", name.strip()) if p]
    if not parts:
        return "?"
    return (parts[0][0] + parts[-1][0]).upper() if len(parts) > 1 else parts[0][:2].upper()


def person_card(e):
    name, slug = e["name"].strip(), e["slug"]
    title = (e.get("title") or "").strip()
    photo = e.get("photo")

    if photo and os.path.exists(os.path.join(ROOT, photo)):
        avatar = (f'<img class="tm-photo" src="/{esc(photo)}" alt="{esc(name)}" '
                  f'width="400" height="400" loading="lazy" decoding="async">')
    else:
        avatar = f'<div class="tm-photo tm-fallback" aria-hidden="true">{esc(initials(name))}</div>'

    bits = [avatar, f"<h3>{esc(name)}</h3>"]
    if title:
        bits.append(f'<p class="tm-role">{esc(title)}</p>')
    if e.get("location"):
        bits.append(f'<p class="tm-loc">{esc(e["location"])}</p>')
    if e.get("bio"):
        bits.append(f'<p class="tm-bio">{esc(e["bio"])}</p>')
    bits.append(f'<a class="btn btn-ghost" href="/team/{esc(slug)}">'
                f'{ICON_CARD}<span>Digital card</span></a>')
    return f'<div class="tm reveal">{"".join(bits)}</div>'


def person_ld(e):
    node = {
        "@type": "Person",
        "@id": f"{SITE}/team/{e['slug']}#person",
        "name": e["name"].strip(),
        "url": f"{SITE}/team/{e['slug']}",
        "worksFor": {"@id": f"{SITE}/#organization"},
    }
    if e.get("title"):
        node["jobTitle"] = e["title"].strip()
    if e.get("email"):
        node["email"] = e["email"]
    if e.get("phone"):
        node["telephone"] = e["phone"]
    if e.get("photo"):
        node["image"] = f"{SITE}/{e['photo']}"
    if e.get("location"):
        node["workLocation"] = {"@type": "Place", "name": e["location"]}
    return node


def main():
    with open(DATA, encoding="utf-8") as f:
        people = json.load(f).get("employees", [])
    people = [e for e in people if e.get("slug") and e.get("name", "").strip()]
    if not people:
        print("no employees in team/employees.json")
        return 1

    # keep the page in a deliberate order rather than whatever JSON order is
    RANK = ["founder", "director", "manager", "executive"]

    def rank(e):
        t = (e.get("title") or "").lower()
        return next((i for i, w in enumerate(RANK) if w in t), len(RANK))

    people.sort(key=lambda e: (rank(e), e["name"]))

    shell = open(SHELL, encoding="utf-8", newline="").read().replace("\r\n", "\n")
    header = re.search(r"<header class=\"site\".*?</header>", shell, re.S).group(0)
    footer = re.search(r"<footer class=\"site\".*?</footer>", shell, re.S).group(0)
    tail = re.search(r"</footer>(.*?)</body>", shell, re.S).group(1)

    # .mobile-nav is a SIBLING after </header>; cloning only the header leaves
    # the burger button wired to an element that does not exist
    start = shell.index('<div class="mobile-nav"')
    i, depth = start, 0
    while i < len(shell):
        if shell.startswith("<div", i):
            depth += 1
        elif shell.startswith("</div>", i):
            depth -= 1
            if depth == 0:
                i += len("</div>")
                break
        i += 1
    mnav = shell[start:i]
    assert 'id="mnav"' in mnav and mnav.count("<div") == mnav.count("</div>")

    # both navs inherit the donor's in-page anchors; this page has its own
    for block_name in ("header", "mnav"):
        pass
    # the donor already carries a /pricing link after these, so only the
    # in-page anchors are swapped - adding one here would duplicate it
    nav_fix = [
        ('<a href="#why">Why Finasheet</a>\n      <a href="#process">Process</a>\n'
         '      <a href="#packages">Packages</a>\n      <a href="#faq">FAQs</a>',
         '<a href="#team">Team</a>'),
    ]
    for old, new in nav_fix:
        assert header.count(old) == 1, f"header nav tail not found ({header.count(old)})"
        header = header.replace(old, new, 1)

    mnav = mnav.replace('<a class="m-link" href="#why">Why Finasheet</a>',
                        '<a class="m-link" href="#team">Team</a>')
    for dead in ['<a class="m-link" href="#process">Process</a>',
                 '<a class="m-link" href="#packages">Packages</a>',
                 '<a class="m-link" href="#faq">FAQs</a>']:
        mnav = mnav.replace(dead, "")
    mnav = mnav.replace('<a class="m-link" href="/pricing">Pricing</a>',
                        '<a class="m-link" href="/pricing">Pricing</a>')

    # this page has no lead form of its own - the sticky CTA bar and the
    # floating action button in the tail point at it too, not just the navs
    header = header.replace('href="#lead-form"', 'href="/services#lead-form"')
    mnav = mnav.replace('href="#lead-form"', 'href="/services#lead-form"')
    footer = footer.replace('href="#lead-form"', 'href="/services#lead-form"')
    tail = tail.replace('href="#lead-form"', 'href="/services#lead-form"')

    for frag, label in ((header, "header"), (mnav, "mobile nav"),
                        (footer, "footer"), (tail, "tail")):
        leftover = [a for a in re.findall(r'href="(#[^"]*)"', frag) if a not in ("#team",)]
        assert not leftover, f"{label} still points at {leftover}"

    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": URL + "#webpage",
                "url": URL,
                "name": "Our Team",
                "description": re.sub(r"&[a-z]+;", "", DESC),
                "inLanguage": "en-AE",
                "isPartOf": {"@id": f"{SITE}/#website"},
                "publisher": {"@id": f"{SITE}/#organization"},
                "breadcrumb": {"@id": URL + "#breadcrumb"},
                "mainEntity": {"@id": URL + "#roster"},
            },
            {
                "@type": "BreadcrumbList",
                "@id": URL + "#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                    {"@type": "ListItem", "position": 2, "name": "Our Team", "item": URL},
                ],
            },
            {
                "@type": "ItemList",
                "@id": URL + "#roster",
                "itemListOrder": "https://schema.org/ItemListUnordered",
                "numberOfItems": len(people),
                "itemListElement": [
                    {"@type": "ListItem", "position": n,
                     "item": {"@id": f"{SITE}/team/{e['slug']}#person"}}
                    for n, e in enumerate(people, 1)
                ],
            },
        ] + [person_ld(e) for e in people],
    }

    cards = "".join(person_card(e) for e in people)

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{TITLE} | Finasheet</title>
<meta name="description" content="{DESC}">
<link rel="canonical" href="{URL}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Finasheet">
<meta property="og:locale" content="en_AE">
<meta property="og:title" content="{TITLE} | Finasheet">
<meta property="og:description" content="{DESC}">
<meta property="og:url" content="{URL}">
<meta property="og:image" content="{SITE}/assets/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Finasheet - accounting software built for UAE businesses">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{TITLE} | Finasheet">
<meta name="twitter:description" content="{DESC}">
<meta name="twitter:image" content="{SITE}/assets/og-image.png">
<script type="application/ld+json">
{json.dumps(ld, indent=2, ensure_ascii=False)}
</script>
<link rel="stylesheet" href="finasheet-services.css">
<style>
/* Page-specific: the portrait and its caption. The grid, buttons, section
   heads and reveal animation are all existing components. */
.tm-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:22px;margin-top:42px}}
.tm{{background:#fff;border:1px solid var(--line);border-radius:var(--radius-lg);
  padding:26px 22px;box-shadow:var(--shadow-sm);text-align:center;
  display:flex;flex-direction:column;align-items:center}}
.tm-photo{{width:132px;height:132px;border-radius:50%;object-fit:cover;
  background:var(--bg-soft);margin-bottom:16px}}
.tm-fallback{{display:grid;place-items:center;font-family:var(--display);
  font-size:40px;font-weight:700;color:#9fb0c4}}
.tm h3{{font-size:1.12rem;margin-bottom:4px}}
.tm-role{{font-size:.9rem;font-weight:600;color:var(--blue);margin-bottom:2px}}
.tm-loc{{font-size:.82rem;color:var(--muted)}}
.tm-bio{{font-size:.88rem;color:var(--muted);margin-top:12px;line-height:1.55}}
.tm .btn{{margin-top:auto;margin-top:18px;gap:8px}}
.tm .btn svg{{width:16px;height:16px}}
@media(max-width:980px){{.tm-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}
@media(max-width:640px){{.tm-grid{{grid-template-columns:minmax(0,1fr);gap:16px}}
  .tm-photo{{width:112px;height:112px}}}}
</style>
</head>
<body>
{header}

{mnav}

<section class="hero">
  <div class="wrap">
    <span class="eyebrow reveal">Our Team</span>
    <h1 class="reveal">The people behind <span class="hl">Finasheet</span>.</h1>
    <p class="sub reveal">You deal with a named person, not a ticket queue. Each card below
      opens their direct contact details, and saves to your phone in one tap.</p>
  </div>
</section>

<section id="team" class="soft">
  <div class="wrap">
    <div class="section-head center reveal">
      <span class="eyebrow" style="justify-content:center">Who you work with</span>
      <h2>Business development and client support.</h2>
      <p class="lead">Based in the United Arab Emirates, working with mainland and free zone
        businesses on accounting, VAT and corporate tax.</p>
    </div>
    <div class="tm-grid">{cards}</div>
  </div>
</section>

{footer}
{tail}</body>
</html>
"""

    with open(OUT, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(page)

    written = open(OUT, encoding="utf-8", newline="").read()
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', written, re.S)
    for b in blocks:
        json.loads(b)
    dead = [a for a in set(re.findall(r'href="(#[^"]+)"', written))
            if not re.search(rf'id="{re.escape(a[1:])}"', written)]
    assert not dead, f"dead in-page anchors: {dead}"
    assert 'id="mnav"' in written, "mobile nav missing"

    print(f"  our-team.html  {os.path.getsize(OUT) // 1024}KB")
    print(f"  {len(people)} people, {len(blocks)} JSON-LD block parsed clean, no dead anchors")
    for e in people:
        print(f"    {e['name']:20s} {e.get('title','')[:40]:42s} -> /team/{e['slug']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
