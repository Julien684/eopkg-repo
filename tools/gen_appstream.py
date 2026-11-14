#!/usr/bin/env python3
"""
gen_appstream.py — Génère les métadonnées AppStream des paquets du dépôt.

Sorties (répertoire ./appstream) :
  metainfo/<id>.metainfo.xml      fiche AppStream de chaque application
                                  (vocation : être embarquée DANS le paquet de
                                  l'appli, sous usr/share/metainfo/)
  linuxon-main.xml(.gz)           catalogue AppStream du dépôt : c'est lui qui
                                  rend les applis visibles dans Discover /
                                  GNOME Software AVANT leur installation
  icons/<size>/<pkg>_<icone>.png  icônes « cached » référencées par le catalogue

Pourquoi un catalogue ? Le backend PackageKit « eopkg » de Solus ne publie
aucune donnée AppStream par dépôt : Discover et GNOME Software ne lisent que
les catalogues système de /usr/share/swcatalog/xml/*.xml.gz (fournis par le
paquet appstream-catalog de Solus, qui ne couvre que les dépôts officiels) et
les metainfo des paquets installés. Un dépôt tiers doit donc fournir son
propre catalogue ; le lien composant -> paquet se fait par <pkgname>.

Sources de vérité : le .desktop embarqué dans le paquet (nom, résumé,
catégories, icône) + eopkg-index.xml (version, licence, page d'accueil).

Usage: python3 tools/gen_appstream.py
"""
import gzip
import io
import os
import re
import tarfile
import zipfile
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "appstream"
INDEX = ROOT / "eopkg-index.xml"

ORIGIN = "linuxon-main"
DEVELOPER_ID = "fr.julien68"
DEVELOPER_NAME = "Julien"
# Hôte cible : "gitea" (défaut) ou "github" — le miroir GitHub porte ses propres
# liens, comme les README des deux copies.
HOST = os.environ.get("AS_HOST", "gitea").lower()
GITEA = "https://depoa.julien68.fr/Linuxon"
GITHUB = "https://github.com/Julien684"


def homepage(pkg):
    return f"{GITHUB}/{pkg}" if HOST == "github" else f"{GITEA}/{pkg}"


def raw_url(pkg, path):
    """URL brute d'un fichier du dépôt source du paquet, selon l'hôte."""
    if HOST == "github":
        return f"https://raw.githubusercontent.com/Julien684/{pkg}/main/{path}"
    return f"{GITEA}/{pkg}/raw/branch/main/{path}"

# Catégories AppStream autorisées (vocabulaire freedesktop). Les catégories du
# .desktop sont filtrées là-dedans ; Filesystem (desktop) -> System.
AS_CATEGORIES = {
    "AudioVideo", "Audio", "Video", "Development", "Education", "Game",
    "Graphics", "Network", "Office", "Science", "Settings", "System", "Utility",
}
DESKTOP_CATEGORY_MAP = {"Filesystem": "System", "FileTools": "Utility"}

# Ce que le dépôt ne peut pas deviner : identifiant AppStream définitif,
# type de composant, mots-clés, capture d'écran, icône de repli.
APPS = [
    dict(pkg="amv-converter", id="fr.julien68.AmvConverter",
         keywords=["amv", "video", "convert", "ffmpeg", "player"],
         shot=("amv-converter", "assets/screenshot.png")),
    dict(pkg="btrfsmgr", id="fr.julien68.BtrfsManager",
         keywords=["btrfs", "snapshot", "subvolume", "restore", "tui"],
         stock="chronometer"),
    dict(pkg="btrfsmgr-gui", id="fr.julien68.BtrfsManagerGui",
         keywords=["btrfs", "snapshot", "subvolume", "restore", "gui"],
         stock="chronometer",
         shot=("btrfsmgr-gui", "gui-screenshot.png")),
    dict(pkg="ollama-manager-qt", id="fr.julien68.OllamaModelManager",
         keywords=["ollama", "model", "llm", "ai"],
         shot=("ollama-manager-qt", "screenshot.png")),
    dict(pkg="solus-external-kernel-manager",
         id="fr.julien68.SolusExternalKernelManager",
         keywords=["kernel", "cachyos", "zen", "liquorix", "boot"],
         shot=("solus-external-kernel-manager", "screenshot.png")),
    # Pas de .desktop : application console, métadonnées fournies à la main.
    dict(pkg="deb-to-eopkg", id="fr.julien68.DebToEopkg",
         kind="console-application",
         name_en="deb-to-eopkg", name_fr="deb-to-eopkg",
         summary_en="Convert Debian .deb packages into Solus .eopkg packages",
         summary_fr="Convertir des paquets Debian .deb en paquets Solus .eopkg",
         cats=["Development", "Utility"],
         keywords=["deb", "eopkg", "package", "convert", "solus"]),
]

