from app.jobs.slack import (
    process_slack_event,
)
from app.jobs.slack_actions import (
    process_slack_action,
)


def enqueue_slack_event(
    payload: dict,
) -> None:
    process_slack_event.send(
        payload
    )


def enqueue_slack_action(
    payload: dict,
) -> None:
    process_slack_action.send(
        payload
    )
