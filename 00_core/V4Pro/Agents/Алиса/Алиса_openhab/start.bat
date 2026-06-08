@echo off

echo Launching the openHAB runtime...

setlocal
set DIRNAME=%~dp0%
set JAVA_OPTS=%JAVA_OPTS% -Dorg.osgi.service.http.port=8081

IF [%OPENHAB_RUNTIME%]==[] (
	set RUNTIME=%DIRNAME%\runtime
) ELSE (
	set RUNTIME=%OPENHAB_RUNTIME%
)
"%RUNTIME%\bin\karaf.bat" %*
