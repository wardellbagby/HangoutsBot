import sqlite3
from sympy.parsing.sympy_parser import parse_expr
from Core.Dispatcher import DispatcherSingleton
from Core.Util import UtilBot, UtilDB


@DispatcherSingleton.register
def calc(bot, event, *args):
    from sympy.parsing.sympy_parser import standard_transformations, implicit_multiplication_application

    query = ' '.join(args)

    transformations = (standard_transformations + (implicit_multiplication_application,))
    result = parse_expr(query, transformations=transformations)
    bot.send_message(event.conv, str(result))


@DispatcherSingleton.register
def poke(bot, event, *args):
    user_name = ' '.join(args)
    if user_name == 'abstain':
        db_file = UtilDB.get_database()
        db = sqlite3.connect(db_file)
        cursor = db.cursor()
        result = cursor.execute("SELECT poke_abstain FROM users WHERE user_id = ?",
                                (event.user.id_.chat_id,)).fetchone()
        if result:
            abstain = result[0]
            cursor.execute("UPDATE users SET poke_abstain = ? WHERE user_id = ?", (not abstain, event.user.id_.chat_id))
        else:
            cursor.execute("INSERT INTO users VALUES (?,?)", (event.user.id_.chat_id, True))
    else:
        for u in event.conv.users:
            if user_name in u.full_name:
                bot_poke_conv = UtilBot.find_private_conversation(bot._conv_list, u.id_.chat_id,
                                                                  default=None)
                if bot_poke_conv is not None and UtilBot.can_poke(event.user.id_.chat_id, u.id_.chat_id,
                                                                  bot_poke_conv.id_):
                    UtilBot.initiate_poke(event.user, u, event.conv, bot)
                    return
                else:
                    bot.send_message(event.conv, "%s can not currently be poked." % u.full_name)
                    return
