# Pod stuck in CrashLoopBackOff

## Symptoms
`kubectl get pods` shows CrashLoopBackOff with a restart count climbing. The
backoff delay doubles each restart up to five minutes, so a pod that has been
failing for a while looks deceptively quiet.

## First checks
Read the logs of the previous container instance, not the current one. The
current container may not have reached the point of failure yet, so its logs are
empty and misleading.

Check the exit code in the pod status. Exit code 1 is usually an application
error and the logs will say why. Exit code 137 is a SIGKILL, which in practice
almost always means the container exceeded its memory limit. Exit code 143 is a
SIGTERM, meaning something asked it to stop.

## Common causes
A memory limit set below real working-set size, which produces a clean-looking
crash with no application error at all. A failing readiness or liveness probe
with too short an initial delay, so a service that simply starts slowly is
killed before it finishes starting. A missing config map or secret, which fails
at mount time before the application runs.

## Resolution
For exit code 137, raise the memory limit or fix the leak; do not raise the
limit without checking which. For probe failures, raise `initialDelaySeconds` to
cover realistic cold-start time and confirm the probe endpoint does not itself
depend on a downstream service.
