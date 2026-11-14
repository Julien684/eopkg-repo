#!/usr/bin/env python3
"""
sync_index.py — Met à jour eopkg-index.xml pour un paquet du dépôt.

- Paquet absent de l'index  -> bloc <Package> complet créé depuis le
  metadata.xml du .eopkg (résumés/descriptions en + fr, historique, etc.).
- Paquet déjà présent       -> seuls les champs « mécaniques » sont mis à jour
  (Version, InstalledSize, PackageSize, PackageHash, PackageURI, History,
  RuntimeDependencies). Les Summary/Description rédigés à la main sont
  conservés.

Puis régénère eopkg-index.xml.xz et les quatre fichiers *.sha1sum/*.sha256sum
(hash BRUT, sans nom de fichier — exigé par pisi/file.py), et vérifie que
chaque <PackageHash>/<PackageSize> correspond au fichier pointé par
<PackageURI>.

Usage: python3 tools/sync_index.py <paquet> [fichier.eopkg]
"""
import hashlib
import lzma
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "eopkg-index.xml"


def pick_artifact(pkg, explicit=None):
    if explicit:
        p = Path(explicit)
        return p if p.is_absolute() else ROOT / p
    files = list((ROOT / pkg[0] / pkg).glob("*.eopkg"))
    if not files:
        raise SystemExit(f"aucun .eopkg dans {pkg[0]}/{pkg}/")

    def rel(p):
        m = re.search(r"-(\d+)-1-x86_64\.eopkg$", p.name)
        return int(m.group(1)) if m else -1

    return max(files, key=rel)


def read_meta(art):
    with zipfile.ZipFile(art) as z:
        return z.read("metadata.xml").decode("utf-8")


def tag(meta, name, lang=None):
    pat = (rf'<{name} xml:lang="{lang}">(.*?)</{name}>' if lang
           else rf"<{name}>(.*?)</{name}>")
    m = re.search(pat, meta, re.S)
    if not m:
        return ""
    v = m.group(1)
    v = re.sub(r"^<!\[CDATA\[(.*)\]\]>$", r"\1", v, flags=re.S)
    return v.strip()


def history_block(meta):
    m = re.search(r"<History>(.*?)</History>", meta, re.S)
    if not m:
        return ""
    body = m.group(1).strip("\n")
    # ré-indenter sous le bloc <Package> de l'index
    lines = [l.strip() for l in body.splitlines() if l.strip()]
    return "\n".join("            " + l for l in lines)


def full_block(pkg, meta, art):
    uri = art.relative_to(ROOT).as_posix()
    deps = re.search(r"<RuntimeDependencies>(.*?)</RuntimeDependencies>", meta, re.S)
    deps_body = "\n".join(
        "            " + l.strip() for l in (deps.group(1) if deps else "").splitlines()
        if l.strip()
    )
    src_home = tag(meta, "Homepage") or f"https://depoa.julien68.fr/Linuxon/{pkg}"
    packager_name = re.search(r"<Packager>\s*<Name>([^<]+)</Name>", meta, re.S)
    packager_mail = re.search(r"<Packager>\s*<Name>[^<]+</Name>\s*<Email>([^<]+)</Email>",
                              meta, re.S)
    return f"""        <Package>
            <Name>{pkg}</Name>
            <Summary xml:lang="en"><![CDATA[{tag(meta, 'Summary', 'en')}]]></Summary>
            <Summary xml:lang="fr"><![CDATA[{tag(meta, 'Summary', 'fr')}]]></Summary>
            <Description xml:lang="en"><![CDATA[{tag(meta, 'Description', 'en')}]]></Description>
            <Description xml:lang="fr"><![CDATA[{tag(meta, 'Description', 'fr')}]]></Description>
            <PartOf>{tag(meta, 'PartOf')}</PartOf>
            <License>{tag(meta, 'License')}</License>
            <RuntimeDependencies>
{deps_body}
            </RuntimeDependencies>
            <History>
{history_block(meta)}
            </History>
            <BuildHost>{tag(meta, 'BuildHost')}</BuildHost>
            <Distribution>{tag(meta, 'Distribution')}</Distribution>
            <DistributionRelease>{tag(meta, 'DistributionRelease')}</DistributionRelease>
            <Architecture>{tag(meta, 'Architecture')}</Architecture>
            <InstalledSize>{tag(meta, 'InstalledSize')}</InstalledSize>
            <PackageSize>{art.stat().st_size}</PackageSize>
            <PackageHash>{hashlib.sha1(art.read_bytes()).hexdigest()}</PackageHash>
            <PackageURI>{uri}</PackageURI>
            <PackageFormat>{tag(meta, 'PackageFormat')}</PackageFormat>
            <Source>
                <Name>{pkg}</Name>
                <Homepage>{src_home}</Homepage>
                <Packager>
                    <Name>{packager_name.group(1) if packager_name else 'Julien'}</Name>
                    <Email>{packager_mail.group(1) if packager_mail else ''}</Email>
                </Packager>
            </Source>
        </Package>"""


