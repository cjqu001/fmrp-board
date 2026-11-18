# ERRORS: errors hit and how they were fixed

| Date | Error | Cause | Fix |
|---|---|---|---|
| 2026-11-18 | `sudo: a password is required` over SSH | NAS sudo needs an interactive password | Used `netstat -tln` without sudo for the port check; Docker commands on the NAS must be run by the user or with their approval. |
| 2026-11-18 | Seed test expected 56 records, got 55 | Test miscount; the handoff table has 55 rows | Test now expects 55. |
