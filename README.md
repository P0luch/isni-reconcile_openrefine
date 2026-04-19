# Service de reconcilaition ISNI

Service de réconciliation [OpenRefine](https://openrefine.org/) pour l'[API ISNI](https://isni.org/).

> Adapté depuis [isni-reconcile](https://github.com/cmharlow/isni-reconcile) (cmharlow)
> 
> Prototype — ce projet est issu d'une session de vibe coding assistée par IA. Il fonctionne mais n'a pas vocation à être utilisé en production sans revue du code.
> 
## Fonctionnalités

- Réconciliation de noms de personnes et d'organisations avec la base ISNI
- Trois modes de recherche :
  - **Nom exact** (`pica.na`) — recherche la séquence de mots dans les noms
  - **Mots-clés** (`pica.nw`) — recherche tous les mots dans les champs indexés
  - **Numéro ISNI** (`pica.isn`) — recherche directe par identifiant
- Extension de données : récupération des métadonnées associées
- Cache persistant des requêtes, exportable/importable pour reprendre sur un autre poste
- Interface de configuration et prévisualisation des résultats

## Prérequis

- Python 3.8+

## Installation

```bash
# Créer et activer un environnement virtuel
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

## Lancement

**Windows**
```bash
start.bat
```

**Linux / macOS**
```bash
chmod +x start.sh
./start.sh
```

Les scripts créent le venv et installent les dépendances automatiquement au premier lancement.

**Lancement manuel**
```bash
python reconcile.py
```

Le service est accessible sur `http://localhost:5100`.

## Utilisation dans OpenRefine

1. Lancer le service
2. Dans OpenRefine, sur une colonne → **Réconcilier > Démarrer la réconciliation**
3. Ajouter le service : `http://localhost:5100/reconcile`
4. Choisir le mode de recherche selon les données

## Extension de données

Les propriétés disponibles pour l'extension de données :

| Propriété | Description |
|---|---|
| `type_entite` | Type : `personne` ou `organisation` |
| `isni` | Identifiant ISNI formaté (`0000 0001 ...`) |
| `uri` | URI ISNI complète |
| `nom` | Nom |
| `prenom` | Prénom |
| `dates` | Dates (naissance-mort) |
| `role` | Rôles de création (codes MARC21 résolus) |
| `variantes` | Variantes du nom |
| `equivalences` | Liens vers des autorités bibliographiques |
| `sameas` | Liens `sameAs` (Wikidata, etc.) |

## Scoring

Les candidats sont scorés selon cinq niveaux :

| Score | Condition |
|---|---|
| 100 | Correspondance exacte avec le nom principal |
| 90 | Correspondance exacte avec une variante |
| 75 | Tous les mots de la requête présents dans le nom principal |
| 65 | Tous les mots de la requête présents dans une variante |
| 0–99 | Score Dice sur bigrammes (similarité textuelle) |

## Cache

Le cache est sauvegardé automatiquement à l'arrêt du service.

- **Exporter** — télécharge un fichier `isni_cache.zip` contenant les deux caches
- **Importer** — importer le fichier `isni_cache.zip` 
- **Vider** — efface le cache mémoire et disque

## Configuration

Interface de configuration disponible à l'adresse `http://127.0.0.1:5100/`
- **Résultats maximum** (1–10) : nombre de candidats retournés par requête
- **Seuil de score** (0–100) : score minimum pour qu'un candidat soit retourné

## Licence

MIT
