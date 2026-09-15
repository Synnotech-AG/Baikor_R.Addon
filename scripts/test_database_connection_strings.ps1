# Requires PowerShell 7, Python with Jinja2/PyYAML, and Npgsql.dll from a built app.
# Renders the actual Ansible Secret templates with synthetic credentials only.
# Does not connect to PostgreSQL or modify any Kubernetes resources.
param(
    [Parameter(Mandatory)]
    [string] $NpgsqlAssemblyPath,
    [string] $PythonExecutable = 'python'
)

$ErrorActionPreference = 'Stop'
[System.Reflection.Assembly]::LoadFrom((Resolve-Path $NpgsqlAssemblyPath).Path) | Out-Null
$templatePath = Join-Path $PSScriptRoot '../tasks/baikor_r/database.yml'
$renderCases = @'
import base64
import json
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, StrictUndefined

environment = Environment(undefined=StrictUndefined)
environment.filters['b64decode'] = lambda value: base64.b64decode(value).decode('utf-8')
tasks = yaml.safe_load(Path(sys.argv[1]).read_text(encoding='utf-8'))
templates = [
    task['kubernetes.core.k8s']['definition']['stringData']['connectionString']
    for task in tasks
    if 'connectionString' in task.get('kubernetes.core.k8s', {}).get('definition', {}).get('stringData', {})
]
assert len(templates) == 2, 'Expected application and migration connection string templates'
values = [
    'ordinary-value',
    'Example;Password=other',
    'Example;SSL Mode=Disable;Host=untrusted',
    'double"quote',
    "single'quote",
    'both\'"quotes;equals=backslash\\',
    '  leading and trailing spaces  ',
    'umlauts-äöü-€',
    'line\nbreak\r\nend',
]
cases = []
for index, value in enumerate(values):
    encoded = base64.b64encode(value.encode('utf-8')).decode('ascii')
    credentials = {'resources': [{'data': {'username': encoded, 'password': encoded}}]}
    for ca_secret in ['', 'database-ca']:
        context = {
            'inv_addons': {'baikor_r': {'database': {
                'host': value, 'port': 5432, 'name': value,
                'ssl_mode': 'VerifyFull', 'trust_server_certificate': False,
                'ca_secret': ca_secret,
            }}},
            'baikor_database_application_credentials': credentials,
            'baikor_database_migration_credentials': credentials,
        }
        for role, template in zip(['application', 'migration'], templates):
            cases.append({
                'name': f'{role}-{index}-ca={bool(ca_secret)}',
                'expected': value,
                'rootCertificate': '/etc/baikor/database-ca/ca.crt' if ca_secret else '',
                'connectionString': environment.from_string(template).render(context),
            })
print(json.dumps(cases))
'@

$rendered = & $PythonExecutable -c $renderCases $templatePath
if ($LASTEXITCODE -ne 0) { throw 'Could not render connection-string test cases.' }
$cases = ($rendered -join "`n") | ConvertFrom-Json
foreach ($case in $cases) {
    $parsed = [Npgsql.NpgsqlConnectionStringBuilder]::new($case.connectionString)
    foreach ($property in @('Host', 'Database', 'Username', 'Password')) {
        if ($parsed.$property -cne $case.expected) {
            throw "Connection-string round trip failed: $($case.name), $property."
        }
    }
    if ($parsed.Port -ne 5432 -or $parsed.SslMode.ToString() -ne 'VerifyFull') {
        throw "Connection-string settings were overwritten: $($case.name)."
    }
    if ([string]$parsed.RootCertificate -cne $case.rootCertificate) {
        throw "Unexpected CA configuration: $($case.name)."
    }
}
Write-Output "PASS: $($cases.Count) rendered connection strings preserve credentials and TLS settings."
