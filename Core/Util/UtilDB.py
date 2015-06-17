import sqlite3

_database_file = None


class DatabaseNotInitializedError(BaseException):
    pass


curr_version = 1


def setDatabase(db):
    global _database_file
    _database_file = db
    _init_tables()


def _on_upgrade(version):
    if _database_file:
        database = sqlite3.connect(_database_file)
        cursor = database.cursor()
    else:
        return

    if version == -1:  # Drop all tables and recreate.
        cursor.execute("DROP TABLE karma")
        cursor.execute("DROP TABLE reminders")
        cursor.execute("DROP TABLE version")

        cursor.execute("CREATE TABLE karma (user_id text, karma integer, abstain boolean)")
        cursor.execute("CREATE TABLE reminders (conv_id text, message text, timestamp integer)")
        cursor.execute("CREATE TABLE version (version integer)")
        version = curr_version  # Since we recreated the whole table, we can just immediately go to current version.

    elif version == 0:  # Added in a abstain column to reminders; adds in version table.
        cursor.execute("ALTER TABLE karma ADD COLUMN abstain boolean")
        cursor.execute("CREATE TABLE version (version integer)")
        version += 1

    cursor.execute("INSERT INTO version VALUES (?)", (version,))
    database.commit()
    database.close()


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
                version = cursor.execute("SELECT version FROM version").fetchone()[0]

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
                    cursor.execute(("INSERT INTO %s VALUES (" % table) + ','.join(["?" for x in defaults]) + ")", defaults)
        database.commit()
    else:
        raise DatabaseNotInitializedError()


def get_database():
    return _database_file
