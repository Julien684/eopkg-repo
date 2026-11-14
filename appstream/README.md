# linuxon-appstream-catalog — métadonnées AppStream du dépôt Linuxon

Ce paquet installe le catalogue AppStream du dépôt eopkg `linuxon` :

```
/usr/share/swcatalog/xml/linuxon-main.xml.gz
/usr/share/swcatalog/icons/linuxon-main/{48x48,64x64,128x128}/*.png
```

Il ne contient aucun exécutable. Sans lui, les applications du dépôt
n'apparaissent dans Discover / GNOME Software qu'une fois installées (et
seulement si leur paquet embarque un fichier `metainfo`).

## Pourquoi un paquet séparé

- Le backend PackageKit `eopkg` de Solus ne publie **aucune** donnée AppStream
  par dépôt : `libpk_backend_eopkg.so` ne contient aucune référence à
  appstream/swcatalog.
- Discover et GNOME Software ne lisent que :
  1. les catalogues système de `/usr/share/swcatalog/xml/*.xml.gz`, fournis par
     le paquet `appstream-catalog` de Solus — qui ne couvre que les dépôts
     officiels ;
  2. les fichiers `metainfo` des paquets **installés** (`/usr/share/metainfo/`).
- Un dépôt tiers doit donc fournir son propre catalogue. Le lien entre un
  composant AppStream et un paquet se fait par `<pkgname>`, que le backend
  eopkg résout ensuite via PackageKit : c'est ce qui rend le bouton
  « Installer » fonctionnel.

## Après installation ou mise à jour

```bash
sudo appstreamcli refresh --source=os
```

Puis relancer Discover (`plasma-discover`) ou GNOME Software s'il était ouvert.

Vérification en ligne de commande :

```bash
appstreamcli search btrfsmgr
appstreamcli get fr.julien68.BtrfsManager
```

## Régénération

Depuis le dépôt `eopkg-repo` :

```bash
python3 tools/gen_appstream.py           # appstream/linuxon-main.xml.gz + metainfo/
# incrémenter RELEASE dans tools/build_appstream_eopkg.py
python3 tools/build_appstream_eopkg.py   # l/linuxon-appstream-catalog/*.eopkg
python3 tools/sync_index.py linuxon-appstream-catalog
```

`tools/gen_appstream.py` lit le `.desktop` et les icônes du `.eopkg` le plus
récent de chaque paquet, ainsi que `eopkg-index.xml` (version, licence,
résumés et descriptions bilingues). Les fiches `appstream/metainfo/<id>.xml`
produites au passage sont destinées à être embarquées **dans** chaque paquet
d'application (`usr/share/metainfo/`) lors de leur prochaine release : un
paquet qui porte sa propre fiche reste reconnu même sans ce catalogue.

## Licence

Les données du catalogue (identifiants, catégories, associations) sont
publiées sous CC0-1.0. Les noms, résumés, descriptions et icônes proviennent
des paquets du dépôt, distribués sous GPL-3.0-or-later.
