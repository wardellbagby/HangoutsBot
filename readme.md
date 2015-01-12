HangoutsBot
==============

Setup
--------------

In order to use this, you'll need to setup a GMail account for logging in, and a config.json file to give the bot its settings. The config file should look like:

```JSON
{
  "admins": ["USER_ID", "USER_ID", "USER_ID", "USER_ID", "USER_ID"],  
  "autoreplies": [  
    [["hi", "hello"], "Hello world!"]  
  ],
  "autoreplies_enabled": false,  
  "development_mode": false,  
  "commands_admin": ["restart", "user", "users", "hangouts", "reload", "quit", "config"],  
  "commands_enabled": true,  
  "forwarding_enabled": false,  
  "conversations": {  
    "CONV1_ID": {  
      "forward_to": [  
        "CONV2_ID"  
      ]  
    },  
    "CONV2_ID": {  
      "autoreplies_enabled": false,  
      "commands_enabled": false,  
      "forwarding_enabled": false,  
      "forward_to": [  
        "CONV1_ID"  
      ]  
    }  
  }  
}  
```

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
Any function created in the commands.py file and decorated with the command.register annotation will be automatically picked up by the bot upon next restart. Commands are very simple and should be in the style of:  

```python  
@command.register
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