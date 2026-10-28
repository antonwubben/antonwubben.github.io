#!/usr/bin/env python3
"""Bouwt de meertalige site van antonwubben.nl.

Bron: templates/*.html met {{sleutels}} en strings/<taal>.json met de teksten.
Uitvoer: Nederlands in de hoofdmap van docs/, de andere talen in docs/<taal>/ met dezelfde structuur.

Gebruik:  python3 docs/_src/build.py
"""

import json
import posixpath
import re
from pathlib import Path

SRC = Path(__file__).resolve().parent
OUT = SRC.parent  # docs/
SITE = "https://antonwubben.nl"

LANGS = ["nl", "en", "de", "es", "fr", "it", "pt"]
DEFAULT = "nl"  # staat in de hoofdmap, zonder taalmap

# Pagina -> pad binnen een taalmap.
PAGES = {
    "home": "index.html",
    "wie": "wie/index.html",
    "glutenscan": "glutenscan/index.html",
    "privacy": "glutenscan/privacy.html",
}

GLOBE = (
    '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/>'
    '<path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></svg>'
)

# Onthoudt de gekozen taal en stuurt bij een eerste bezoek één keer door naar de taal van de browser,
# net zoals de app de taal van het toestel overneemt. Daarna wint altijd de keuze in de taalkiezer.
SCRIPT = """<script>
(function () {
  // Bedankje tonen als het contactformulier zojuist is verstuurd (FormSubmit stuurt terug met ?sent=1).
  var sent = document.querySelector('.sent');
  if (sent && /[?&]sent=1/.test(location.search)) { sent.hidden = false; }
  var key = 'lang', sels = document.querySelectorAll('.lang-switch select'), i;
  function go(url, lang) { try { localStorage.setItem(key, lang); } catch (e) {} location.href = url; }
  for (i = 0; i < sels.length; i++) {
    sels[i].addEventListener('change', function () {
      var o = this.options[this.selectedIndex]; go(o.value, o.getAttribute('data-lang'));
    });
  }
  try {
    if (!sels.length || sessionStorage.getItem('langChecked')) return;
    sessionStorage.setItem('langChecked', '1');
    var current = document.documentElement.lang, wanted = localStorage.getItem(key);
    if (!wanted) { wanted = ((navigator.languages && navigator.languages[0]) || navigator.language || '').slice(0, 2).toLowerCase(); }
    if (wanted && wanted !== current) {
      var o = sels[0].querySelector('option[data-lang="' + wanted + '"]');
      if (o) location.replace(o.value);
    }
  } catch (e) {}
})();
</script>"""


def page_path(lang: str, page: str) -> str:
    path = PAGES[page]
    if lang == DEFAULT:
        return path

    directory, filename = posixpath.split(path)
    stem, extension = posixpath.splitext(filename)
    localized_filename = f"{stem}_{lang}{extension}"
    return posixpath.join(directory, localized_filename) if directory else localized_filename


def relative(from_path: str, to_path: str) -> str:
    """Relatieve link van het ene uitvoerbestand naar het andere (werkt ook lokaal vanaf schijf)."""
    return posixpath.relpath(to_path, posixpath.dirname(from_path) or ".")


def root_prefix(from_path: str) -> str:
    depth = from_path.count("/")
    return "../" * depth


def load_strings() -> dict[str, dict[str, str]]:
    return {lang: json.loads((SRC / "strings" / f"{lang}.json").read_text(encoding="utf-8")) for lang in LANGS}


def lang_switch(lang: str, page: str, strings: dict, floating: bool = False) -> str:
    here = page_path(lang, page)
    options = []
    for other in LANGS:
        selected = " selected" if other == lang else ""
        options.append(
            f'<option value="{relative(here, page_path(other, page))}" data-lang="{other}"{selected}>'
            f'{strings[other]["lang_name"]}</option>'
        )
    cls = "lang-switch floating" if floating else "lang-switch"
    # Zichtbaar staat alleen de taalcode (NL, EN, ...), als gewone tekst zodat hij uitlijnt met de menulinks;
    # in het menu zelf staan de voluit geschreven taalnamen. De echte keuzelijst ligt er onzichtbaar overheen.
    return (
        f'<label class="{cls}">{GLOBE}<span>{lang.upper()}</span>'
        f'<select aria-label="{strings[lang]["lang_label"]}">{"".join(options)}</select></label>'
    )


def alternates(page: str) -> str:
    lines = [f'<link rel="alternate" hreflang="{lang}" href="{SITE}/{page_path(lang, page)}">' for lang in LANGS]
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{SITE}/{page_path(DEFAULT, page)}">')
    return "\n".join(lines)


