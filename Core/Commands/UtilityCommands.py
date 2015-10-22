from sympy.parsing.sympy_parser import parse_expr
from Core.Dispatcher import DispatcherSingleton


@DispatcherSingleton.register
def calc(bot, event, *args):
    from sympy.parsing.sympy_parser import standard_transformations, implicit_multiplication_application

    query = ' '.join(args)

    transformations = (standard_transformations + (implicit_multiplication_application,))
    result = parse_expr(query, transformations=transformations)
    bot.send_message(event.conv, str(result))
