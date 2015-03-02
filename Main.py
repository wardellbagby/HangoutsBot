import os

from Core.Bot import HangoutsBot

base_config = '''{
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
}'''

if __name__ == "__main__":

    # This commands auto updates the project. Please have Git installed and in your PATH variable on Windows.
    os.system("git pull")
    if os.path.isfile("config.json"):
        HangoutsBot("cookies.txt", "config.json").run()
    elif os.path.isfile("Core" + os.sep + "config.json"):
        HangoutsBot("Core" + os.sep + "cookies.txt", "Core" + os.sep + "config.json").run()
    else:
        print("Error finding config.json file. Creating default config file in at Core/config.json")
        config_file = open("Core" + os.sep + "config.json", 'w+')
        config_file.writelines(base_config)
        config_file.close()
        HangoutsBot("Core" + os.sep + "cookies.txt", "Core" + os.sep + "config.json").run()