# Spam Shield

A full-stack web app that checks emails for spam using a Hugging Face transformer model. Users create an account, paste an email or upload `.eml` files, and get a verdict with a confidence score. Every check is saved to their private history.

## Features

- **Paste and check:** classify the text of a single email
- **Bulk upload:** check up to 20 `.eml` files at once, with one error per bad file instead of a failed batch
- **Accounts:** register, log in and log out with secure server-side sessions
- **Private history:** each user sees only their own last 50 results
- **REST API:** interactive documentation at `/docs`

## Tech stack

| Area | Tools |
| --- | --- |
| Backend | Python, FastAPI, Pydantic |
| Machine learning | Hugging Face Transformers, PyTorch, BERT-tiny |
| Database | PostgreSQL, SQLAlchemy 2.0 |
| Authentication | bcrypt, session cookies |
| Frontend | HTML, CSS, JavaScript |
| Testing | pytest, FastAPI TestClient |

## How it works

```mermaid
flowchart LR
    B[Browser] <-->|JSON and cookie| F[FastAPI server]
    F <-->|predict| M[Hugging Face model]
    F <-->|SQL| D[(PostgreSQL)]
```

The browser only talks to the FastAPI server. For each request, the server checks the session, validates the input, runs the model and saves the result. The model is loaded once at startup, so requests don't pay that cost.

## Project structure

```text
app/
  main.py           App setup and prediction routes
  auth.py           Register, login, logout and sessions
  model.py          Wrapper around the Hugging Face model
  email_parser.py   Extracts the subject and text from .eml files
  schemas.py        Request and response validation
  db.py             Database connection
  db_models.py      Database tables
static/             Web pages, styles and browser JavaScript
tests/              Automated tests
```

## Getting started

You need Python 3.9 or newer (tested on 3.9) and a running PostgreSQL server.

```bash
git clone https://github.com/aviral112op/spam-shield.git
cd spam-shield

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

createdb -U postgres spam_detector
cp .env.example .env
```

Edit `.env` and set `DATABASE_URL` to your PostgreSQL details, then start the server:

```bash
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000> for the app, or <http://127.0.0.1:8000/docs> for the API documentation. The model downloads automatically on the first run.

## Configuration

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | Yes | PostgreSQL connection address |
| `COOKIE_SECURE` | No | Set to `true` when serving over HTTPS |
| `SESSION_DAYS` | No | Days a login lasts (default 7) |
| `MODEL_NAME` | No | Hugging Face model to use |

## API

| Method and path | Login needed | Purpose |
| --- | --- | --- |
| `POST /auth/register` | No | Create an account and log in |
| `POST /auth/login` | No | Log in |
| `POST /auth/logout` | No | Log out |
| `GET /auth/me` | Yes | Get the current user |
| `POST /predict` | Yes | Classify one email |
| `POST /predict/batch` | Yes | Classify up to 100 emails |
| `POST /predict/eml` | Yes | Classify up to 20 `.eml` files |
| `GET /history` | Yes | Get your last 50 results |
| `GET /health` | No | Check the server and model status |

Example response from `POST /predict`:

```json
{"label": "ham", "is_spam": false, "confidence": 0.9362}
```

## Security

- Passwords are hashed with bcrypt and are never stored in plain text
- Session tokens are random, and only their SHA-256 hashes are stored
- Session cookies are `HttpOnly` and `SameSite=Lax`, with `Secure` available for HTTPS
- Every history query is limited to the logged-in user
- Email content is displayed as plain text in the browser, which prevents script injection

## Testing

The tests replace the real model with a fake one, so they run quickly and offline. They delete all tables in the database they use, so always give them a separate database, never your real one.

```bash
pip install -r requirements-dev.txt
createdb -U postgres spam_detector_test
TEST_DATABASE_URL='postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/spam_detector_test' pytest -v
```

## Known limitations

- **Model accuracy:** the default model is tuned for SMS messages and is built to be small, so it misses some obvious email spam. In a small manual check, it labelled "Claim your prize now" as not spam with 92.9% confidence. Treat its results as a demonstration, not a reliable filter.
- **Database changes:** tables are created at startup, and there are no migrations yet.
- **Login protection:** login attempts aren't rate limited yet, so add this before deploying publicly.

## Planned improvements

- [ ] Evaluate models on real emails with precision and recall, and switch to a better one
- [ ] Handle simultaneous sign-ups with the same email cleanly
- [ ] Add login rate limiting and database migrations with Alembic
- [ ] Add Docker and automated test runs with GitHub Actions
