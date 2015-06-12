from Core.Autoreplies import AutoReply
from Core.Dispatcher import DispatcherSingleton


url_regex = "^((([A-Za-z]{3,9}:(?:\\/\\/)?)(?:[\\-;:&=\\+\\$,\\w]+@)?[A-Za-z0-9\\.\\-]+|(?:www\\.|[\\-;:&=\\+\\$,\\w]+@)[A-Za-z0-9\\.\\-]+)((?:\\/[\\+~%\\/\\.\\w\\-]*)?\\??(?:[\\-\\+=&;%@\\.\\w]*)#?(?:[\\.\\!\\/\\\\w]*))?)$"

DispatcherSingleton.register_autoreply(
    AutoReply(["whistle", "bot", "whistlebot"], "/think {}", label="Automatic Replies"))
DispatcherSingleton.register_autoreply(AutoReply(["^@[\\w\\s]+$"], "/karma {}", label="Karma Status"))
DispatcherSingleton.register_autoreply(AutoReply(["^@[\\w\\s]+\\++$"], "/karma {}", label="Karma Increasing"))
DispatcherSingleton.register_autoreply(AutoReply(["^@[\\w\\s]+-+$"], "/_karma {}", label="Karma Decreasing"))
DispatcherSingleton.register_autoreply(AutoReply([url_regex], "/_karma {}", label="Link Summarizer"))
