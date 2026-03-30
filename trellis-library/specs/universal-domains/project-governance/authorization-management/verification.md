# Authorization Management — Verification

## Test Scenarios

### TC-A: Trial Expiration Preserves Data

1. Set system date to 1 day before trial expiration
2. Create sample data (documents, records, etc.)
3. Advance system date past expiration
4. Verify:
   - System shows "trial expired" or enters demo mode
   - All sample data is still visible
   - Export function works for all data types
   - No "access denied" errors for reading existing data

### TC-B: Permanent Authorization Transitions Cleanly

1. Install trial version, create sample data
2. Apply permanent license key (simulate payment completion)
3. Verify:
   - Trial banners/demo watermarks disappear
   - Previously restricted features become available
   - Sample data still present and accessible
   - No reinstallation or data migration prompts

### TC-C: Authorization Status Visibility

1. Navigate to "License Information" or "About" page
2. Verify displayed:
   - Current status (trial/expired/permanent)
   - Expiration date if applicable
   - Days remaining / uses remaining
   - Instructions for upgrading if in trial

### TC-D: Clock Rollback Resistance (if time-based)

1. Set trial expiration to tomorrow
2. Run software, verify trial active
3. Set system clock 1 month back
4. Restart software
5. Verify:
   - System detects clock rollback OR
   - Trial still counts down based on original expiration (not extended by rollback)

## Evidence Collection

For each test scenario, capture:

- Screenshot of authorization status page
- Video or step-by-step screenshots of expiration behavior
- Exported data file (to prove export works)
- License key application confirmation

Store evidence in `delivery/verification-evidence/` or attach to delivery documentation.

## Gate Conditions

Before marking delivery complete:

- [ ] TC-A passed (expiration non-destructive)
- [ ] TC-B passed (upgrade seamless)
- [ ] TC-C passed (status visible)
- [ ] TC-D passed (if applicable: clock rollback handled)
- [ ] All evidence collected and reviewed
