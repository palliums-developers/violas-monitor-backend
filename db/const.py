HOST="127.0.0.1"
PORT="5007"
USER="postgres"
PASSWORD="monitor-postgres"
DATABASE="postgres"

dsn = f"postgres://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
