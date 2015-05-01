HangoutsBot
==============

Before you get started, I highly recommend you take a look at [xmikos's Hangupsbot](https://github.com/xmikos/hangupsbot) from which this is a fork of. 

Setup
--------------

In order to use this, you'll need to setup a GMail account for logging in, and a config.json file (placed either at the folder root or in the Core folder) to give the bot its settings. The config file should look something like:

```JSON
{
  "admins": ["YOUR-USER-ID-HERE"],
  "autoreplies_enabled": true,
  "autoreplies": [
    [["^@[\\w\\s]+\\++$"],"/karma {}"],
    [["^@[\\w\\s]+-+$"],"/karma {}"],
    [["bot", "robot", "Yo"], "/think {}"]
  ],
  "development_mode": false,
  "commands_admin": ["hangouts", "reload", "quit", "config", "block", "record clear"],
  "commands_conversation_admin": ["leave", "echo", "block"],
  "commands_enabled": true,
  "forwarding_enabled": false,
  "rename_watching_enabled": true,
  "conversations": {
    "CONV-ID-HERE": {
      "conversation_admin": "USER-ID-HERE",
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

If you neglect to create a config.json file, this exact one will be created for you in the Core folder.  

Line by Line breakdown (excluding braces/brackets):  
  
1. Sets the admins. Only admins can use the admin commands listed in commands_admin.  
2. Sets autoreplies to be enabled for every conversation the bot is in.  
3. Sets the autoreplies for all conversations the bot is in.  
4. Sets "Dev Mode" to default to off for all conversations. Dev Mode will force the bot to print out all of it's replies to the console window instead of replying via Hangouts.  
5. Array of all of the commands that only admins will have access to use.  Note: You can block subcommands by explictly stating the command and subcommand (as in "record clear"). You can block all subcommands by using "command \*"  
6. Array of all of the commands that only conversation admins and normal admins will have access to use.  
7. Sets commands to be enabled for all chats.  
8. Sets chat forwarding for all chats to disabled. (When enabled, you must have a conversation object with a "forward_to" member that is set to a different conversation id.)  
9. Sets rename watching to enabled. (This is required to have /record record name changes.)  
10. Start of the conversations dictionary.  
11. Start of a conversation specific dictionary. "CONV-ID-HERE" should be replaced with an actual id, which looks something like "Ugxxxxxxxxxxx_xxxxxx4AaABAQ".  
12. Sets the conversation admin for a specific conversation. Unlike the admins array on line 1, there can only be one conversation admin per conversation.  
13. Sets the autoreplies for this specific conversation, which entirely overrides any autoreplies set for all conversations.  
14. Sets an autoreply keyword and reply. In this case, "whistle", "bot", and "whistlebot" are all keywords, and the reply will be the command /think, which will be given the entirety of what the user posted. For example: A user saying "Bot, how are you?" would cause the command "/think Bot, how are you?" to be ran. NOTE: The keywords are case-insensitive.  
15. Sets another autoreply keyword and reply. In this case, if a user says "trash," the Bot will reply with "You're trash." NOTE: The keywords are case-insensitive.  
16. Start of the "forward_to" array. All conversation IDs listed here will have this conversation forwarded to them.  
17. "CONV-ID-HERE" should be replaced with an actual id, which looks something like "Ugxxxxxxxxxxx_xxxxxxxxxxxxx", and then commands will be forwarded to that conversation.  

Note: Every top-level argument can be made a conversation level argument, which will overwrite the top level argument for that conversation. For instance, if you put a commands_admin array containing only "quit" and "block" in "CONV-ID-HERE", in the CONV-ID-HERE conversation, all users would be able to run /hangouts, /reload, /config, etc but would still be blocked from running /quit and /block. Conversely, if you put an empty commands_admin array in CONV-ID-HERE, all users in that conversation would be able to run all commands (except any commands in the "commands_conversation_admin" array unless they're a conversation admin.)  

A cookies.txt file will also be created, holding the cookies that are valid for your login.  
  
Usage
--------------
To actually get the bot up and running, run the Main.py file. If you have Git installed, it will attempt to pull the 
most recent version from the repo. If you don't want that functionality, simply delete the os.system("git pull") line from
Main.py.  

On first load, it will ask you for an Email and Password for a Google Account. Input that and the bot will start.    

Upon connection, test to make sure that the bot is functioning properly by starting a chat with it and using /ping. If it replies with 'pong', you're in business! If not, manually log into the bot's gmail account and see if it didn't auto-accept the Hangouts invitation.  

Adding Functionality
-------
Any function created in the ExtraCommands.py file (or any .py file that imports the DispatcherSingleton and is manually imported in the Handlers.py file or placed in the Core/Commands folder) and decorated with the @DispatcherSingle.register annotation will be automatically picked up by the bot upon next restart. Commands are very simple and should be in the style of:  

```python  
@DispatcherSingleton.register
def command(bot, event, *args):
    """Command
    Usage: /command <required argument> <optional: optional argument> {for complicated commands, put an example call in curly braces}
    Purpose: Does a thing."""
    
    # Do actual functionality here.
```  

The docstring isn't necessary, but should be used as it will be printed out if a user uses "/help \<command name\>" or does "/\<command_name\> ?". Admin-only commands generally don't have help text by default, but that's left up to your discretion.
   
The bot variable is a reference to the HangoutsBot that is currently running. The event variable is a ConversationEvent that has information about the event (as in, text, the user who sent it, the conversation, and all users in the conversation.) The \*args variable is a tuple of all of the text sent along with the command call, split by whitespace so that you can easily check its values. Look at the DefaultCommands.py file for actual examples of how commands work.  
  
It should be frowned upon to force a user to put underscores in to use a command, but that's up to you to decide.
  
  
  
Have fun botting!

Extra
-----------
  
Special credit to:  
  
[tdryer](https://github.com/tdryer/hangups) for the wonderful Hangups API.  
[xmikos](https://github.com/xmikos/hangupsbot) for a flawless foundation and them some to build off of.  
[DocJava](https://github.com/DocJava) for support, help, and rubber ducking.
  
  
This is always going to be a work in progress, and has been built with a focus on my personal conversations, hence some of the more esoteric features. Regardless, I try to make it as accessible as possible for any one who does wish to use it. Expect a lot of changes and some weirdness.