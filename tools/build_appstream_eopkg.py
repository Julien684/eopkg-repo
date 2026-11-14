#!/usr/bin/env python3
"""
build_appstream_eopkg.py — Construit le paquet linuxon-appstream-catalog.

Ce paquet ne contient que des données : le catalogue AppStream du dépôt
(/usr/share/swcatalog/xml/linuxon-main.xml.gz) et ses icônes. Installé, il
fait apparaître toutes les applications du dépôt dans Discover et GNOME
Software, y compris celles qui ne sont pas encore installées.

Usage: python3 tools/build_appstream_eopkg.py [out_dir]
"""
import hashlib
import io
import sys
import tarfile
import zipfile
from datetime import date
from xml.sax.saxutils import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "l" / "linuxon-appstream-catalog"
AS = ROOT / "appstream"

PACKAGE_NAME = "linuxon-appstream-catalog"
VERSION = "1.0.0"
RELEASE = 10          # ⚠ incrémenter à CHAQUE régénération du catalogue
DIST_RELEASE = 1
ARCH = "x86_64"
DIST_NAME = "Solus"
BUILD_HOST = "solus-local"
HOME_PAGE = "https://depoa.julien68.fr/Linuxon/eopkg-repo"
PACKAGER_NAME = "Julien"
PACKAGER_EMAIL = "julien_solus@use.startmail.com"
PART_OF = "desktop.core"

OUT_FILENAME = f"{PACKAGE_NAME}-{VERSION}-{RELEASE}-{DIST_RELEASE}-{ARCH}.eopkg"

SUMMARY_EN = ("AppStream metadata for the Linuxon repository: its applications "
              "show up in Discover and GNOME Software")
SUMMARY_FR = ("Métadonnées AppStream du dépôt Linuxon : ses applications "
              "apparaissent dans Discover et GNOME Software")
DESC_EN = """This package ships the AppStream catalog of the Linuxon eopkg
repository (/usr/share/swcatalog/xml/linuxon-main.xml.gz plus its icons).
Solus' PackageKit backend does not publish per-repository AppStream data, and
the distribution catalog (appstream-catalog) only covers the official
repositories, so a third-party repository must provide its own catalog.
Without it, an application only becomes visible once installed (and only if
its own package ships a metainfo file). With it, Discover and GNOME Software
can browse, search and install the repository's applications, mapping each
AppStream component to its eopkg package through <pkgname>. After installing
or updating this package, refresh the AppStream cache with
"sudo appstreamcli refresh --source=os" (Discover may need a restart)."""
DESC_FR = """Ce paquet fournit le catalogue AppStream du dépôt eopkg Linuxon
(/usr/share/swcatalog/xml/linuxon-main.xml.gz et ses icônes). Le backend
PackageKit de Solus ne publie aucune donnée AppStream par dépôt, et le
catalogue de la distribution (appstream-catalog) ne couvre que les dépôts
officiels : un dépôt tiers doit donc fournir le sien. Sans lui, une
application n'apparaît qu'une fois installée (et seulement si son propre
paquet embarque un fichier metainfo). Avec lui, Discover et GNOME Software
peuvent parcourir, rechercher et installer les applications du dépôt, chaque
composant AppStream étant relié à son paquet eopkg par <pkgname>. Après
installation ou mise à jour de ce paquet, rafraîchir le cache AppStream avec
« sudo appstreamcli refresh --source=os » (un redémarrage de Discover peut
être nécessaire)."""


