@echo off
echo ========================================
echo  SEDBMS - Running All Test Suites
echo ========================================
echo.
cd /d "%~dp0.."

echo 1. Unit Tests
echo ------------
py -3.12 -m pytest tests/unit -v --tb=short
if %ERRORLEVEL% neq 0 (
    echo FAILED: Unit tests
    exit /b 1
)
echo.

echo 2. Scenario Tests (Patent Evidence)
echo -----------------------------------
py -3.12 -m pytest tests/scenarios -v --tb=short
if %ERRORLEVEL% neq 0 (
    echo FAILED: Scenario tests
    exit /b 1
)
echo.

echo 3. All Tests Combined
echo --------------------
py -3.12 -m pytest tests/unit tests/scenarios -v --tb=short --junitxml=patent\evidence_appendix\test_results.xml
if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================
    echo  ALL TESTS PASSED
    echo ========================================
)
echo.
echo Results saved to patent\evidence_appendix\test_results.xml
pause
