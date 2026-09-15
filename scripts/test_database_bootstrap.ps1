param(
    [string] $Namespace = 'tst-database-stack',
    [string] $DatabasePod = 'baikor-r-db-0'
)
$ErrorActionPreference = 'Stop'
# Only synthetic resources with a unique prefix are created or removed.
$database = 'baikor_test_' + [Guid]::NewGuid().ToString('N').Substring(0, 10)
$jobName = $database.Replace('_', '-')
$roles = @("${database}_owner", "${database}_writer", "${database}_publisher")
$source = kubectl -n $Namespace get job baikor-r-database-bootstrap -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Deploy the addon bootstrap job before running this test.' }
$source.metadata = @{name=$jobName; namespace=$Namespace}
$source.PSObject.Properties.Remove('status')
$source.spec.PSObject.Properties.Remove('selector')
$source.spec.template.metadata = @{}
$container = $source.spec.template.spec.containers[0]
$loginSecret = @{apiVersion='v1';kind='Secret';metadata=@{name=$jobName;namespace=$Namespace};type='Opaque';stringData=@{}}
foreach ($entry in $container.env) {
    if ($entry.name -eq 'BAIKOR_DATABASE') { $entry.value = $database }
    if ($entry.name -match '^BAIKOR_(OWNER|WRITER|PUBLISHER)(_PASSWORD)?$') {
        $roleIndex = @('OWNER','WRITER','PUBLISHER').IndexOf($Matches[1])
        $value = if ($Matches[2]) { [Guid]::NewGuid().ToString('N') } else { $roles[$roleIndex] }
        $loginSecret.stringData[$entry.name] = $value
        $entry.valueFrom.secretKeyRef.name = $jobName
        $entry.valueFrom.secretKeyRef.key = $entry.name
    }
}
try {
    $loginSecret | ConvertTo-Json -Depth 20 | kubectl apply -f - | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Cannot create temporary credentials.' }
    foreach ($run in 1..2) {
        $source | ConvertTo-Json -Depth 40 | kubectl apply -f - | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Cannot create bootstrap test job.' }
        kubectl -n $Namespace wait --for=condition=complete "job/$jobName" --timeout=120s
        if ($LASTEXITCODE -ne 0) { throw "Bootstrap test run $run failed." }
        kubectl -n $Namespace delete job $jobName --wait=true | Out-Null
    }
    $actual = kubectl -n $Namespace exec $DatabasePod -- psql -U postgres -d $database -Atc "SELECT count(*) FROM pg_extension WHERE extname='postgis'; SELECT count(*) FROM pg_namespace WHERE nspname='baikor';"
    if ($LASTEXITCODE -ne 0 -or ($actual -join ',') -ne '1,1') { throw 'Missing database bootstrap artifacts.' }
    Write-Output 'PASS: a fresh database, PostGIS, schema and three logins were created; a second run succeeded unchanged.'
} finally {
    if ($database -notmatch '^baikor_test_[a-f0-9]{10}$') { throw 'Unsafe cleanup target.' }
    kubectl -n $Namespace delete job $jobName --ignore-not-found --wait=true | Out-Null
    kubectl -n $Namespace exec $DatabasePod -- psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS $database;" | Out-Null
    foreach ($role in $roles) {
        kubectl -n $Namespace exec $DatabasePod -- psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "DROP ROLE IF EXISTS $role;" | Out-Null
    }
    kubectl -n $Namespace delete secret $jobName --ignore-not-found | Out-Null
}