ICON_SIZES = (48, 64, 128)
CATALOG_ICON_SIZE = 128


# ─────────────────────────────────────────────────────────────────────────────
# Lecture du dépôt
# ─────────────────────────────────────────────────────────────────────────────
def read_index():
    text = INDEX.read_text(encoding="utf-8")
    out = {}
    for block in re.findall(r"<Package>(.*?)</Package>", text, re.S):
        name = re.search(r"<Name>([^<]+)</Name>", block).group(1)

        def lang(tag, lg):
            m = re.search(
                r'<%s xml:lang="%s">(?:<!\[CDATA\[(.*?)\]\]>|(.*?))</%s>'
                % (tag, lg, tag), block, re.S)
            if not m:
                return ""
            return (m.group(1) if m.group(1) is not None else m.group(2)).strip()

        lic = re.search(r"<License>([^<]+)</License>", block)
        home = re.search(r"<Homepage>([^<]+)</Homepage>", block)
        ver = re.search(r"<Version>([^<]+)</Version>", block)
        out[name] = dict(
            summary_en=lang("Summary", "en"),
            summary_fr=lang("Summary", "fr"),
            desc_en=lang("Description", "en"),
            desc_fr=lang("Description", "fr"),
            license=lic.group(1) if lic else "GPL-3.0-or-later",
            homepage=home.group(1) if home else f"{GITEA}/{name}",
            version=ver.group(1) if ver else "0",
        )
    return out


def latest_artifact(pkg):
    files = list((ROOT / pkg[0] / pkg).glob("*.eopkg"))
    if not files:
        raise SystemExit(f"aucun .eopkg pour {pkg}")

    def rel(p):
        m = re.search(r"-(\d+)-1-x86_64\.eopkg$", p.name)
        return int(m.group(1)) if m else -1

    return max(files, key=rel)


def read_payload(pkg):
    """{chemin: bytes} des membres utiles (desktop + icônes hicolor) et l'historique."""
    art = latest_artifact(pkg)
    files, history = {}, []
    with zipfile.ZipFile(art) as z:
        meta = z.read("metadata.xml").decode("utf-8", "replace")
        with tarfile.open(fileobj=io.BytesIO(z.read("install.tar.xz"))) as tar:
            for m in tar.getmembers():
                if not m.isfile():
                    continue
                if m.name.endswith(".desktop") or re.search(
                        r"usr/share/icons/hicolor/(\d+)x\d+/apps/[^/]+\.png$", m.name):
                    files[m.name] = tar.extractfile(m).read()
    # <History> : la release la plus récente donne la version ET la date réelles
    for upd in re.finditer(r'<Update release="(\d+)">(.*?)</Update>', meta, re.S):
        rel, body = int(upd.group(1)), upd.group(2)
        d = re.search(r"<Date>([^<]+)</Date>", body)
        v = re.search(r"<Version>([^<]+)</Version>", body)
        if d and v:
            history.append((rel, v.group(1).strip(), d.group(1).strip()))
    history.sort(reverse=True)
    return files, (history[0] if history else None)


