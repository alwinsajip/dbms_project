@echo off
set PGBIN=C:\Program Files\PostgreSQL\18\bin
set PGDATA_PROD=C:\Patent\dbms\pgdata\prod
set PGDATA_TWIN=C:\Patent\dbms\pgdata\twin
set PROD_PORT=5542
set TWIN_PORT=5543

echo Initializing production PG18 instance on port %PROD_PORT%...
if not exist "%PGDATA_PROD%\postgresql.conf" (
    "%PGBIN%\initdb" -D "%PGDATA_PROD%" -E UTF8 --locale="C" --username=postgres --auth=trust
    echo port = %PROD_PORT% >> "%PGDATA_PROD%\postgresql.conf"
    echo shared_preload_libraries = 'pg_stat_statements' >> "%PGDATA_PROD%\postgresql.conf"
    echo pg_stat_statements.max = 10000 >> "%PGDATA_PROD%\postgresql.conf"
    echo pg_stat_statements.track = all >> "%PGDATA_PROD%\postgresql.conf"
    echo listen_addresses = 'localhost' >> "%PGDATA_PROD%\postgresql.conf"
)

echo Starting production PG18...
"%PGBIN%\pg_ctl" start -D "%PGDATA_PROD%" -l "%PGDATA_PROD%\logfile" -w -t 30 -o "-p %PROD_PORT%" 2>nul

echo Creating sedbms database...
"%PGBIN%\psql" -U postgres -h localhost -p %PROD_PORT% -c "CREATE DATABASE sedbms_prod;" 2>nul
"%PGBIN%\psql" -U postgres -h localhost -p %PROD_PORT% -d sedbms_prod -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;" 2>nul

echo Initializing twin PG18 instance on port %TWIN_PORT%...
if not exist "%PGDATA_TWIN%\postgresql.conf" (
    "%PGBIN%\initdb" -D "%PGDATA_TWIN%" -E UTF8 --locale="C" --username=postgres --auth=trust
    echo port = %TWIN_PORT% >> "%PGDATA_TWIN%\postgresql.conf"
    echo listen_addresses = 'localhost' >> "%PGDATA_TWIN%\postgresql.conf"
)

echo Starting twin PG18...
"%PGBIN%\pg_ctl" start -D "%PGDATA_TWIN%" -l "%PGDATA_TWIN%\logfile" -w -t 30 -o "-p %TWIN_PORT%" 2>nul

echo Done. Both PG18 instances should be running.
"%PGBIN%\pg_isready" -h localhost -p %PROD_PORT%
"%PGBIN%\pg_isready" -h localhost -p %TWIN_PORT%
