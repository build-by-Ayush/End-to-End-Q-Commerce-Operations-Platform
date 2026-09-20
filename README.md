For this project, the RAW layer will prioritize source preservation over semantic typing. Fields whose dirty representations could cause ingestion/type failures will be landed as STRING and converted in STAGING.

---

date - 15/09/206

Discovered Timestamp issue in the staging models , pausing the work on intermediate layer to reslove the issue. 
resolved - 18-09-2026


Don't create a forest of precision columns. Keep the rows. Don't invent seconds. When an exact duration is required and its source timestamp precision is insufficient, leave that derived duration NULL rather than fabricating a value.