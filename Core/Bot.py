#!/usr/bin/env python
# coding=utf-8
from datetime import date, datetime
import os
import random
import sys
import asyncio
import tempfile
import time
import signal
import traceback
from urllib import request
from urllib.request import FancyURLopener

import hangups
from hangups.ui.utils import get_conv_name
from requests import HTTPError
from Core.Commands.Dispatcher import DispatcherSingleton

from Core.Util import ConfigDict, UtilDB
from Core import Handlers


class HangoutsBotOpener(FancyURLopener):
    version = 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36'


request.urlretrieve = HangoutsBotOpener().retrieve

__version__ = '1.1'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


class ConversationEvent(object):
    def __init__(self, bot, conv_event):
        self.conv_event = conv_event
        self.conv_id = conv_event.conversation_id
        self.conv = bot._conv_list.get(self.conv_id)
        self.user_id = conv_event.user_id
        self.user = self.conv.get_user(self.user_id)
        self.timestamp = conv_event.timestamp
        self.text = conv_event.text.strip() if isinstance(conv_event, hangups.ChatMessageEvent) else ''

    def print_debug(self):
        print('Conversation ID: {}'.format(self.conv_id))
        print('Conversation name: {}'.format(get_conv_name(self.conv, truncate=True)))
        print('User ID: {}'.format(self.user_id))
        print('User name: {}'.format(self.user.full_name))
        print('Timestamp: {}'.format(self.timestamp.astimezone(tz=None).strftime('%Y-%m-%d %H:%M:%S')))
        print('Text: {}'.format(self.text))
        print()


