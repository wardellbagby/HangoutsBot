import sqlite3

_database_file = None


class DatabaseNotInitializedError(BaseException):
    pass


def setDatabase(db):
    global _database_file
    _database_file = db
    _init_tables()


def _init_tables():
    if _database_file:
        database = sqlite3.connect(_database_file)
        cursor = database.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='karma'")
        if not cursor.fetchone():
            cursor.execute("CREATE TABLE karma (user_id text, karma integer)")

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reminders'")
        if not cursor.fetchone():
            cursor.execute(
                "CREATE TABLE reminders (conv_id text, message text, timestamp integer)")

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


def set_value_by_user_id(table, user_id, keyword, value, conv_id=None):
    if _database_file:
        database = sqlite3.connect(_database_file)
        cursor = database.cursor()
        if conv_id:
            result = get_value_by_user_id(table, user_id, conv_id)
            if result:
                cursor.execute("UPDATE %s SET %s = ? WHERE user_id = ? and conv_id = ?" % (table, keyword),
                               (keyword, value, user_id, conv_id))
            else:
                cursor.execute("INSERT INTO %s VALUES (?, ?, ?)" % table, (user_id, conv_id, value))
        else:
            result = get_value_by_user_id(table, user_id, conv_id)
            if result:
                cursor.execute("UPDATE %s SET %s = ? WHERE user_id = ?" % (table, keyword), (value, user_id))
            else:
                cursor.execute("INSERT INTO %s VALUES (?, ?)" % table, (user_id, value))
        database.commit()
    else:
        raise DatabaseNotInitializedError()

def get_database():
    return _database_file



