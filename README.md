# Balise — information et orientation sur le handicap

**Balise** est un MVP d’agent conversationnel qui informe et oriente, en France,
les personnes en situation de handicap, leurs proches et les professionnels
(médecins, ESMS, travailleurs sociaux…). Il ne remplace ni une évaluation
médicale ou sociale, ni une décision administrative ou juridique.

## Garantie de grounding

Balise ne doit afficher que des éléments soutenus par les documents autorisés :

- chaque paragraphe, étape et contact doit référencer au moins une source
  réellement affichée ;
- chaque élément doit fournir au serveur un extrait littéral présent dans le
  document cité ;
- le serveur vérifie aussi un recouvrement lexical entre l’affirmation et ses
  extraits ;
- les marqueurs de citation libres produits par le modèle sont supprimés, puis
  les marqueurs vérifiés et les URL sont ajoutés par le serveur ;
- un document live est rejeté si son URL finale, après redirection, sort de
  l’allowlist ;
- en l’absence de preuve suffisante, la réponse échoue de façon fermée :
  `unknown: true`, sans texte, action ou contact ajouté par défaut.

## Architecture A/B isolée

```text
question + contexte déclaré
          │
          ▼
A — planificateur Mistral isolé
    compréhension / synonymes / requêtes uniquement
          │
          ├── corpus vérifié
          ├── index CASF local (DILA/LEGI)
          ├── annuaire FINESS si pertinent
          └── recherche live sur domaines autorisés
                         │
                         ▼
                 filtre d’allowlist
                         │
                         ▼
B — synthétiseur Mistral dans un contexte neuf
    question + profil de présentation + documents autorisés
                         │
                         ▼
contrôle littéral + recouvrement lexical + citations serveur
```

Le contenu libre produit par A n’est jamais transmis à B : seules ses requêtes
pilotent la recherche. B ne reçoit ni plan d’action ni fait du planificateur.
L’historique des réponses de l’assistant n’est jamais réinjecté ; seuls les
messages utilisateur récents peuvent servir à comprendre une relance. Les
profils `famille` et `pro`, ainsi que le mode FALC, changent la présentation,
mais ne créent aucune nouvelle source de faits.

## Sources autorisées

Le registre effectif est `backend/app/ressources.py`. Les corpus locaux gardent
leurs identifiants de routage, mais leurs URL doivent appartenir à l’un de ces
domaines. Toute autre origine est rejetée avant la synthèse.

| Source | Type | Domaine de référence |
|---|---|---|
| Légifrance — CASF | Public | `legifrance.gouv.fr` |
| FINESS | Public | `finess.esante.gouv.fr`, `data.gouv.fr` |
| Service-Public.fr | Public | `service-public.fr`, `service-public.gouv.fr` |
| MDPH en ligne (CNSA) | Public | `mdphenligne.cnsa.fr` |
| CNSA | Public | `cnsa.fr` |
| GNCRA / Maison de l’autisme | Public | `maisondelautisme.gouv.fr` |
| CReHPsy | Public | `centre-ressource-rehabilitation.org` |
| CNRHR | Public | `cnrlapepiniere.fr` |
| Annuaire des MDPH | Public | `lannuaire.service-public.gouv.fr` |
| Unafam | Association | `unafam.org` |
| Autisme Info Service | Association | `autismeinfoservice.fr` |
| Nephou | Association | `nephou.org` |
| HAS | Public | `has-sante.fr` |
| Agence de la biomédecine — Génétique médicale | Public | `genetique-medicale.fr` |
| Filières de santé maladies rares | Public | `filieresmaladiesrares.fr` |
| Maladies Rares Info Services | Association | `maladiesraresinfo.org` |
| Agefiph | Association | `agefiph.fr`, `espace-emploi.agefiph.fr` |
| Ministère chargé du handicap | Public | `handicap.gouv.fr` |
| Mon parcours handicap | Public | `monparcourshandicap.gouv.fr` |
| FFDys | Association | `ffdys.com` |
| APF France handicap | Association | `apf-francehandicap.org` |
| Unapei | Association | `unapei.org` |
| Psycom | Association | `psycom.org` |
| Communauté 360 | Public | `solidarites-sante.gouv.fr` |

La MDPH et la Communauté 360 ne sont pas proposées par défaut : elles ne
peuvent apparaître que si un extrait autorisé les rend pertinentes pour la
question. Le corpus vérifié inclut notamment la page HAS consacrée au protocole
national de diagnostic et de soins de la sclérose latérale amyotrophique.[2]

## Snapshot CASF

`backend/data/casf_index.json` est un index compact du Code de l’action sociale
et des familles, construit hors ligne depuis les archives ouvertes LEGI de la
DILA.[1] Le snapshot livré est arrêté au **2026-09-15** :

| Métadonnée | Valeur |
|---|---:|
| Identifiant du code | `LEGITEXT000006074069` |
| Articles courants | `3 659` |
| État des articles | `VIGUEUR` |
| Archives manifestées | `432` (1 stock + 431 différentiels) |
| Dernier différentiel | `LEGI_20260915-211944.tar.gz` |
| Taille de l’index | `6 318 461` octets |
| SHA-256 de l’index | `7caa6556f47aa4c306eca865336e17c7f31bbdc56678a4a9a4e0506113c1874f` |

