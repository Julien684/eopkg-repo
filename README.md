# eopkg-repo — Linuxon / Solus EOPKG Repository

Repository EOPKG personnel pour les paquets Solus `amv-converter`, `btrfsmgr`,
`btrfsmgr-gui`, `deb-to-eopkg`, `ollama-manager-qt` et
`solus-external-kernel-manager`.

> **Testé de bout-en-bout sur Solus 4.9 (eopkg 5.0.0)** :
> `eopkg add-repo` + `eopkg install btrfsmgr` fonctionnent.

## ⚠️ Format des `.sha1sum` (important)

pisi lit **uniquement le hash brut** du fichier `.sha1sum` (`pisi/file.py` :
`newsha1 = sha1f.read().split("\n")[0]`). Le format GNU standard
`<hash>  <filename>` **ne marche pas** et fait échouer `eopkg add-repo`
avec "repository could not be reached" (le dépôt est alors retiré).

Le CDN Solus officiel (`cdn.getsol.us`) utilise aussi le **hash brut seul** :
```
99962ca5a93a011d385eea675137edab3cec24e9
```

## Installation du dépôt

URL publique :

```
https://depoa.julien68.fr/Linuxon/eopkg-repo/raw/branch/main/eopkg-index.xml
```

> Les fichiers bruts (index et `.eopkg`) sont servis par
> `depoa.julien68.fr/…/raw/branch/main/`, sans authentification.

### Commandes (eopkg 5.0)

#### Ajouter le dépôt (syntaxe: add-repo <nom> <url>, sans options)
```bash
sudo eopkg add-repo linuxon https://depoa.julien68.fr/Linuxon/eopkg-repo/raw/branch/main/eopkg-index.xml
```
#### Vérifier
```bash
sudo eopkg list-repo
```
#### Installer un paquet

Un bloc par paquet ; chaque lien mène à la page du projet.

