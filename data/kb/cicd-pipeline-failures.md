# CI/CD pipeline failing after a green local build

## Symptoms
Tests pass locally and fail in the pipeline, or the pipeline fails at a stage
that was passing the previous day with no related code change.

## First checks
Compare the dependency versions resolved in CI against the local lockfile. A
build that installs from a range rather than a lock will drift the moment an
upstream release lands, which is why a pipeline can break with no commit behind
it.

Check whether the failing stage depends on state left by an earlier stage. A
runner that has been reused keeps caches and sometimes containers; a job that
passes only on a warm runner will fail unpredictably.

## Common causes
Unpinned dependencies. Tests that depend on execution order and happen to pass
locally. A secret or environment variable present locally and absent in the
runner, usually surfacing as an authentication error rather than a missing-value
error. Time zone or locale differences between the developer machine and the
runner image.

## Resolution
Pin dependencies with a lockfile committed to the repository and install from it
in CI. Run the test suite in a randomised order locally so ordering dependencies
surface early. Make missing configuration fail loudly at startup with a named
variable rather than failing later as an opaque auth error.
