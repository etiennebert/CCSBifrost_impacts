@echo off
REM ============================================================
REM Proxy-sector sensitivity: run the two unit-demand MATLAB
REM scripts (Full Leontief + Rank1) in batch mode.
REM Input : 5. MRIOs\2. Input Vektor\Sensitivity_Unit\Input_Vektor_Unit_USD.csv
REM Output: 5. MRIOs\4. Output\sensitivity_unit\2021_*_T_BIFROST_Unit_{Full,Rank1}_59_country.csv
REM Then run: python "6. Results\4. Sensitivity_Proxy\proxy_sensitivity.py"
REM ============================================================
setlocal
set "MATLAB_EXE=matlab"
set "SCRIPT_DIR=C:\Users\etber\OneDrive - Massachusetts Institute of Technology\Documents\CCS\5. MRIOs\3. Script\sensitivity_unit"
set "OUT_DIR=C:\Users\etber\OneDrive - Massachusetts Institute of Technology\Documents\CCS\5. MRIOs\4. Output\sensitivity_unit"
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

for %%S in (GLORIA_BIFROST_Unit_Full GLORIA_BIFROST_Unit_Rank1) do (
    echo [ %TIME% ] Running %%S.m ...
    "%MATLAB_EXE%" -batch "cd('%SCRIPT_DIR%'); run('%%S.m')" 1> "%OUT_DIR%\%%S.out.log" 2> "%OUT_DIR%\%%S.err.log"
    if errorlevel 1 (echo   FAILED: %%S.m  ^(see %OUT_DIR%\%%S.err.log^)) else (echo   OK    : %%S.m)
)
echo Done. Now run proxy_sensitivity.py
endlocal
