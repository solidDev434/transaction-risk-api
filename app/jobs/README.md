# Outbox Worker and Provider Simulation

This folder contains a minimal background worker that drains `transaction_outbox` rows and a simulated payment provider.

Files:

- `provider.py` — simple async simulator that randomly succeeds/fails/timeouts.
- `outbox_worker.py` — the drain worker: reserves a pending outbox row, calls the provider, performs Phase 2 updates atomically (capture funds, credit receiver, mark transaction cleared), and handles retries.
- `worker.py` — small entrypoint to run the worker loop.

Run the worker locally:

```bash
# from the project root
python -m app.jobs.worker
```

Notes:

- The worker uses `SELECT ... FOR UPDATE SKIP LOCKED` to reserve rows for processing.
- Provider behavior is simulated; replace `app.jobs.provider.process_payment` with real HTTP calls for production.
- Backoff and recovery are intentionally simple for clarity — you can extend with a retry queue or external scheduler.
