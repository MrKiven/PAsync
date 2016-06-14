# PAsync
Async Framework Based On Python

Usage
=====

Client
-------

``` python

    from pasync.connection import ConnectionPool

    pool = ConnectionPool()
    client = pool.get_connection()

    client.send('hello')
    res = client.get_result()

```