def sha1_hex(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def file_type_for(path: str) -> str:
    if path.startswith(("usr/bin/", "bin/", "usr/sbin/", "usr/libexec/")):
        return "executable"
    if path.startswith("usr/share/doc/") or path.startswith("usr/share/help/"):
        return "doc"
    return "data"


def file_list():
    """[(chemin dans le paquet, fichier source, mode)]"""
    entries = [
        ("usr/share/swcatalog/xml/linuxon-main.xml.gz",
         AS / "linuxon-main.xml.gz", 0o644),
        ("usr/share/doc/" + PACKAGE_NAME + "/README.md",
         AS / "README.md", 0o644),
        ("usr/share/licenses/" + PACKAGE_NAME + "/LICENSE",
         AS / "LICENSE", 0o644),
    ]
    for size_dir in sorted((AS / "icons").glob("*x*")):
        for png in sorted(size_dir.glob("*.png")):
            entries.append((f"usr/share/swcatalog/icons/linuxon-main/{size_dir.name}/{png.name}",
                            png, 0o644))
    return entries


def build():
    if not (AS / "linuxon-main.xml.gz").exists():
        raise SystemExit("appstream/linuxon-main.xml.gz absent : lancer tools/gen_appstream.py d'abord")

    entries = []
    for dest, src, mode in file_list():
        if not src.exists():
            raise SystemExit(f"fichier source manquant : {src}")
        entries.append((dest, src.read_bytes(), mode))

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:xz") as tar:
        for dest, data, mode in entries:
            info = tarfile.TarInfo(name=dest)
            info.size = len(data)
            info.mode = mode
            info.uid = info.gid = 0
            info.mtime = 0
            tar.addfile(info, io.BytesIO(data))
    install_tar_xz = buf.getvalue()

    files_parts = ["<Files>"]
    for dest, data, mode in entries:
        files_parts += [
            "  <File>",
            f"    <Path>{dest}</Path>",
            f"    <Type>{file_type_for(dest)}</Type>",
            f"    <Size>{len(data)}</Size>",
            "    <Uid>0</Uid>",
            "    <Gid>0</Gid>",
            f"    <Mode>{mode:04o}</Mode>",
            f"    <Hash>{sha1_hex(data)}</Hash>",
            "  </File>",
        ]
    files_parts.append("</Files>")
    files_xml = "\n".join(files_parts).encode("utf-8")

    today = date.today().isoformat()
    installed_size = sum(len(d) for _, d, _ in entries)

    # Un <RuntimeDependencies> VIDE fait planter eopkg (free(): double free dans
    # la vérification des dépendances inverses) : ne l'émettre que s'il y a
    # réellement des dépendances, comme tous les autres paquets du dépôt.
    RUNTIME_DEPS: list[str] = []
    deps_xml = ""
    if RUNTIME_DEPS:
        deps_xml = ("        <RuntimeDependencies>\n"
                    + "".join(f"            <Dependency>{d}</Dependency>\n"
                              for d in RUNTIME_DEPS)
                    + "        </RuntimeDependencies>\n")

    def a(s: str) -> str:
        return s.encode("ascii", "replace").decode("ascii")

    # Le texte des descriptions doit être ÉCHAPPÉ : « <pkgname> » y figure
    # littéralement et, laissé brut, il est lu comme un élément XML — eopkg
    # 5.0 plante alors au parsing du paquet (« free(): double free »).
    desc_en = escape(a(DESC_EN))
    desc_fr = escape(DESC_FR)

    metadata_xml = f"""<PISI>
    <Source>
        <Name>{PACKAGE_NAME}</Name>
        <Homepage>{HOME_PAGE}</Homepage>
        <Packager>
            <Name>{PACKAGER_NAME}</Name>
            <Email>{PACKAGER_EMAIL}</Email>
        </Packager>
    </Source>
    <Package>
        <Name>{PACKAGE_NAME}</Name>
        <Summary xml:lang="en">{a(SUMMARY_EN)}</Summary>
        <Summary xml:lang="fr">{SUMMARY_FR}</Summary>
        <Description xml:lang="en">{desc_en}</Description>
        <Description xml:lang="fr">{desc_fr}</Description>
        <PartOf>{PART_OF}</PartOf>
        <License>CC0-1.0</License>
{deps_xml}        <History>
            <Update release="{RELEASE}">
                <Date>{today}</Date>
                <Version>{VERSION}</Version>
                <Comment>{PACKAGE_NAME} {VERSION} : catalogue AppStream du depot (Discover / GNOME Software)</Comment>
                <Name>{PACKAGER_NAME}</Name>
                <Email>{PACKAGER_EMAIL}</Email>
            </Update>
        </History>
        <BuildHost>{BUILD_HOST}</BuildHost>
        <Distribution>{DIST_NAME}</Distribution>
        <DistributionRelease>{DIST_RELEASE}</DistributionRelease>
        <Architecture>{ARCH}</Architecture>
        <InstalledSize>{installed_size}</InstalledSize>
        <PackageFormat>1.2</PackageFormat>
        <Source>
            <Name>{PACKAGE_NAME}</Name>
            <Homepage>{HOME_PAGE}</Homepage>
            <Packager>
                <Name>{PACKAGER_NAME}</Name>
                <Email>{PACKAGER_EMAIL}</Email>
            </Packager>
        </Source>
    </Package>
</PISI>""".encode("utf-8")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / OUT_FILENAME
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("metadata.xml", metadata_xml)
        zf.writestr("files.xml", files_xml)
        zf.writestr("install.tar.xz", install_tar_xz)

    print(f"  {len(entries)} fichiers, install.tar.xz {len(install_tar_xz)} octets")
    print(f"  ✓ {out_path}  ({out_path.stat().st_size} octets)")
    print(f"  SHA1 {sha1_hex(out_path.read_bytes())}")


if __name__ == "__main__":
    build()