def parse_desktop(text):
    """{clé: valeur} pour un .desktop (section [Desktop Entry] uniquement)."""
    out, in_entry = {}, False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("["):
            in_entry = line == "[Desktop Entry]"
            continue
        if not in_entry or not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def as_categories(desktop_cats):
    cats = []
    for c in (desktop_cats or "").split(";"):
        c = DESKTOP_CATEGORY_MAP.get(c.strip(), c.strip())
        if c in AS_CATEGORIES and c not in cats:
            cats.append(c)
    return cats or ["Utility"]


# ─────────────────────────────────────────────────────────────────────────────
# Rendu XML
# ─────────────────────────────────────────────────────────────────────────────
def para(text):
    """Paragraphe AppStream : lignes du dépôt recollées en texte continu."""
    return escape(" ".join(l.strip() for l in text.splitlines() if l.strip()))


def metainfo_xml(app, info, today):
    L = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<component type="{app["kind"]}">',
        f"  <id>{app['id']}</id>",
        "  <metadata_license>CC0-1.0</metadata_license>",
        f"  <project_license>{escape(info['license'])}</project_license>",
        f'  <developer id="{DEVELOPER_ID}"><name>{DEVELOPER_NAME}</name></developer>',
        f"  <name>{escape(info['name_en'])}</name>",
    ]
    if info["name_fr"] and info["name_fr"] != info["name_en"]:
        L.append(f'  <name xml:lang="fr">{escape(info["name_fr"])}</name>')
    L.append(f"  <summary>{escape(info['summary_en'])}</summary>")
    if info["summary_fr"] and info["summary_fr"] != info["summary_en"]:
        L.append(f'  <summary xml:lang="fr">{escape(info["summary_fr"])}</summary>')
    if app.get("desktop"):
        L.append(f'  <launchable type="desktop-id">{app["desktop"]}</launchable>')
    L.append(f'  <url type="homepage">{escape(info["homepage"])}</url>')
    L.append('  <content_rating type="oars-1.1"/>')
    L.append("  <description>")
    L.append(f"    <p>{para(info['desc_en'] or info['summary_en'])}</p>")
    if info["desc_fr"]:
        L.append(f'    <p xml:lang="fr">{para(info["desc_fr"])}</p>')
    L.append("  </description>")
    L.append("  <categories>")
    L += [f"    <category>{c}</category>" for c in info["cats"]]
    L.append("  </categories>")
    if app["keywords"]:
        L.append("  <keywords>")
        L += [f"    <keyword>{escape(k)}</keyword>" for k in app["keywords"]]
        L.append("  </keywords>")
    if app.get("shot"):
        L += ["  <screenshots>", '    <screenshot type="default">',
              f'      <image type="source">{escape(app["shot"])}</image>',
              "    </screenshot>", "  </screenshots>"]
    L += ["  <releases>",
          f'    <release version="{escape(info["version"])}" '
          f'date="{info["release_date"]}"/>',
          "  </releases>", "</component>"]
    return "\n".join(L) + "\n"


def catalog_component(app, info, icon_files):
    L = [
        f'<component type="{app["kind"]}">',
        f"  <id>{app['id']}</id>",
        f"  <name>{escape(info['name_en'])}</name>",
        f"  <summary>{escape(info['summary_en'])}</summary>",
        f"  <pkgname>{app['pkg']}</pkgname>",
    ]
    if app.get("icon") and CATALOG_ICON_SIZE in icon_files:
        L.append(f'  <icon type="cached" width="{CATALOG_ICON_SIZE}" '
                 f'height="{CATALOG_ICON_SIZE}">{icon_files[CATALOG_ICON_SIZE]}</icon>')
    elif app.get("stock"):
        L.append(f'  <icon type="stock">{app["stock"]}</icon>')
    L.append("  <categories>")
    L += [f"    <category>{c}</category>" for c in info["cats"]]
    L.append("  </categories>")
    L.append("</component>")
    return "\n".join(L)


