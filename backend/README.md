# Home Cash backend — phase 1
This is a read-only YNAB integration foundation. It does not post transactions or control hardware yet. The existing GitHub Pages demo is unchanged.

On the Raspberry Pi, clone the repository, enter backend, create a virtual environment, and install requirements:
```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
read -rs -p 'YNAB token: ' YNAB_TOKEN; echo
export YNAB_TOKEN
uvicorn main:app --host 127.0.0.1 --port 8000
```
Visit http://127.0.0.1:8000/docs locally or through an SSH tunnel. Do not expose this unauthenticated development server to the network. Use GET /api/ynab/budgets to find the budget ID, then set YNAB_BUDGET_ID before restarting. Use GET /api/ynab/accounts to find the cash account ID and set YNAB_CASH_ACCOUNT_ID before restarting. Never commit the token. Inventory starts at zero; do not interpret reconciliation as accurate until an initial count is implemented. Transaction writes, durable retry logic, authentication, frontend integration and hardware support are future phases.
