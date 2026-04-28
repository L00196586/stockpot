# StockPot

A smart inventory management system and recipe engine built with Django and Django REST Framework.

StockPot helps users manage their food inventory and reduce waste by tracking what they have at home and suggesting recipes based on available ingredients. Rather than searching for a recipe and then buying ingredients, StockPot analyses the user's pantry and proposes a menu accordingly.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Running Tests](#running-tests)
- [Code Quality](#code-quality)
- [CI Pipeline](#ci-pipeline)

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, Django 5.0, Django REST Framework 3.15 |
| Database | PostgreSQL 16 |
| Containerisation | Docker, Docker Compose |
| CI/CD | GitHub Actions |
| Web server | Gunicorn |

---

## Project Structure

```
stockpot/
├── .github/
│   ├── workflows/
│   │   └── ci.yml              # CI pipeline (lint → test → build)
│   ├── dependabot.yml          # Automated dependency updates
│   └── pull_request_template.md
├── pantry/                     # Inventory management app
│   ├── migrations/
│   ├── tests/
│   │   ├── test_models.py
│   │   ├── test_serializers.py
│   │   └── test_views.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py               # Ingredient, StockItem
│   ├── serializers.py
│   ├── urls.py
│   └── views.py
├── stockpot/                   # Django project settings
│   ├── settings.py
│   └── urls.py
├── .env.example                # Environment variable template
├── .flake8                     # Linter configuration
├── docker-compose.yml
├── Dockerfile
├── manage.py
├── pytest.ini
├── requirements.txt
└── requirements-dev.txt
```

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/)

### 1. Clone the repository

```bash
git clone https://github.com/your-username/stockpot.git
cd stockpot
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your preferred values (the defaults work out of the box for local development).

### 3. Start the application

```bash
docker compose up --build
```

This starts two services:

| Service | URL |
|---------|-----|
| Django API | http://localhost:8000 |
| PostgreSQL | localhost:5432 |

### 4. Apply database migrations

```bash
docker compose run --rm web python manage.py migrate
```

### 5. Create a superuser (optional)

```bash
docker compose run --rm web python manage.py createsuperuser
```

The Django admin panel is available at http://localhost:8000/admin/.

---

## Environment Variables

All variables are loaded from the `.env` file via [`python-decouple`](https://pypi.org/project/python-decouple/). Copy `.env.example` to `.env` to get started.

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | `django-insecure-...` |
| `DEBUG` | Enable debug mode | `True` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1` |
| `DB_NAME` | PostgreSQL database name | `stockpot` |
| `DB_USER` | PostgreSQL username | `stockpot` |
| `DB_PASSWORD` | PostgreSQL password | `stockpot` |
| `DB_HOST` | Database host | `db` |
| `DB_PORT` | Database port | `5432` |

---

## API Reference

All endpoints require authentication. Session-based authentication is used — log in via the browsable API at `/api-auth/login/`.

### Ingredients

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/ingredients/` | List all ingredients. Supports `?search=<name>` |
| `POST` | `/api/ingredients/` | Create a new ingredient |

**Ingredient object**

```json
{
  "id": 1,
  "name": "Flour",
  "unit": "g"
}
```

Supported units: `g`, `kg`, `ml`, `L`, `pcs`, `tbsp`, `tsp`, `cup`

---

### Pantry (Stock Items)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/stock/` | List the authenticated user's pantry |
| `POST` | `/api/stock/` | Add an ingredient to the pantry |
| `GET` | `/api/stock/<id>/` | Retrieve a single pantry item |
| `PUT` | `/api/stock/<id>/` | Replace a pantry item |
| `PATCH` | `/api/stock/<id>/` | Partially update a pantry item |
| `DELETE` | `/api/stock/<id>/` | Remove an item from the pantry |

**Stock item object (response)**

```json
{
  "id": 1,
  "ingredient": {
    "id": 1,
    "name": "Flour",
    "unit": "g"
  },
  "quantity": "500.00",
  "expiry_date": "2027-06-01",
  "created_at": "2026-04-08T09:00:00Z",
  "updated_at": "2026-04-08T09:00:00Z"
}
```

**Stock item request body (POST / PUT / PATCH)**

```json
{
  "ingredient_id": 1,
  "quantity": "500.00",
  "expiry_date": "2027-06-01"
}
```

`expiry_date` is optional.

---

## Running Tests

The test suite uses **pytest** with **pytest-django** and covers models, serializers, and API views (73 tests).

### Run all tests

```bash
docker compose run --rm web pytest
```

### Run with coverage report

```bash
docker compose run --rm web pytest --cov=. --cov-report=term-missing
```

> The CI pipeline enforces a minimum coverage of **80 %**. The build will fail if this threshold is not met.

### Run a specific test file

```bash
docker compose run --rm web pytest pantry/tests/test_views.py
```

---

## Code Quality

### Linting (Flake8)

```bash
docker compose run --rm web flake8 .
```

### Security scanning (Bandit)

```bash
docker compose run --rm web bandit -r . --exclude ./pantry/migrations,./pantry/tests,./local_files -ll
```

### Install dev dependencies

```bash
docker compose run --rm web pip install -r requirements-dev.txt
```

---

## CI Pipeline

Every pull request targeting `main` runs the following jobs in parallel:

| Job | Tool | Gate |
|-----|------|------|
| Python Lint | Flake8 | PEP 8 compliance |
| Frontend Lint | ESLint | JavaScript style (skipped if no JS files present) |
| Security Scan | Bandit | Medium+ severity vulnerabilities |
| Tests & Coverage | pytest + pytest-cov | All tests pass, coverage ≥ 80 % |

Once all four gates pass, a sequential **Docker build** job pushes the verified image to the GitHub Container Registry, tagged with the commit SHA, and generates an SBOM artefact.

Merging to `main` is blocked until every gate is green and at least one peer review approval has been given.