def nav(lang: str, page: str, strings: dict) -> str:
    here = page_path(lang, page)
    s = strings[lang]
    # Op smalle schermen verdwijnen de links achter een knop met twee streepjes (zoals bij Apple); de
    # onzichtbare checkbox houdt bij of het menu open is, zodat er geen script voor nodig is.
    return (
        '<nav class="nav">\n'
        '  <input type="checkbox" id="menu-toggle" class="menu-toggle">\n'
        f'  <a class="brand" href="{relative(here, page_path(lang, "home"))}">Anton Wubben</a>\n'
        '  <ul class="nav-links">\n'
        f'    <li><a href="{relative(here, page_path(lang, "wie"))}">{s["nav_wie"]}</a></li>\n'
        f'    <li><a href="{relative(here, page_path(lang, "glutenscan"))}">{s["nav_glutenscan"]}</a></li>\n'
        f"    <li>{lang_switch(lang, page, strings)}</li>\n"
        "  </ul>\n"
        '  <div class="nav-tools">\n'
        '    <label for="menu-toggle" class="menu-button" aria-label="Menu"><span></span><span></span></label>\n'
        "  </div>\n"
        "</nav>"
    )


def ext(url: str, text: str) -> str:
    return f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'


def render(lang: str, page: str, templates: dict, strings: dict) -> str:
    here = page_path(lang, page)
    s = dict(strings[lang])
    root = root_prefix(here)

    # Links in lopende tekst.
    s["wie_p4"] = s["wie_p4"].replace("{haskoning}", ext("https://www.haskoning.com", "Haskoning"))
    s["wie_p6"] = s["wie_p6"].replace(
        "{glutenscan}", f'<a href="{relative(here, page_path(lang, "glutenscan"))}">Glutenscan</a>'
    )
    s["pv_off_p"] = (
        s["pv_off_p"]
        .replace("{off}", ext("https://world.openfoodfacts.org", "Open Food Facts"))
        .replace("{off_privacy}", ext("https://world.openfoodfacts.org/privacy", s["pv_off_privacy_text"]))
    )
    s["pv_feedback_p"] = s["pv_feedback_p"].replace("{formsubmit}", ext("https://formsubmit.co", "FormSubmit"))
    s["pv_tips_p"] = s["pv_tips_p"].replace(
        "{apple_privacy}", ext("https://www.apple.com/legal/privacy/", s["pv_apple_privacy_text"])
    )

    s.update(
        lang=lang,
        root=root,
        alternates=alternates(page),
        nav=nav(lang, page, strings),
        lang_switch_floating=lang_switch(lang, page, strings, floating=True),
        script=SCRIPT,
        url_home=relative(here, page_path(lang, "home")),
        url_wie=relative(here, page_path(lang, "wie")),
        url_glutenscan=relative(here, page_path(lang, "glutenscan")),
        url_privacy=relative(here, page_path(lang, "privacy")),
        page_url=f"{SITE}/{here}",
    )

    html = templates[page]

    def sub(match: re.Match) -> str:
        key = match.group(1)
        if key not in s:
            raise KeyError(f"Onbekende sleutel {{{{{key}}}}} in template {page} ({lang})")
        return s[key]

    return re.sub(r"\{\{(\w+)\}\}", sub, html)


def main() -> None:
    strings = load_strings()
    templates = {page: (SRC / "templates" / f"{page}.html").read_text(encoding="utf-8") for page in PAGES}

    # Versienummer achter style.css, afgeleid van de inhoud: na elke wijziging halen browsers de nieuwe
    # stijl op in plaats van een oude kopie uit hun cache te gebruiken.
    import hashlib
    css_version = hashlib.sha1((OUT / "style.css").read_bytes()).hexdigest()[:8]
    templates = {page: html.replace("style.css\"", f"style.css?v={css_version}\"") for page, html in templates.items()}

    # Controleer dat elke taal dezelfde sleutels heeft als het Nederlands.
    base = set(strings[DEFAULT])
    for lang in LANGS:
        missing = base - set(strings[lang])
        extra = set(strings[lang]) - base
        if missing or extra:
            raise SystemExit(f"{lang}.json: ontbreekt {sorted(missing)}, overbodig {sorted(extra)}")

    # Verwijder oude taalmap-uitvoer. Vertalingen staan voortaan naast de Nederlandse bestanden
    # met een suffix, bijvoorbeeld glutenscan/index_en.html.
    import shutil
    for lang in LANGS:
        if lang != DEFAULT:
            shutil.rmtree(OUT / lang, ignore_errors=True)

    written = []
    for lang in LANGS:
        for page in PAGES:
            target = OUT / page_path(lang, page)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(render(lang, page, templates, strings), encoding="utf-8")
            written.append(target.relative_to(OUT).as_posix())

    print(f"{len(written)} pagina's geschreven:")
    for path in written:
        print("  " + path)


if __name__ == "__main__":
    main()
