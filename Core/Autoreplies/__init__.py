import asyncio
import glob
import os
import re
import types

extra_replies = glob.glob("Core" + os.sep + "Autoreplies" + os.sep + "*.py")
__all__ = [os.path.basename(f)[:-3] for f in extra_replies]
__all__.append("AutoReply")
__all__.append("NullAutoReply")

# In order to facilitate turning off certain autoreplies in chat, we need to keep them in memory.
class AutoReply(object):
    def __init__(self, triggers, response, conv_id=None, muted=None, label=None):
        self.triggers = frozenset(triggers)
        if isinstance(response, types.FunctionType):
            self.response_func = asyncio.coroutine(response)
        else:
            self.response = response
        self.conv_id = conv_id

        # For global autoreplies, this is a dictionary. Otherwise, it's just a boolean.
        if conv_id is not None:
            self.muted = False if muted is None else True
        else:
            if isinstance(muted, dict):
                self.muted = muted
            else:
                self.muted = {}
        if not label:
            self.label = " / ".join(triggers)
        else:
            self.label = label

    def __eq__(self, other):
        return self.response == other.response and self.conv_id == other.conv_id and self.triggers == other.triggers

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return self.triggers.__hash__() ^ \
            (self.response_func.__hash__()) if self.is_func() else self.response.__hash__() ^ self.conv_id.__hash__()

    def is_triggered(self, text, conv_id=None):
        if self.is_muted(conv_id):
            return False
        if self.conv_id is not None and conv_id != self.conv_id:
            return False
        for trigger in self.triggers:
            if trigger == '*':  # * is the wildcard for any text.
                return True

            # This is a regex based trigger, so we have to match based on it.
            if trigger[0] == '^' and trigger[-1] == '$':
                if re.match(trigger, text):
                    return True
                continue
            else:
                escaped = trigger.encode('unicode-escape').decode()
                if trigger != escaped:
                    if trigger in text:
                        return True
                # For word/phrased based triggers, we need to put a word boundary between the words we check for.
                if re.search('\\b' + trigger + '\\b', text, re.IGNORECASE):
                    return True
        return False

    def is_command(self, command_char):
        return not self.is_func() and self.response.startswith(command_char)

    def is_func(self):
        try:
            self.response_func
        except AttributeError:
            return False
        return True

    def is_muted(self, conv_id=None):
        if conv_id and isinstance(self.muted, dict):
            try:
                return self.muted[conv_id]
            except KeyError:
                self.muted[conv_id] = False
                return False
        return self.muted

    def set_muted(self, muted, conv_id=None):
        if isinstance(self.muted, dict) and conv_id is not None:
            self.muted[conv_id] = muted
        else:
            self.muted = muted


# For conversations that specifically want no autoreplies set.
class NullAutoReply(AutoReply):
    def __init__(self, triggers, response, conv_id=None):
        super().__init__(triggers, response, conv_id=conv_id)
        self.label = None

    def is_triggered(self, text, conv_id=None):
        return False
