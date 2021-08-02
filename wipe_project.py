from sentry.runner import configure
configure()

import time
import click

from sentry.group_deletion import delete_group
from sentry.models import Project, Group, GroupStatus
import sentry_sdk


sentry_sdk.init("")

StopWorking = "stop_working"


@click.command()
@click.option("--project-id", type=int, help="the project id to be dumped, alternative to dsn, or (project-slug,org-slug)")
@click.option("--project-slug", type=str, help="project slug, must also use org-slug, alternatively use project-id or dsn")
@click.option("--org-slug", type=str, help="organization slug, must also use project-slug, alternatively use project-id or dsn")
def main( project_id: int, project_slug: str, org_slug: str):
    """
   Wipes the project of all messages before starting to send.
    """
    now = time.time()

    if project_id is None:
        project = Project.objects.get(organization__slug=org_slug, slug=project_slug)
        project_id = project.id

    delete_groups(project_id)

    print(f"Done. Elapsed time is {time.time() - now} secs.")


def delete_groups(project_id: int):
    groups = (Group.objects.filter(project_id=project_id).
              exclude(status__in=[GroupStatus.PENDING_DELETION, GroupStatus.DELETION_IN_PROGRESS]))

    groups = list(groups)
    print(f"Deleting {len(groups)} existing groups...")

    from sentry.testutils.helpers.task_runner import TaskRunner

    from sentry.eventstream import backend
    # Skip over all snuba replacements to avoid causing load
    # Discover will be full of noise because we will not actually delete
    # events, but that should be fine.
    backend._send = lambda *a, **kw: None

    # TaskRunner such that our monkeypatch above does something
    with TaskRunner():

        with click.progressbar(groups) as groups:
            for group in groups:
                delete_group(group)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
