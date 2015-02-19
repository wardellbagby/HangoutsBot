HangoutsBot
==============

Setup
--------------

In order to use this, you'll need to setup a GMail account for logging in, and a config.json file to give the bot its settings. The config file should look like:

```JSON
{
  "admins": ["YOUR-USER-ID-HERE"],
  "autoreplies_enabled": true,
  "autoreplies": [
    [["bot", "robot", "Yo"], "/think {}"]
  ],
  "development_mode": false,
  "commands_admin": ["hangouts", "reload", "quit", "restart", "config", "restart", "block"],
  "commands_enabled": true,
  "forwarding_enabled": false,
  "rename_watching_enabled": true,
  "conversations": {
    "CONV-ID-HERE": {
      "autoreplies": [
        [["whistle", "bot", "whistlebot"], "/think {}"],
        [["trash"], "You're trash"]
      ],
      "forward_to": [  
        "CONV1_ID" 
      ]
    }
  }
}
```

Line by Line breakdown (excluding braces/brackets):
1. Sets the admins. Only admins can use the admin commands listed in commands_admin.
2. Sets autoreplies to be enabled for every conversation the bot is in.
3. Sets the autoreplies for all conversations the bot is in.
4. Sets "Dev Mode" to default to off for all conversations. Dev Mode will force the bot to print out all of it's replies to the console window instead of replying via Hangouts.
5. Array of all of the commands that only admins will have access to use.
6. Sets commands to be enabled for all chats.
7. Sets chat forwarding for all chats to disabled. (When enabled, you must have a conversation object with a "forward_to" member that is set to a different conversation id.)
8. Sets rename watching to enabled. (This is required to have /record record name changes.)
9. Start of the conversations dictionary.
10. Start of a conversation specific dictionary. "CONV-ID-HERE" should be replaced with an actual id, which looks something like "Ugxxxxxxxxxxx_xxxxxxxxxxxxx".
11. Sets the autoreplies for this specific conversation, which entirely overrides any autoreplies set for all conversations.
12. Sets an autoreply keyword and reply. In this case, "whistle", "bot", and "whistlebot" are all keywords, and the reply will be the command /think, which will be given the entirety of what the user posted. For example: A user saying "Bot, how are you?" would cause the command "/think Bot, how are you?" to be ran. NOTE: The keywords are case-insensitive.
13. Sets another autoreply keyword and reply. In this case, if a user says "trash," the Bot will reply with "You're trash." NOTE: The keywords are case-insensitive.
14. Start of the "forward_to" array. All conversation IDs listed here will have this conversation forwarded to them.
15. "CONV-ID-HERE" should be replaced with an actual id, which looks something like "Ugxxxxxxxxxxx_xxxxxxxxxxxxx", and then commands will be forwarded to that conversation.

A cookies.txt file will also be created, holding the cookies that are valid for your login.  
  
Usage
--------------
To actually get the bot up and running, run the Main.py file. If you have Git installed, it will attempt to pull the 
most recent version from the repo. If you don't want that functionality, simply delete the os.system("git pull") line from
Main.py.  

On first load, it will ask you for an Email and Password. Input that and the bot will start.    

Upon connection, test to make sure that the bot is functioning properly by starting a chat with it and using /ping. If it replies with 'pong', you're in business! If not, manually log into the bot's gmail account and see if it didn't auto-accept the Hangouts invitation.  

Adding Functionality
-------
Any function created in the ExtraCommands.py file (or any .py that imports the DispatcherSingleton) and decorated with the @DispatcherSingle.register annotation will be automatically picked up by the bot upon next restart. Commands are very simple and should be in the style of:  

```python  
@DispatcherSingleton.register
def function_for_bot(bot, event, *args):
     if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('New Function For Bot', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /function_for_bot <required argument> <optional: optional argument>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Does a thing.')]
        bot.send_message_segments(event.conv, segments)
     else:
        # Do actual functionality here.
```  

It should be frowned upon to force a user to put underscores in to use a command, but that's up to you to decide.  
  
  
Have fun botting!

Extra
-----------
  
Special credit to:  
  
[tdryer](https://github.com/tdryer/hangups) for the wonderful Hangups API.  
[xmikos](https://github.com/xmikos/hangupsbot) for a flawless foundation and them some to build off of.  
[DocJava](https://github.com/DocJava) for support, help, and rubber ducking.
  
  
This is always going to be a work in progress, and has been built with a focus on my personal conversations, hence some of the more esoteric features. Regardless, I try to make it as accessible as possible for any one who does wish to use it. Expect a lot of changes and some weirdness.