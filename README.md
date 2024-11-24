# grant_search

## To Run locally:
### Setup environment
1. create a virtual env `.venv` under the root directory:
`python3 -m venv .venv`
2. active that virtual env:
`./.venv/bin/activate`
3. create a `.env` file. It should look like:
```
FLASK_SECRET_KEY=809j439rj834f
SECRETS_KEY=[KEY TO DECRYPT client_secrets.json.encrypt]
HEROKU_LOCAL=1
POSTGRES_URL=[Postgres URL from neon]
```

### To run:
1. start Heroku:
`heroku local -f Procfile.local`
2. start local next.js:
`cd grant_search-frontend && npm run dev`


## Updating dependencies
Install new Python deps with: `pip install XXXX`
After that update the requirements.txt: `pip freeze -> requirements.txt`

NPM works similarly: `npm install XXXX`
NPM automatically updates `package.json` and `package.json.lock`
Note that on Heroky none of the "development" dependencies are installed, so if they are needed for next.js compilation make sure to include them in the main dependencies.

### Database upgrades
TO reset the DB:
`python -m grant_search.db.reset`

To create an upgrade script:
`alembic revision --autogenerate -m "UPGRADE DESCRIPTION"`

To upgrade:
`alembic upgrade head`

