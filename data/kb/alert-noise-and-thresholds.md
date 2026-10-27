# Alert noise and threshold tuning

## Symptoms
A channel full of alerts that nobody reads, and incidents that are noticed by a
customer before they are noticed by the alert that fired four hours earlier.

## First checks
Count alerts by rule over the last month and sort by volume. In most systems a
small number of rules produce the large majority of pages, and they are usually
the ones nobody acts on any more.

For each high-volume rule, ask what the recipient is supposed to do when it
fires. A rule with no answer to that question is not an alert; it is a metric
that should live on a dashboard.

## Common causes
Thresholds set on instantaneous values rather than on a duration, so a single
scrape above the line pages someone. Alerts on causes rather than symptoms, so
one underlying fault produces a dozen pages. Thresholds copied from a different
service with a different normal.

## Resolution
Alert on user-visible symptoms and let causes stay on dashboards. Require a
condition to hold for a duration before firing, so transient spikes do not page.
Set thresholds from the observed distribution of the metric rather than a round
number, and review the top rules by volume regularly rather than only after an
incident.