Le manifeste embarque le nom, l’URL, le SHA-256 et les compteurs d’application
de chaque archive. L’index conserve le texte complet des articles : aucune
coupe n’est appliquée pendant la construction. À l’exécution, la recherche
lexicale sélectionne un passage de phrases complètes de `1 800` caractères au
maximum pour limiter le contexte envoyé au modèle.

### Reconstruction reproductible

Le stock utilisé est `Freemium_legi_global_20250713-140000.tar.gz`. Les archives
volumineuses restent dans `/tmp` et ne doivent pas être committées.

```bash
cd backend

curl -fL \
  https://echanges.dila.gouv.fr/OPENDATA/LEGI/Freemium_legi_global_20250713-140000.tar.gz \
  -o /tmp/legi-global.tar.gz

.venv/bin/python scripts/download_legi_deltas.py \
  --after 20250713-140000 \
  --as-of 2026-09-15 \
  --out /tmp/legi-deltas

.venv/bin/python scripts/build_casf_index.py \
  /tmp/legi-global.tar.gz \
  --deltas-dir /tmp/legi-deltas \
  --as-of 2026-09-15 \
  --out data/casf_index.json
```

Contrôles rapides :

```bash
.venv/bin/python -m pytest tests/test_casf.py tests/test_casf_build.py -q
.venv/bin/python -c \
  'from app.casf import search; print(search(["article D. 312-162"]))'
```

## Limites

- Le registre autorisé n’est pas une garantie d’exhaustivité. Un site
  indisponible, une recherche interne médiocre ou un document non indexé peut
  conduire à `unknown`.
- Le snapshot CASF reflète les archives disponibles au 2026-09-15. Pour une
  situation juridique réelle, vérifier le texte consolidé courant sur
  Légifrance.
- La recherche CASF est lexicale, pas une interprétation juridique.
- Les coordonnées FINESS et les pages live peuvent évoluer après leur lecture.
- Le contrôle littéral réduit les hallucinations sans prouver qu’une source est
  complète, à jour ou applicable au cas individuel.
- Balise ne pose pas de diagnostic, ne prescrit pas de traitement et ne prend
  pas de décision à la place des organismes compétents.

## Stack

| Couche | Technologie |
|---|---|
| Front | HTML, CSS/Tailwind (Play CDN), JavaScript vanilla |
| Back | Python 3.12, FastAPI, httpx |
| LLM | Mistral AI : planificateur A puis synthétiseur B isolé |
| Données locales | corpus vérifié + index CASF JSON |
| Exécution | Docker / Docker Compose |

## Monorepo

```text
backend/          API, planificateur, recherche, synthèse et tests
backend/data/     corpus et index compacts embarqués
backend/scripts/  reconstruction des index
frontend/         chat statique
docker/           images, nginx et Compose
.github/          CI lint + tests
```

## Démarrage local

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
MISTRAL_API_KEY=sk-… .venv/bin/uvicorn app.main:app --port 8000 --reload

# autre terminal
cd frontend
python3 -m http.server 8080
```

Ouvrir `http://localhost:8080`. Le frontend appelle l’API locale configurée par
`API_BASE` dans `frontend/app.js`.

## Variables d’environnement

| Variable | Rôle |
|---|---|
| `MISTRAL_API_KEY` | clé requise pour `/api/chat` |
| `PLANNER_MODEL` | modèle de l’étape A (défaut : `mistral-medium-latest`) |
| `CHAT_MODEL_SMALL` | synthèse à effort `small` |
| `CHAT_MODEL_MEDIUM` | synthèse à effort `medium` |
| `CHAT_MODEL_LARGE` | synthèse à effort `large` |
| `CORS_ALLOW_ORIGINS` | origines CORS, séparées par des virgules |
| `LOG_LEVEL` | niveau de logs backend |

## Qualité

```bash
cd backend
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest -q
node --check ../frontend/app.js
```

### Validation réelle Mistral (hors CI)

```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/e2e_grounding.py \
  --env-file ../docker/.env --output-dir /tmp/balise-grounding --repeats 2
```

Ce test consomme des appels API réels. Il ne tourne pas dans la CI. Il couvre
le scénario professionnel global, une famille, un autre sujet nommé et les
modes de lecture simplifiée famille/professionnel. Chaque exécution conserve
le plan privé, les documents retenus, les réponses brutes du modèle et la sortie
validée dans un fichier JSON distinct. `report.json` contient les contrôles
agrégés ; une réponse manquante ou un contrôle échoué donne un code de sortie
non nul. Utiliser `--scenario <nom>` pour rejouer un cas isolé.

Les contrôles de longueur ne certifient pas une conformité FALC : une relecture
humaine reste nécessaire pour l'accessibilité et l'applicabilité des informations.

## Sources

[1] https://echanges.dila.gouv.fr/OPENDATA/LEGI — DILA — archives ouvertes LEGI
[2] https://www.has-sante.fr/jcms/c_2573383/fr/sclerose-laterale-amyotrophique — HAS — Sclérose latérale amyotrophique