def main():
    index = read_index()
    today = date.today().isoformat()
    (OUT / "metainfo").mkdir(parents=True, exist_ok=True)
    (OUT / "icons").mkdir(parents=True, exist_ok=True)

    components, report = [], []
    for app in APPS:
        pkg = app["pkg"]
        if pkg not in index:
            raise SystemExit(f"{pkg} absent de eopkg-index.xml")
        meta = index[pkg]
        payload, history = read_payload(pkg)

        desktop_path = next((p for p in payload if p.endswith(".desktop")), None)
        dt = parse_desktop(payload[desktop_path].decode("utf-8")) if desktop_path else {}

        # Le .desktop peut donner un chemin absolu (Icon=/usr/share/pixmaps/x.png)
        raw_icon = dt.get("Icon", "")
        icon_name = raw_icon.rsplit("/", 1)[-1]
        icon_name = re.sub(r"\.(png|svg|xpm)$", "", icon_name) if icon_name else ""

        version, release_date = (history[1], history[2]) if history else (meta["version"], today)
        info = dict(
            version=version,
            release_date=release_date,
            license=meta["license"],
            homepage=homepage(pkg),
            name_en=app.get("name_en") or dt.get("Name") or pkg,
            name_fr=app.get("name_fr") or dt.get("Name[fr]", ""),
            # Summary/Description de l'index : bilingues et tenus à jour
            # (le Comment d'un .desktop est souvent monolingue).
            summary_en=app.get("summary_en") or meta["summary_en"] or dt.get("Comment", ""),
            summary_fr=app.get("summary_fr") or meta["summary_fr"]
            or dt.get("Comment[fr]", ""),
            desc_en=meta["desc_en"],
            desc_fr=meta["desc_fr"],
            cats=app.get("cats") or as_categories(dt.get("Categories")),
        )
        if isinstance(app.get("shot"), tuple):
            app = dict(app, shot=raw_url(*app["shot"]))
        app = dict(app, desktop=desktop_path.rsplit("/", 1)[-1] if desktop_path else None,
                   kind=app.get("kind", "desktop-application"),
                   icon=icon_name or None)

        (OUT / "metainfo" / f"{app['id']}.metainfo.xml").write_text(
            metainfo_xml(app, info, today), encoding="utf-8")

        icon_files = {}
        if app.get("icon"):
            for path, data in payload.items():
                hit = re.search(r"hicolor/(\d+)x\d+/apps/([^/]+)\.png$", path)
                if hit and int(hit.group(1)) in ICON_SIZES:
                    size = int(hit.group(1))
                    d = OUT / "icons" / f"{size}x{size}"
                    d.mkdir(parents=True, exist_ok=True)
                    fn = f"{pkg}_{app['icon']}.png"
                    (d / fn).write_bytes(data)
                    icon_files[size] = fn

        components.append(catalog_component(app, info, icon_files))
        report.append(f"  {pkg:32s} {app['id']:42s} v{info['version']:9s} "
                      f"icônes={sorted(icon_files) or 'stock'}")

    catalog = ('<?xml version="1.0" encoding="utf-8"?>\n'
               f'<components version="1.0" origin="{ORIGIN}" time="{today}T00:00:00Z">\n'
               + "\n".join(components) + "\n</components>\n")
    (OUT / f"{ORIGIN}.xml").write_text(catalog, encoding="utf-8")
    (OUT / f"{ORIGIN}.xml.gz").write_bytes(gzip.compress(catalog.encode("utf-8"), 9, mtime=0))

    print("Catalogue AppStream généré :")
    print("\n".join(report))
    print(f"\n  {OUT / (ORIGIN + '.xml.gz')}  ({len(components)} composants)")
    print(f"  {OUT / 'metainfo'}  ({len(components)} fiches)")


if __name__ == "__main__":
    main()
