# Balise — agent d'information et d'orientation sur le handicap

**Balise** est un MVP d'agent conversationnel qui **informe et oriente** les
personnes en situation de handicap, leurs proches, et les professionnels
(médecins, ESMS, travailleurs sociaux…) — en France.

## Principe

- L'agent répond **uniquement** à partir des contenus publics des **centres de
  ressources** (organismes publics et associations reconnues). Ces centres
  tiennent lieu de base de connaissance (RAG) : Balise n'a **aucune**
  connaissance propre.
- L'agent **n'invente rien** : réflexion volontairement minimale, réponses
  factuelles strictes. Si l'information n'est pas trouvée, il dit
  **« je ne sais pas »** et oriente vers les bons interlocuteurs.
- **Chaque réponse cite ses sources** : document, centre ressource, lien.

## Centres ressources mobilisés

Du plus général au plus spécifique — publics et associations, c'est
l'information qui prime :

| # | Centre ressource | Type | Site |
|---|---|---|---|
| 1 | Service-Public.fr | Public | https://www.service-public.fr/ |
| 2 | MDPH en ligne (CNSA) | Public | https://mdphenligne.cnsa.fr/ |
| 3 | CNSA | Public | https://www.cnsa.fr/ |
| 4 | Annuaire des MDPH | Public | https://lannuaire.service-public.gouv.fr/navigation/maison_handicapees |
| 5 | GNCRA — centres ressources autisme | Public | https://maisondelautisme.gouv.fr/ |
| 6 | CReHPsy — handicap psychique | Public | https://centre-ressource-rehabilitation.org/ |
| 7 | CNRHR — handicaps rares | Public | https://cnrlapepiniere.fr/ |
| 8 | Communauté 360 (solidarites-sante.gouv.fr) | Public | https://solidarites-sante.gouv.fr/ |
| 9 | Unafam | Association | https://www.unafam.org/ |
| 10 | Autisme Info Service | Association | https://autismeinfoservice.fr/ |
| 11 | Nephou (polyhandicap) | Association | https://www.nephou.org/ |

Le site de chaque centre est interrogé **en direct et en parallèle** (un agent
par centre) ; le moteur de recherche interne du site sert d'index, les pages
trouvées servent de contexte au modèle.

## Utilisateurs

- **Famille / proche** — s'informer et s'orienter : droits, MDPH, aides, contacts.
- **Professionnel** (médecin, ESMS, coordonnateur) — compléter un manque
  d'information ou se renseigner : dispositifs, référentiels, modalités.

## Stack

| Couche | Techno |
|---|---|
| Front | HTML / CSS / Tailwind (Play CDN), JS vanilla |
| Back | Python 3.12, FastAPI, httpx |
| LLM | Mistral AI (`mistral-small-latest`), citations obligatoires |
| Déploiement | Docker + docker compose |

## Monorepo

```
backend/    FastAPI + agents de recherche parallèles + Mistral
frontend/   one-page chat statique
docker/     Dockerfile.back, Dockerfile.front, compose.yaml
.github/    CI minimale (lint + tests backend)
```

## Démarrage (dev)

```bash
# back
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
MISTRAL_API_KEY=sk-… .venv/bin/uvicorn app.main:app --port 8000 --reload

# front (autre terminal)
cd frontend
python3 -m http.server 8080
```

Ouvrir http://localhost:8080 (le front appelle l'API sur
`http://localhost:8000` en dev — réglable via `API_BASE` en tête de
`app.js`).

## Docker (machine distante)

```bash
docker compose -f docker/compose.yaml up -d --build
# front : http://<host>:3000 · API : http://<host>:8000
```

## Variables d'environnement

| Variable | Rôle |
|---|---|
| `MISTRAL_API_KEY` | clé API Mistral (requis pour `/api/chat`) |
| `CHAT_MODEL` | modèle de synthèse (défaut : `mistral-small-latest`) |

## CI minimale

Un seul workflow : lint (`ruff`) + tests pytest du backend, Linux uniquement.