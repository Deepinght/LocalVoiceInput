import json
import sqlite3
from dataclasses import asdict
from datetime import datetime


class History:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute('''CREATE TABLE IF NOT EXISTS history (
          id INTEGER PRIMARY KEY, timestamp TEXT, profile TEXT, app_name TEXT,
          raw_text TEXT, processed_text TEXT, confirmed_text TEXT, committed INTEGER, trace TEXT)''')
        self.db.commit()

    def add(self, ctx):
        cursor = self.db.execute("INSERT INTO history VALUES(NULL,?,?,?,?,?,?,?,?)", (
            datetime.now().astimezone().isoformat(), ctx.profile, ctx.app_name, ctx.raw_text, ctx.text, None, 0,
            json.dumps([asdict(event) for event in ctx.trace], ensure_ascii=False)))
        self.db.commit()
        return cursor.lastrowid

    def finish(self, row, text, committed):
        self.db.execute("UPDATE history SET confirmed_text=?, committed=? WHERE id=?", (text, int(committed), row))
        self.db.commit()

    def recent(self):
        return self.db.execute("SELECT timestamp,profile,raw_text,processed_text,confirmed_text,committed,trace FROM history ORDER BY id DESC LIMIT 100").fetchall()
