# eopkg-repo — Linuxon / Solus EOPKG Repository

Repository EOPKG personnel pour les paquets Solus `btrfsmgr`, `btrfsmgr-gui`
et `deb-to-eopkg`.

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
http://depoa.julien68.fr/Linuxon/eopkg-repo/raw/branch/main/eopkg-index.xml
```

> Le domaine `depoa.julien68.fr` redirige automatiquement vers le reverse
> proxy Gitea (HTTP → HTTPS), aucun port à préciser.

### Commandes (eopkg 5.0)

#### Ajouter le dépôt (syntaxe: add-repo <nom> <url>, sans options)
```bash
sudo eopkg add-repo linuxon http://depoa.julien68.fr/Linuxon/eopkg-repo/raw/branch/main/eopkg-index.xml
```
#### Vérifier
```bash
sudo eopkg list-repo
```
#### Installer un paquet
```bash
sudo eopkg install btrfsmgr
sudo eopkg install btrfsmgr-gui
sudo eopkg install deb-to-eopkg
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
├── b/
│   ├── btrfsmgr/
│   │   └── btrfsmgr-1.0.12-1-1-x86_64.eopkg
│   └── btrfsmgr-gui/
│       └── btrfsmgr-gui-1.1.2-1-1-x86_64.eopkg
└── d/
    └── deb-to-eopkg/
        └── deb-to-eopkg-2.2.0-1-1-x86_64.eopkg
```

Le chemin `<lettre>/<nom-paquet>/<fichier>.eopkg` suit la convention du CDN
officiel Solus (`cdn.getsol.us/repo/polaris/`).

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

| Paquet         | Gitea                                                        |
|----------------|--------------------------------------------------------------|
| btrfsmgr       | http://depoa.julien68.fr/Linuxon/btrfsmgr                    |
| btrfsmgr-gui   | http://depoa.julien68.fr/Linuxon/btrfsmgr-gui                |
| deb-to-eopkg   | http://depoa.julien68.fr/Linuxon/deb-to-eopkg                |
