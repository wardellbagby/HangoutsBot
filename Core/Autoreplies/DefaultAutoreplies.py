import asyncio
from urllib.error import HTTPError, URLError
import hangups
from hangups import hangouts_pb2
from Core.Autoreplies import AutoReply
from Core.Dispatcher import DispatcherSingleton
from Libraries.cleverbot import ChatterBotFactory, ChatterBotType

ignore_urls = ["reddit.com", "googleusercontent", "youtube.com", "youtu.be"]
nltk_installed = True
try:
    from Libraries import summarize
except ImportError:
    nltk_installed = False

clever_session = ChatterBotFactory().create(ChatterBotType.CLEVERBOT).create_session()

url_regex = "^((([A-Za-z]{3,9}:(?:\\/\\/)?)(?:[\\-;:&=\\+\\$,\\w]+@)?[A-Za-z0-9\\.\\-]+|(?:www\\.|[\\-;:&=\\+\\$,\\w]+@)[A-Za-z0-9\\.\\-]+)((?:\\/[\\+~%\\/\\.\\w\\-]*)?\\??(?:[\\-\\+=&;%@\\.\\w]*)#?(?:[\\.\\!\\/\\\\w]*))?)$"

DispatcherSingleton.register_autoreply_type(AutoReply(["^@[\\w\\s]+$"], "/karma {}", label="Karma Status"))
DispatcherSingleton.register_autoreply_type(AutoReply(["^@[\\w\\s]+\\++$"], "/_karma {}", label="Karma Increasing"))
DispatcherSingleton.register_autoreply_type(AutoReply(["^@[\\w\\s]+-+$"], "/_karma {}", label="Karma Decreasing"))


@asyncio.coroutine
def send_image(bot, event, url):
    try:
        image_id = yield from bot.upload_image(url)
    except HTTPError:
        bot.send_message(event.conv, "Error attempting to upload image.")
        return
    bot.send_message_segments(event.conv, [
        hangups.ChatMessageSegment("Picture Message", segment_type=hangouts_pb2.SEGMENT_TYPE_LINE_BREAK)],
                              image_id=image_id)


@DispatcherSingleton.register_autoreply([url_regex], label="Link Summarizer")
def _url_handle(bot, event, url):
    lower_url = url.lower()
    for ignore in ignore_urls:
        if ignore in lower_url:
            yield from bot._client.settyping(event.conv_id, hangups.TypingStatus.STOPPED)
            return

    if "imgur" in lower_url and lower_url.endswith('.gifv'):
        index = lower_url.rfind('gifv')
        if index > 0 and index + 3 < len(lower_url):
            url = url[0:index] + "gif"
    elif "imgur" in lower_url and lower_url.endswith('.webm'):
        index = lower_url.rfind('webm')
        if index > 0 and index + 3 < len(lower_url):
            url = url[0:index] + "gif"

    if (url.endswith('.gif') or url.endswith('.jpg') or url.endswith(".jpeg") or url.endswith(
            '.png') or url.endswith(
        ".bmp")):
        yield from send_image(bot, event, url)
        return

    @asyncio.coroutine
    def send_link_preview(bot, event, url):
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "http://" + url

        try:
            summary = summarize.summarize_page(url)
            if len(summary.summaries) < 3:
                return
            if len(summary.summaries) > 3:
                summary = " ".join(summary.summaries[:3])
            else:
                summary = " ".join(summary.summaries)
        except HTTPError as e:
            segments = [hangups.ChatMessageSegment('"{}" gave HTTP error code {}.'.format(url, e.code))]
            bot.send_message_segments(event.conv, segments)
            return
        except (ValueError, URLError):
            yield from bot._client.settyping(event.conv_id, hangups.TYPING_TYPE_STOPPED)
            return

        bot.send_message_segments(event.conv, [
            hangups.ChatMessageSegment(summary),
            hangups.ChatMessageSegment('\n', hangouts_pb2.SEGMENT_TYPE_LINE_BREAK),
            hangups.ChatMessageSegment('\n', hangouts_pb2.SEGMENT_TYPE_LINE_BREAK),
            hangups.ChatMessageSegment(url, hangouts_pb2.SEGMENT_TYPE_LINK, link_target=url)])

        # TODO Possibly add in Facebook-esque image sending, too.

    if nltk_installed:
        yield from send_link_preview(bot, event, url)


@DispatcherSingleton.register_autoreply(["whistle", "bot", "whistlebot", "catbug"], label="Automatic Context Replies")
def think(bot, event, *args):
    if clever_session:
        bot.send_message(event.conv, clever_session.think(' '.join(args)))


@DispatcherSingleton.register_autoreply(["^r\/\\w+$"], label="Reddit autocomplete")
def reddit_complete(bot, event, *args):
    if len(args) == 1:
        link = "http://www.reddit.com/"
        segment = [hangups.ChatMessageSegment(link + args[0], link_target=link + args[0])]
        bot.send_message_segments(event.conv, segment)
    yield from bot._client.settyping(event.conv_id, hangups.TYPING_TYPE_STOPPED)
