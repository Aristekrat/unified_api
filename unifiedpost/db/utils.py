from typing import Optional, Dict, List, Text

from aiopg.sa import SAConnection


async def fetchone(conn: SAConnection, query: Text) -> Optional[Dict]:
    """ Wrapper for fetching a single row """
    cursor = await conn.execute(query)
    row = await cursor.fetchone()
    return dict(row) if row else None


async def fetchall(conn: SAConnection, query: Text) -> Optional[List[Dict]]:
    """ Wrapper for fetching all rows """
    cursor = await conn.execute(query)
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]
