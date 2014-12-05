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