def patch_block(block, meta, art):
    uri = art.relative_to(ROOT).as_posix()

    def setv(pattern, value, text):
        return re.sub(pattern, value, text, count=1, flags=re.S)

    block = setv(r"<Version>[^<]*</Version>", f"<Version>{tag(meta, 'Version')}</Version>", block)
    block = setv(r"<InstalledSize>[^<]*</InstalledSize>",
                 f"<InstalledSize>{tag(meta, 'InstalledSize')}</InstalledSize>", block)
    block = setv(r"<PackageSize>[^<]*</PackageSize>",
                 f"<PackageSize>{art.stat().st_size}</PackageSize>", block)
    block = setv(r"<PackageHash>[^<]*</PackageHash>",
                 f"<PackageHash>{hashlib.sha1(art.read_bytes()).hexdigest()}</PackageHash>", block)
    block = setv(r"<PackageURI>[^<]*</PackageURI>", f"<PackageURI>{uri}</PackageURI>", block)
    block = re.sub(r"<History>.*?</History>",
                   "<History>\n" + history_block(meta) + "\n            </History>",
                   block, count=1, flags=re.S)
    deps = re.search(r"<RuntimeDependencies>(.*?)</RuntimeDependencies>", meta, re.S)
    deps_body = "\n".join("            " + l.strip()
                          for l in (deps.group(1) if deps else "").splitlines() if l.strip())
    block = re.sub(r"<RuntimeDependencies>.*?</RuntimeDependencies>",
                   "<RuntimeDependencies>\n" + deps_body + "\n            </RuntimeDependencies>",
                   block, count=1, flags=re.S)
    return block


def write_sums():
    data = INDEX.read_bytes()
    xz = INDEX.with_suffix(".xml.xz")
    xz.write_bytes(lzma.compress(data, format=lzma.FORMAT_XZ, preset=9))
    for f in (INDEX, xz):
        raw = f.read_bytes()
        Path(str(f) + ".sha1sum").write_text(hashlib.sha1(raw).hexdigest())
        Path(str(f) + ".sha256sum").write_text(hashlib.sha256(raw).hexdigest())


def verify():
    text = INDEX.read_text(encoding="utf-8")
    bad = 0
    for block in re.findall(r"<Package>(.*?)</Package>", text, re.S):
        name = re.search(r"<Name>([^<]+)</Name>", block).group(1)
        uri = re.search(r"<PackageURI>([^<]+)</PackageURI>", block).group(1)
        ph = re.search(r"<PackageHash>([^<]+)</PackageHash>", block).group(1)
        ps = int(re.search(r"<PackageSize>(\d+)</PackageSize>", block).group(1))
        path = ROOT / uri
        if not path.exists():
            print(f"  ✗ {name}: {uri} absent du disque")
            bad += 1
            continue
        raw = path.read_bytes()
        ok = hashlib.sha1(raw).hexdigest() == ph and len(raw) == ps
        if not ok:
            print(f"  ✗ {name}: hash/taille incohérents ({uri})")
            bad += 1
        for lg in ("en", "fr"):
            for t in ("Summary", "Description"):
                m = re.search(rf'<{t} xml:lang="{lg}">(?:<!\[CDATA\[(.*?)\]\]>)', block, re.S)
                if not m or not m.group(1).strip():
                    print(f"  ✗ {name}: {t}[{lg}] vide")
                    bad += 1
    return bad


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    pkg = sys.argv[1]
    art = pick_artifact(pkg, sys.argv[2] if len(sys.argv) > 2 else None)
    if not art.exists():
        raise SystemExit(f"introuvable : {art}")
    meta = read_meta(art)

    text = INDEX.read_text(encoding="utf-8")
    m = re.search(r"        <Package>\s*<Name>%s</Name>.*?        </Package>" % re.escape(pkg),
                  text, re.S)
    if m:
        new_block = patch_block(m.group(0), meta, art)
        text = text[:m.start()] + new_block + text[m.end():]
        action = "mis à jour"
    else:
        block = full_block(pkg, meta, art)
        pos = text.rindex("    </PISI>")
        text = text[:pos] + block + "\n" + text[pos:]
        action = "ajouté"

    INDEX.write_text(text, encoding="utf-8")
    write_sums()

    bad = verify()
    print(f"  {pkg} {action} dans eopkg-index.xml "
          f"({tag(meta, 'Version')}-{tag(meta, 'Release') or '?'})")
    print(f"  index : {INDEX.stat().st_size} octets, "
          f"xz : {INDEX.with_suffix('.xml.xz').stat().st_size} octets")
    if bad:
        raise SystemExit(f"  {bad} incohérence(s) — index NON publiable")
    print("  ✓ tous les PackageHash/PackageSize et les textes en/fr sont valides")


if __name__ == "__main__":
    main()
