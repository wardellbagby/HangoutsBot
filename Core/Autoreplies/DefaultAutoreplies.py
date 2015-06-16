import asyncio
from urllib.error import HTTPError, URLError
import hangups
from Core.Autoreplies import AutoReply
from Core.Dispatcher import DispatcherSingleton
from Libraries.cleverbot import ChatterBotFactory, ChatterBotType

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
        hangups.ChatMessageSegment("Picture Message", segment_type=hangups.SegmentType.LINE_BREAK)],
                              image_id=image_id)


@DispatcherSingleton.register_autoreply([url_regex], label="Link Summarizer")
def _url_handle(bot, event, url):
    if "googleusercontent" in url or "youtube" in url or "youtu.be" in url:  # Ignore links Hangouts will handle itself.
        yield from bot._client.settyping(event.conv_id, hangups.TypingStatus.STOPPED)
        return

    if "imgur" in url and url.endswith('gifv'):
        url = url.replace("gifv", "gif")

    if (url.endswith('gif') or url.endswith('jpg') or url.endswith("jpeg") or url.endswith('png') or url.endswith(
            "bmp")):
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
            yield from bot._client.settyping(event.conv_id, hangups.TypingStatus.STOPPED)
            return

        bot.send_message_segments(event.conv, [
            hangups.ChatMessageSegment(summary),
            hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
            hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
            hangups.ChatMessageSegment(url, hangups.SegmentType.LINK, link_target=url)])

        # TODO Possibly add in Facebook-esque image sending, too.

    if nltk_installed:
        yield from send_link_preview(bot, event, url)



@DispatcherSingleton.register_autoreply(["whistle", "bot", "whistlebot"], label="Automatic Context Replies")
def think(bot, event, *args):
    if clever_session:
        bot.send_message(event.conv, clever_session.think(' '.join(args)))
