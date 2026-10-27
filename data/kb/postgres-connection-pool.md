# PostgreSQL connection pool exhaustion

## Symptoms
Application logs show `FATAL: sorry, too many clients already` or
`remaining connection slots are reserved for non-replication superuser connections`.
Request latency rises sharply before any error appears, because callers queue
waiting for a connection rather than failing fast.

## First checks
Count live connections and group them by state. A pool that is exhausted by
`idle in transaction` connections is a different problem from one exhausted by
`active` ones: the first is a code path that opens a transaction and forgets to
close it, the second is genuine load.

Check `max_connections` on the server against the sum of pool sizes across every
deploying service. Each replica carries its own pool, so horizontal scaling
multiplies connection demand even when traffic is flat.

## Common causes
A pool size that was tuned for one replica and never revisited after the service
was scaled out. A long-running analytical query holding a connection. A missing
timeout on an external call made inside a transaction, so the transaction stays
open for as long as the remote service takes to answer.

## Resolution
Set a statement timeout and an idle-in-transaction session timeout so a stuck
transaction releases its slot instead of holding it indefinitely. Move
analytical queries off the primary. If the pool is genuinely undersized,
introduce a connection pooler in transaction mode rather than raising
`max_connections`, which costs memory per connection on the server.
