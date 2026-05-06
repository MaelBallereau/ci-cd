# Documentation GitLab CI

Ce projet utilise GitLab CI pour automatiser les controles de qualite, les tests, le test HTTP de l'API, la construction Docker et une etape de deploiement simulee.

Le pipeline est defini dans le fichier `.gitlab-ci.yml`.

## Declenchement du pipeline

Le pipeline GitLab est lance dans deux cas :

- lorsqu'un commit est pousse sur la branche `main`
- lorsqu'une merge request cible la branche `main`

La section responsable est :

```yaml
workflow:
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
    - if: '$CI_MERGE_REQUEST_TARGET_BRANCH_NAME == "main"'
```

Cela permet d'avoir un comportement proche du workflow GitHub Actions du projet.

## Image de base

Par defaut, les jobs utilisent l'image Docker suivante :

```yaml
image: python:3.12
```

Elle fournit Python 3.12 pour installer les dependances, lancer Ruff, pip-audit, pytest et Uvicorn.

Le job Docker utilise une autre image :

```yaml
image: docker:latest
```

car il doit executer la commande `docker build`.

## Ordre des stages

Les stages sont executes dans cet ordre :

```yaml
stages:
  - lint
  - audit
  - test
  - api-test
  - docker-build
  - deploy
```

GitLab execute les jobs stage par stage. Si un stage echoue, les stages suivants ne sont pas executes.

## Cache pip

Le pipeline met en cache le dossier `.cache/pip` :

```yaml
cache:
  paths:
    - .cache/pip
```

Ce cache peut accelerer les installations Python entre deux pipelines.

## Stage `lint`

Le job `lint` verifie la qualite du code avec Ruff.

Il fait les actions suivantes :

1. met `pip` a jour
2. installe les dependances du projet depuis `requirements.txt`
3. installe `ruff`
4. lance `ruff check .`

Commande principale :

```bash
ruff check .
```

Si Ruff detecte une erreur de style ou une erreur statique, le job echoue.

## Stage `audit`

Le job `audit` analyse les dependances Python avec `pip-audit`.

Il fait les actions suivantes :

1. met `pip` a jour
2. installe les dependances du projet
3. installe `pip-audit`
4. lance l'audit de securite

Commande principale :

```bash
pip-audit --ignore-vuln CVE-2025-54121 --ignore-vuln CVE-2025-62727
```

Les deux CVE ignorees correspondent a des alertes Starlette deja gerees par la configuration actuelle du projet. Si les dependances sont mises a jour et que ces exceptions ne sont plus necessaires, elles peuvent etre retirees.

## Stage `test`

Le job `test` lance les tests automatises Python avec `pytest`.

Il fait les actions suivantes :

1. met `pip` a jour
2. installe les dependances du projet
3. installe `pytest`
4. lance les tests

Commande principale :

```bash
pytest
```

Si un test echoue, le pipeline s'arrete avant le test API, le build Docker et le deploiement.

## Stage `api-test`

Le job `api-curl-test` verifie que l'API FastAPI demarre correctement et repond a des requetes HTTP reelles.

Il installe d'abord `curl`, car l'image `python:3.12` ne le fournit pas toujours :

```yaml
before_script:
  - apt-get update
  - apt-get install -y curl
  - python -m pip install --upgrade pip
  - pip install -r requirements.txt
```

Ensuite, il demarre l'application avec Uvicorn :

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 &
API_PID=$!
trap 'kill "$API_PID"' EXIT
```

Le `&` lance le serveur en arriere-plan. La variable `API_PID` garde l'identifiant du processus. Le `trap` arrete automatiquement Uvicorn a la fin du job, meme si une commande echoue.

Le job attend ensuite que l'API soit prete :

```bash
for i in $(seq 1 30); do
  if curl --fail --silent http://127.0.0.1:8000/ > /tmp/root.json; then
    break
  fi
  sleep 1
done
```

Cette boucle essaie pendant 30 secondes maximum d'appeler la route `/`.

Puis le job teste plusieurs endpoints :

```bash
curl --fail --silent http://127.0.0.1:8000/
```

Teste la route racine.

```bash
curl --fail --silent \
  -X POST http://127.0.0.1:8000/items \
  -H "Content-Type: application/json" \
  -d '{"name":"pipeline-test","price":9.99}' \
  --output /tmp/item.json
```

Cree un item dans l'API.

```bash
curl --fail --silent http://127.0.0.1:8000/items/1
```

Verifie que l'item cree peut etre relu.

L'option `--fail` fait echouer `curl` si l'API retourne une erreur HTTP comme `404` ou `500`.

## Stage `docker-build`

Le job `docker-build-job` construit l'image Docker de l'application :

```bash
docker build -t mon-app:latest .
```

Ce job utilise Docker-in-Docker :

```yaml
services:
  - docker:dind
variables:
  DOCKER_HOST: tcp://docker:2375
  DOCKER_TLS_CERTDIR: ""
```

Important : le runner GitLab doit generalement etre configure en mode `privileged` pour que `docker:dind` fonctionne.

Exemple de configuration runner :

```toml
[runners.docker]
  privileged = true
```

Sans cette configuration, le job Docker peut echouer meme si le `Dockerfile` est correct.

## Stage `deploy`

Le job `deploy-job` est actuellement une simulation :

```bash
echo "Deploiement de l'application"
echo "Image Docker prete a etre deployee"
```

Il ne publie pas encore l'image Docker et ne deploie pas sur un serveur reel. Il sert de point d'extension pour ajouter plus tard un vrai deploiement.

## Resume du pipeline

Le pipeline suit ce parcours :

1. `lint` verifie le code avec Ruff
2. `audit` verifie les vulnerabilites Python
3. `test` lance les tests unitaires avec pytest
4. `api-curl-test` demarre l'API et la teste avec curl
5. `docker-build-job` construit l'image Docker
6. `deploy-job` simule le deploiement

Si une etape echoue, GitLab stoppe les etapes suivantes. Cela evite de construire ou deployer une application qui n'a pas passe les controles.

## Commandes utiles en local

Pour reproduire une partie du pipeline localement :

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install ruff pytest pip-audit
ruff check .
pytest
pip-audit --ignore-vuln CVE-2025-54121 --ignore-vuln CVE-2025-62727
```

Pour tester l'API localement avec `curl` :

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
curl --fail http://127.0.0.1:8000/
curl --fail -X POST http://127.0.0.1:8000/items \
  -H "Content-Type: application/json" \
  -d '{"name":"local-test","price":9.99}'
curl --fail http://127.0.0.1:8000/items/1
```
