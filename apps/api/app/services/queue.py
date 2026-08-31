from app.jobs.slack import process_slack_event


def enqueue_slack_event(payload: dict) -> None:
    process_slack_event.send(payload)
