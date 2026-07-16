@echo off
set PGBIN=C:\Program Files\PostgreSQL\18\bin
set PGDATA_PROD=J:\Patent\dbms\pgdata\prod
set PGDATA_TWIN=J:\Patent\dbms\pgdata\twin
set PROD_PORT=5542
set TWIN_PORT=5543

echo Stopping twin PG18 (%TWIN_PORT%)...
"%PGBIN%\pg_ctl" stop -D "%PGDATA_TWIN%" -m fast 2>nul

echo Stopping production PG18 (%PROD_PORT%)...
"%PGBIN%\pg_ctl" stop -D "%PGDATA_PROD%" -m fast 2>nul

echo Done.