class HangoutsBot(object):
    """Hangouts bot listening on all conversations"""

    def __init__(self, cookies_path, config_path, command_char='/', max_retries=5):
        self._client = None
        self._cookies_path = cookies_path
        self._max_retries = max_retries
        self._command_char = command_char

        # These are populated by on_connect when it's called.
        self._conv_list = None  # hangups.ConversationList
        self._user_list = None  # hangups.UserList
        self._message_handler = None  # MessageHandler

        # Load config file
        self.config = ConfigDict.ConfigDict(config_path)
        self.devmode = self.get_config_suboption('', 'development_mode')

        self.database = "database.db"
        UtilDB.setDatabase(self.database)

        # Handle signals on Unix
        # (add_signal_handler is not implemented on Windows)
        try:
            loop = asyncio.get_event_loop()
            for signum in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(signum, lambda: self.stop())
        except NotImplementedError:
            pass

    def restart(self):
        self.stop()
        self.run()

    def login(self, cookies_path):
        """Login to Google account"""
        # Authenticate Google user and save auth cookies
        # (or load already saved cookies)
        try:
            cookies = hangups.auth.get_auth_stdin(cookies_path)
            return cookies
        except hangups.GoogleAuthError as e:
            print('Login failed ({})'.format(e))
            return False

    def run(self):
        """Connect to Hangouts and run bot"""
        cookies = self.login(self._cookies_path)
        if cookies:
            while True:
                try:
                    # Create Hangups client
                    self._client = hangups.Client(cookies)
                    self._client.on_connect.add_observer(self._on_connect)
                    self._client.on_disconnect.add_observer(self._on_disconnect)

                    # Start asyncio event loop and connect to Hangouts
                    # If we are forcefully disconnected, try connecting again
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(self._client.connect())
                    sys.exit(0)
                except Exception as e:
                    print('Client unexpectedly disconnected:\n{}'.format(e))
                    log = open('log.txt', 'a+')
                    log.writelines(str(datetime.now()) + ":\n " + traceback.format_exc() + "\n\n")
                    log.close()
                    print(traceback.format_exc())
                    time.sleep(10)
            print('Maximum number of retries reached! Exiting...')
        sys.exit(1)

    def stop(self):
        """Disconnect from Hangouts"""
        asyncio.async(
            self._client.disconnect()
        ).add_done_callback(lambda future: future.result())

    def handle_chat_message(self, conv_event):
        """Handle chat messages"""
        event = ConversationEvent(self, conv_event)
        asyncio.async(self._message_handler.handle(event))

    def handle_membership_change(self, conv_event):
        """Handle conversation membership change"""
        event = ConversationEvent(self, conv_event)

        # Don't handle events caused by the bot himself
        if event.user.is_self:
            return

        # Test if watching for membership changes is enabled
        if not self.get_config_suboption(event.conv_id, 'membership_watching_enabled'):
            return

        # Generate list of added or removed users
        event_users = [event.conv.get_user(user_id) for user_id
                       in event.conv_event.participant_ids]
        names = ', '.join([user.full_name for user in event_users])

        # JOIN
        if event.conv_event.type_ == hangups.MembershipChangeType.JOIN:
            # Test if user who added new participants is admin
            admins_list = self.get_config_suboption(event.conv_id, 'admins')
            if event.user_id.chat_id in admins_list:
                self.send_message(event.conv,
                                  '{}: Hello and welcome!'.format(names))
            else:
                segments = [hangups.ChatMessageSegment('!!! CAUTION !!!', is_bold=True),
                            hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                            hangups.ChatMessageSegment('{} has illegally added {} to this hangout!'.format(
                                event.user.full_name, names)),
                            hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                            hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                            hangups.ChatMessageSegment('{}: Please leave this Hangout immediately!'.format(names))]
                self.send_message_segments(event.conv, segments)
        # LEAVE
        else:
            self.send_message(event.conv, 'Goodbye, {}.'.format(names))

    def handle_rename(self, conv_event):
        """Handle conversation rename"""
        event = ConversationEvent(self, conv_event)

        # Test if watching for conversation rename is enabled
        if not self.get_config_suboption(event.conv_id, 'rename_watching_enabled'):
            return

        # TODO This needs to refactored. No extra-command specific logic should be in the Bot file.
        if DispatcherSingleton.commands['record']:
            if event.conv_event.new_name == '':
                text = "Name cleared"
                directory = "Records" + os.sep + str(event.conv_id)
                if not os.path.exists(directory):
                    os.makedirs(directory)
                filename = str(date.today()) + ".txt"
                file = open(directory + os.sep + filename, "a+")
                file.write(text + '\n')
            else:
                text = "Name changed to: " + conv_event.new_name
                directory = "Records" + os.sep + str(event.conv_id)
                if not os.path.exists(directory):
                    os.makedirs(directory)
                filename = str(date.today()) + ".txt"
                file = open(directory + os.sep + filename, "a+")
                file.write(text + '\n')

    def send_message(self, conversation, text):
        """"Send simple chat message"""
        self.send_message_segments(conversation, [hangups.ChatMessageSegment(text)])

    def send_message_segments(self, conversation, segments, image_id=None):
        """Send chat message segments"""
        # Ignore if the user hasn't typed a message.
        if len(segments) == 0:
            return
        # XXX: Exception handling here is still a bit broken. Uncaught
        # exceptions in _on_message_sent will only be logged.
        asyncio.async(
            conversation.send_message(segments, image_id=image_id)
        ).add_done_callback(self._on_message_sent)

    @asyncio.coroutine
    def upload_image(self, url, filename=None, delete=False):
        if not filename:
            tempdir = tempfile.gettempdir()
            filename = tempdir + os.sep + '{}.png'.format(random.randint(0, 9999999999))
        req = request.Request(url, headers={
            'User-agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36'})
        image = request.urlopen(req)
        try:
            with open(filename, "wb") as image_file:
                image_file.write(image.read())
        except HTTPError as e:
            raise e

        # request.urlretrieve(url, filename)
        file = open(filename, "rb")
        image_id = yield from self._client.upload_image(file)
        if delete:
            file.close()
            os.remove(filename)
        return image_id

    def list_conversations(self):
        """List all active conversations"""
        convs = sorted(self._conv_list.get_all(),
                       reverse=True, key=lambda c: c.last_modified)
        return convs

    def get_config_suboption(self, conv_id, option):
        """Get config suboption for conversation (or global option if not defined)"""
        try:
            suboption = self.config['conversations'][conv_id][option]
        except KeyError:
            try:
                suboption = self.config[option]
            except KeyError:
                suboption = None
        except TypeError:
            if self.config['conversations'] is None:
                self.config['conversations'] = {}
            elif self.config['conversations'][conv_id] is None:
                self.config['conversations'][conv_id] = {}
            suboption = None
        return suboption

    def _on_message_sent(self, future):
        """Handle showing an error if a message fails to send"""
        try:
            future.result()
        except hangups.NetworkError:
            print('Failed to send message!')

    def _on_connect(self, initial_data):
        """Handle connecting for the first time"""
        print('Connected!')

        self._user_list = hangups.UserList(self._client,
                                           initial_data.self_entity,
                                           initial_data.entities,
                                           initial_data.conversation_participants)
        self._conv_list = hangups.ConversationList(self._client,
                                                   initial_data.conversation_states,
                                                   self._user_list,
                                                   initial_data.sync_timestamp)
        self._conv_list.on_event.add_observer(self._on_event)

        self._message_handler = Handlers.MessageHandler(self, command_char=self._command_char)

        print('Conversations:')
        for c in self.list_conversations():
            print(('  {} ({})'.format(get_conv_name(c, truncate=True), c.id_)).encode('UTF-8'))
        print()

    def _on_event(self, conv_event):
        """Handle conversation events"""
        if isinstance(conv_event, hangups.ChatMessageEvent):
            self.handle_chat_message(conv_event)
        elif isinstance(conv_event, hangups.MembershipChangeEvent):
            self.handle_membership_change(conv_event)
        elif isinstance(conv_event, hangups.RenameEvent):
            self.handle_rename(conv_event)

    def _on_disconnect(self):
        """Handle disconnecting"""
        print('Connection lost!')