**[amv-converter](https://depoa.julien68.fr/Linuxon/amv-converter)** — convertit une vidéo en AMV pour petits lecteurs MP3/vidéo
```bash
sudo eopkg install amv-converter
```

**[btrfsmgr](https://depoa.julien68.fr/Linuxon/btrfsmgr)** — gestionnaire Btrfs (CLI)
```bash
sudo eopkg install btrfsmgr
```

**[btrfsmgr-gui](https://depoa.julien68.fr/Linuxon/btrfsmgr-gui)** — interface graphique de btrfsmgr (Qt6)
```bash
sudo eopkg install btrfsmgr-gui
```

**[deb-to-eopkg](https://depoa.julien68.fr/Linuxon/deb-to-eopkg)** — convertit un paquet `.deb` en `.eopkg` (Rust)
```bash
sudo eopkg install deb-to-eopkg
```

**[ollama-manager-qt](https://depoa.julien68.fr/Linuxon/ollama-manager-qt)** — gestionnaire de modèles Ollama (Qt6)
```bash
sudo eopkg install ollama-manager-qt
```

**[solus-external-kernel-manager](https://depoa.julien68.fr/Linuxon/solus-external-kernel-manager)** — installe des noyaux CachyOS / Zen / Liquorix sur Solus (Qt6)
```bash
sudo eopkg install solus-external-kernel-manager
```

**[linuxon-appstream-catalog](https://depoa.julien68.fr/Linuxon/eopkg-repo)** — métadonnées AppStream : rend les applications du dépôt visibles dans Discover / GNOME Software
```bash
sudo eopkg install linuxon-appstream-catalog
sudo appstreamcli refresh --source=os
```

#### Retirer le dépôt
```bash
sudo eopkg remove-repo linuxon
```

#### Vider le cache (après une mise à jour des .eopkg)
```bash
sudo eopkg delete-cache
```

> **Note syntaxe** : eopkg 5.0 utilise `add-repo`/`remove-repo`/`list-repo`
> (pas `repo-add`/`repo-rm`/`showrepo` des versions anciennes) et n'accepte
> que `--ignore-check`, `--no-fetch`, `--at` en options — pas de `--name`
> ni `--description`.

## Structure du dépôt

```
eopkg-repo/
├── eopkg-index.xml            ← index PISI (lu par eopkg)
├── eopkg-index.xml.xz         ← index compressé XZ
├── eopkg-index.xml.sha1sum    ← HASH BRUT (pas "hash  filename")
├── eopkg-index.xml.sha256sum
├── eopkg-index.xml.xz.sha1sum
├── eopkg-index.xml.xz.sha256sum
├── appstream/                 ← catalogue AppStream (généré) + fiches metainfo
│   ├── linuxon-main.xml.gz
│   ├── icons/<taille>/*.png
│   └── metainfo/<id>.metainfo.xml
├── tools/                     ← gen_appstream.py, build_appstream_eopkg.py, sync_index.py
├── l/
│   └── linuxon-appstream-catalog/
│       └── linuxon-appstream-catalog-1.0.0-1-1-x86_64.eopkg
├── b/
│   ├── btrfsmgr/
│   │   └── btrfsmgr-1.0.13-2-1-x86_64.eopkg
│   └── btrfsmgr-gui/
│       └── btrfsmgr-gui-1.1.2-1-1-x86_64.eopkg
└── d/
    └── deb-to-eopkg/
        └── deb-to-eopkg-2.2.0-1-1-x86_64.eopkg
└── s/
    └── solus-external-kernel-manager/
        └── solus-external-kernel-manager-0.1.1-2-1-x86_64.eopkg
```

Le chemin `<lettre>/<nom-paquet>/<fichier>.eopkg` suit la convention du CDN
officiel Solus (`cdn.getsol.us/repo/polaris/`).

## Discover / GNOME Software (AppStream)

Les applications du dépôt apparaissent dans **Discover** (KDE) et **GNOME
Software** grâce à un catalogue AppStream livré par le paquet
`linuxon-appstream-catalog`.

**Pourquoi un catalogue séparé :**

- le backend PackageKit `eopkg` de Solus ne publie **aucune** donnée AppStream
  par dépôt — `libpk_backend_eopkg.so` ne contient aucune référence à
  `appstream`/`swcatalog`, et il n'existe pas de méthode « AppStream par
  dépôt » dans PackageKit ;
- Discover / GNOME Software ne lisent que :
  1. les catalogues système `/usr/share/swcatalog/xml/*.xml.gz`, fournis par le
     paquet `appstream-catalog` de Solus, qui ne couvre que les dépôts
     officiels ;
  2. les fichiers `metainfo` des paquets **installés**
     (`/usr/share/metainfo/`) ;
- le paquet `linuxon-appstream-catalog` installe donc
  `/usr/share/swcatalog/xml/linuxon-main.xml.gz` (+ les icônes), avec un
  `<pkgname>` par composant : c'est ce lien qui associe la fiche AppStream au
  paquet eopkg et rend le bouton « Installer » fonctionnel via PackageKit.

Après installation ou mise à jour du catalogue :

```bash
sudo appstreamcli refresh --source=os
```

Vérification : `appstreamcli search btrfsmgr` (ou `appstreamcli get
fr.julien68.BtrfsManager`), puis relancer Discover.

**Régénérer le catalogue** (après ajout ou mise à jour d'un paquet) :

```bash
python3 tools/gen_appstream.py            # appstream/linuxon-main.xml.gz + appstream/metainfo/
# incrémenter RELEASE dans tools/build_appstream_eopkg.py
python3 tools/build_appstream_eopkg.py    # l/linuxon-appstream-catalog/*.eopkg
python3 tools/sync_index.py linuxon-appstream-catalog
```

`tools/gen_appstream.py` déduit nom, résumé, catégories et icône du `.desktop`
et des icônes embarqués dans le `.eopkg` le plus récent, et prend version,
licence et textes bilingues dans `eopkg-index.xml`. Les fiches
`appstream/metainfo/<id>.metainfo.xml` produites au passage sont destinées à
être **embarquées dans chaque paquet d'application** (`usr/share/metainfo/`)
lors de sa prochaine release : un paquet qui porte sa propre fiche reste
reconnu même sans le catalogue.

## Regénérer l'index

Après avoir déposé un nouveau `.eopkg` dans le bon sous-dossier
`<lettre>/<nom>/`, régénérer `eopkg-index.xml` (et ses variantes `.xz` +
`.sha1sum`/`.sha256sum`).

**Checklist de build de l'index :**
- [ ] `eopkg-index.xml` : `<PISI><Distribution>…</Distribution><Package>…</Package>…</PISI>`
- [ ] Chaque `<Package>` contient : `Name`, `Summary`/`Description` (en + fr, en CDATA),
      `PartOf`, `License`, `<RuntimeDependencies></RuntimeDependencies>` (vide),
      `<History><Update release=…>`, `BuildHost`, `Distribution`, `DistributionRelease`,
      `Architecture`, `InstalledSize`, `PackageSize`, `PackageHash` (SHA1 du .eopkg),
      `PackageURI` (= `<lettre>/<nom>/<fichier>`, relatif à la racine du repo),
      `PackageFormat`, `<Source>` (Name/Homepage/Packager).
- [ ] `eopkg-index.xml.xz` = même contenu, compressé en XZ.
- [ ] `.sha1sum` / `.sha256sum` : **hash brut seul**, sans nom de fichier.

## Notes

- Les paquets sont construits hors dépôt Solus : aucun
  `<RuntimeDependencies>` PISI résolvable. Les prérequis sont vérifiés au
  runtime par les applications (`btrfsmgr` check `shutil.which("btrfs")`).
- Architecture : `x86_64` uniquement.
- Le texte FR dans `metadata.xml` passe par `.encode('utf-8')` dans les
  build scripts — ne jamais le faire transiter par un helper ascii-replace.

## Projets sources

| Paquet         | Gitea                                                            |
|----------------|------------------------------------------------------------------|
| amv-converter  | https://depoa.julien68.fr/Linuxon/amv-converter |
| btrfsmgr       | https://depoa.julien68.fr/Linuxon/btrfsmgr |
| btrfsmgr-gui   | https://depoa.julien68.fr/Linuxon/btrfsmgr-gui |
| deb-to-eopkg   | https://depoa.julien68.fr/Linuxon/deb-to-eopkg |
| ollama-manager-qt | https://depoa.julien68.fr/Linuxon/ollama-manager-qt |
| solus-external-kernel-manager | https://depoa.julien68.fr/Linuxon/solus-external-kernel-manager |
