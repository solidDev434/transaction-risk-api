from .celery import celery_app


@celery_app.task(name="drain_transaction_outbox")
def drain_transaction_outbox():
    print("running")
