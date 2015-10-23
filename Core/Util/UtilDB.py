import sqlite3

_database_file = None


# TODO It's obvious that my SQL knowledge is severely lacking. If anyone wants to fix this, please feel free.

class DatabaseNotInitializedError(BaseException):
    pass


_create_table_sql = {
    "karma": "CREATE TABLE karma (user_id text, karma integer, abstain boolean)",
    "version": "CREATE TABLE version (version integer)",
    "autoreplies": "CREATE TABLE autoreplies (hashcode integer primary key, muted boolean)",
    "reminders": "CREATE TABLE reminders (conv_id text, message text, timestamp integer)",
    "focus": "CREATE TABLE focus (conv_id text, user_id text, type integer, timestamp integer)",
    "pokes": "CREATE TABLE pokes (conv_id text, poker_id text, pokee_id text)",
    "users": "CREATE TABLE users (user_id text, poke_abstain boolean)"
}
curr_version = 3


def setDatabase(db):
    global _database_file
    _database_file = db
    _init_tables()


def _on_upgrade(version):
    if _database_file and version is not curr_version:
        database = sqlite3.connect(_database_file)
        cursor = database.cursor()
    else:
        return
    print("Upgrading Database from %s to %s" % (version, curr_version))
    try:
        if version == -1:  # Drop all tables and recreate.
            database.commit()
            database.close()
            database, cursor = _create_tables(_database_file)
            version = curr_version
        elif version == 0:  # Added in a abstain column to reminders; adds in version table.
            cursor.execute("ALTER TABLE karma ADD COLUMN abstain boolean")
            cursor.execute("CREATE TABLE version (version integer)")
            version += 1

        elif version == 1:  # Added in a table to autoreplies.
            cursor.execute("CREATE TABLE autoreplies (hashcode integer primary key, muted boolean)")
            version += 1
        elif version == 2:  # Created tables for persisting focus and pokes
            cursor.execute(_create_table_sql["focus"])
            cursor.execute(_create_table_sql["pokes"])
            cursor.execute(_create_table_sql["users"])
            version += 1
    except sqlite3.OperationalError:
        # Just recreate.
        cursor.close()
        database.commit()
        database.close()
        database, cursor = _create_tables(_database_file)
        version = curr_version

    cursor.execute("UPDATE version SET version = ?", (version,))
    database.commit()
    database.close()


def _create_tables(_database_file):
    db = sqlite3.connect(_database_file)
    cursor = db.cursor()
    for table in _create_table_sql.keys():
        cursor.execute("DROP TABLE IF EXISTS %s" % table)
        cursor.execute(_create_table_sql[table])

    cursor.execute("INSERT INTO version VALUES (?)", (curr_version,))
    db.commit()
    db.close()
    db = sqlite3.connect(_database_file)
    return db, db.cursor()


def _init_tables():
    if _database_file:
        database = sqlite3.connect(_database_file)
        cursor = database.cursor()

        cursor.execute("SELECT name from sqlite_master WHERE type='table'")
        result = cursor.fetchall()

        if len(result) == 0:  # No tables! Let's make them all!
            _on_upgrade(-1)
            return

        version = None
        for row in result:
            if 'version' in row:
                version = cursor.execute("SELECT version FROM version").fetchone()
                if version:
                    version = version[0]

        # If we don't have a version from the table, it doesn't exist. Let's create it.
        if not version:
            version = 0

        if version != curr_version:
            _on_upgrade(version)

        database.commit()
        cursor.close()
        database.close()
    else:
        raise DatabaseNotInitializedError()


def get_value_by_user_id(table, user_id, conv_id=None):
    if _database_file:
        database = sqlite3.connect(_database_file)
        cursor = database.cursor()
        if conv_id:
            cursor.execute("SELECT * FROM %s WHERE user_id = ? AND conv_id = ?" % table, (user_id, conv_id))
        else:
            cursor.execute("SELECT * FROM %s WHERE user_id = ?" % table, (user_id,))
        return cursor.fetchone()

    else:
        raise DatabaseNotInitializedError()


def get_values_by_user_id(table, user_id, conv_id=None):
    if _database_file:
        database = sqlite3.connect(_database_file)
        cursor = database.cursor()
        if conv_id:
            cursor.execute("SELECT * FROM %s WHERE user_id = ? AND conv_id = ?" % table, (user_id, conv_id))
        else:
            cursor.execute("SELECT * FROM %s WHERE user_id = ?" % table, (user_id,))
        return cursor.fetchall()

    else:
        raise DatabaseNotInitializedError()


# TODO This is a bad function that does bad things.
def set_value_by_user_id(table, user_id, keyword, value, conv_id=None, defaults=None):
    if not defaults:
        defaults = []
    if _database_file:
        database = sqlite3.connect(_database_file)
        cursor = database.cursor()
        if conv_id:
            result = get_value_by_user_id(table, user_id, conv_id)
            if result:
                cursor.execute("UPDATE %s SET %s = ? WHERE user_id = ? and conv_id = ?" % (table, keyword),
                               (keyword, value, user_id, conv_id))
            else:
                cursor.execute(("INSERT INTO %s VALUES (" % table) + ','.join(["?" for x in defaults]) + ")", defaults)
        else:
            result = get_value_by_user_id(table, user_id, conv_id)
            if result:
                cursor.execute("UPDATE %s SET %s = ? WHERE user_id = ?" % (table, keyword), (value, user_id))
            else:
                try:
                    cursor.execute("INSERT INTO %s VALUES (?, ?)" % table, (user_id, value))
                except sqlite3.OperationalError:
                    cursor.execute(("INSERT INTO %s VALUES (" % table) + ','.join(["?" for x in defaults]) + ")",
                                   defaults)
        database.commit()
    else:
        raise DatabaseNotInitializedError()


def get_database():
    return _database_file
