# §14 API acceptance against Flowlab (synthetic). Exit 0 = pass.
$ErrorActionPreference = "Stop"
$Base = if ($env:UHQ_API_BASE) { $env:UHQ_API_BASE } else { "https://codebase.flowlab.fun" }

function Assert-True($cond, $msg) {
  if (-not $cond) { throw "FAIL: $msg" }
  Write-Host "PASS: $msg"
}

Write-Host "=== §14 acceptance @ $Base ==="

$health = Invoke-RestMethod "$Base/health"
Assert-True ($health.status -eq "ok") "/health ok"

# Staff Hospital A
$sa = Invoke-RestMethod -Method POST "$Base/api/v1/auth/session" -ContentType "application/json" -Body '{"username":"demo@health.local","password":"demo-password-change-me","org_name":"Demo Hospital A"}'
Assert-True ($sa.access_token) "Staff A JWT"
$Ha = @{ Authorization = "Bearer $($sa.access_token)" }

# 1+2 Register synthetic + opaque QR
$regBody = '{"display_name":"S14 Synthetic Acceptance","date_of_birth":"1991-03-03"}'
$reg = Invoke-RestMethod -Method POST "$Base/api/v1/patients" -Headers $Ha -ContentType "application/json; charset=utf-8" -Body $regBody
Assert-True ($reg.uhid -like "UHQ-*") "Unique UHID $($reg.uhid)"
$qr = $reg.card.qr_token
Assert-True ($qr.Length -ge 16) "Opaque QR token length"
Assert-True ($qr -notmatch "CNIC|diagnosis|S14 Synthetic") "QR has no PHI/name"

# Unauthorized
try {
  Invoke-RestMethod -Method POST "$Base/api/v1/patients" -ContentType "application/json" -Body '{"display_name":"Nope"}'
  throw "expected 401"
} catch {
  Assert-True ($_.Exception.Response.StatusCode.value__ -eq 401) "Unauthorized register → 401"
}

# 3+4 Final save sync
$rid = "rx-s14-$(Get-Random)"
$rx = @{
  patient_id = $reg.id
  source_org_name = "Demo Hospital A"
  source_record_id = $rid
  version = 1
  medication_text = "Doxycycline 100mg"
  dose_text = "1 capsule twice daily"
  status = "final"
  local_saved = $true
} | ConvertTo-Json
$evt = Invoke-RestMethod -Method POST "$Base/api/v1/integration-events" -Headers $Ha -ContentType "application/json" -Body $rx
Assert-True ($evt.status -eq "confirmed") "Sync confirmed ($($evt.id))"

# Draft rejected
try {
  $draft = $rx | ConvertFrom-Json
  $draft.status = "draft"
  $draft.source_record_id = "$rid-draft"
  Invoke-RestMethod -Method POST "$Base/api/v1/integration-events" -Headers $Ha -ContentType "application/json" -Body ($draft | ConvertTo-Json)
  throw "expected draft fail"
} catch {
  Assert-True ($_.Exception.Response.StatusCode.value__ -eq 422) "Draft sync → 422"
}

# 5 Idempotent
$dup = Invoke-RestMethod -Method POST "$Base/api/v1/integration-events" -Headers $Ha -ContentType "application/json" -Body $rx
Assert-True ($dup.id -eq $evt.id -and $dup.duplicate -eq $true) "Idempotent duplicate"

# Hospital B resolve + records
$sb = Invoke-RestMethod -Method POST "$Base/api/v1/auth/session" -ContentType "application/json" -Body '{"username":"demo@health.local","password":"demo-password-change-me","org_name":"Demo Hospital B"}'
$Hb = @{ Authorization = "Bearer $($sb.access_token)" }
$resolved = Invoke-RestMethod "$Base/api/v1/patients/resolve-qr?token=$([uri]::EscapeDataString($qr))" -Headers $Hb
Assert-True ($resolved.uhid -eq $reg.uhid) "B resolve QR → same patient"

$records = Invoke-RestMethod "$Base/api/v1/patients/$($reg.id)/records" -Headers $Hb
Assert-True ($records.total -ge 1) "B sees synced records"
$meds = @($records.items | ForEach-Object { $_.body.medicationCodeableConcept.text })
Assert-True ($meds -contains "Doxycycline 100mg") "B sees Hospital A medication"

# Revoked QR denied + audit
$rev = Invoke-RestMethod -Method POST "$Base/api/v1/patients/$($reg.id)/qr/revoke?replace=true" -Headers $Ha
try {
  Invoke-RestMethod "$Base/api/v1/patients/resolve-qr?token=$([uri]::EscapeDataString($qr))" -Headers $Hb
  throw "expected 404"
} catch {
  Assert-True ($_.Exception.Response.StatusCode.value__ -eq 404) "Revoked QR → 404"
}

$audit = Invoke-RestMethod "$Base/api/v1/audit-events?limit=30" -Headers $Ha
$denies = @($audit | Where-Object { $_.decision -eq "deny" })
Assert-True ($denies.Count -ge 1) "Audit denials present"

# Patient channel sees same rx
$email = "s14.$(Get-Random)@example.com"
$pat = Invoke-RestMethod -Method POST "$Base/api/v1/auth/patient/register" -ContentType "application/json" -Body (@{
  email = $email
  password = "synthet1c-pass"
  display_name = "S14 Portal Patient"
  otp = "123456"
} | ConvertTo-Json)
# Link path: staff event already on another patient; for portal patient create rx:
$Hp = @{ Authorization = "Bearer $($pat.access_token)" }
$rx2 = @{
  patient_id = $pat.patient_id
  source_org_name = "Demo Hospital A"
  source_record_id = "rx-s14-portal-$(Get-Random)"
  version = 1
  medication_text = "Portal Visible Med"
  dose_text = "once daily"
  status = "final"
  local_saved = $true
} | ConvertTo-Json
$null = Invoke-RestMethod -Method POST "$Base/api/v1/integration-events" -Headers $Ha -ContentType "application/json" -Body $rx2
$mine = Invoke-RestMethod "$Base/api/v1/patients/me/records" -Headers $Hp
$myMeds = @($mine.items | ForEach-Object { $_.body.medicationCodeableConcept.text })
Assert-True ($myMeds -contains "Portal Visible Med") "Patient /me/records shows synced Rx"

# Admin aggregates
$stats = Invoke-RestMethod "$Base/api/v1/admin/stats" -Headers $Ha
Assert-True ($stats.patients -ge 1 -and $stats.organizations -ge 2) "Admin stats"

Write-Host ""
Write-Host "=== ALL AUTOMATED §14 API CHECKS PASSED ==="
Write-Host "Manual: extension prefill confirm on Hospital B (:5174) — see docs/acceptance-section14.md item 7."
exit 0
