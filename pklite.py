import sqlite3
import pickle

DEFAULT_TABLE = "anim1"
DEFAULT_DB = "./db.sqlite3"

def create_anim_table(db=DEFAULT_DB, table_name=DEFAULT_TABLE):
    db.execute(
        f"CREATE TABLE IF NOT EXISTS {table_name} (frame INTEGER PRIMARY KEY NOT NULL, data BINARY NOT NULL)"
    )

def save_frame(db=DEFAULT_DB, frame=0, pixels=[], table_name=DEFAULT_TABLE):
    db = sqlite3.connect(db)
    create_anim_table(db, table_name)
    pickled_data = pickle.dumps(pixels, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"INSERT OR REPLACE INTO {table_name} (frame, data) VALUES ({frame}, {pickled_data})")
    res = db.execute(
        f"INSERT OR REPLACE INTO {table_name} (frame, data) VALUES (?, ?)",
        (frame, pickled_data),
    )
    db.commit()  # Remember to commit changes after saving things.
    db.close()
    return res

def load_frame(db=DEFAULT_DB, frame=0, table_name=DEFAULT_TABLE):
    db = sqlite3.connect(db)
    res = db.execute(f"SELECT data FROM {table_name} WHERE frame = ?", (frame,))
    row = res.fetchone()
    db.close()
    if not row:
        raise KeyError(frame)
    return pickle.loads(row[0])
