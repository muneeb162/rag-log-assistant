# TLS certificate expiry and handshake failures

## Symptoms
Clients report `certificate verify failed`, `x509: certificate has expired or is
not yet valid`, or a sudden wave of connection errors from one service with no
corresponding deploy. Server-side logs may show nothing at all, because the
handshake fails before the request reaches the application.

## First checks
Read the certificate's not-before and not-after dates directly from the endpoint
rather than trusting a dashboard. Check the whole chain, not the leaf: an expired
intermediate produces the same error as an expired leaf and is easier to miss.

Check the clock on both ends. A client whose clock has drifted far enough will
reject a perfectly valid certificate as not yet valid.

## Common causes
A certificate renewed in one environment but not another. An automated renewal
that succeeded while the service kept serving the old certificate because it
only reads the file at startup. A certificate pinned by a client that was
rotated on the server side without coordination.

## Resolution
Reload or restart the serving process after renewal, and verify the served
certificate rather than the certificate on disk. Alert on days-to-expiry well
ahead of the event; alerting on the failure itself means finding out from users.
