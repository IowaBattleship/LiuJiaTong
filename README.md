# Wenling LiuJiaTong

This project aims to implement a simple Wenling LiuJiaTong game. 
Wenling LiuJiaTong is popular in Wenling area of Taizhou. It consists of 6 people playing four-deck with a total of 216 cards, of which 3 people in a group are called Dujia.

# Get started!

This project is fully implemented using python(>=3.9.0).

Start server/main.py on the server, players/onlookers can connect to start game.

Now we have implemented reconnecting mechanism, it use local cookie to resume. 

+ For server: Now it can serve forever for every game and don't need to restart if anything ok.
+ For client: So if you want to execute multiple clients on one machine, you need to add `-n` flag to disable local cookie. Also the last client cookie will be saved and other cookies will disappear.

```shell
# start server
python3 ./server
# start client
python3 ./client
# start multiple clients on one machine
python3 ./client -n
```

# Multi-platform

This game can be run on Windows/Linux/Mac, but needs underlying terminal to support ANSI escape code.

There are something you need to care before playing.

+ `Windows`: It's recommanded to use `Windows Terminal`, you can find it in Microsoft software store. `Cmd/Powershell` before Windows10 doesn't support ANSI escape code.
+ `Linux`: There is nothing needs to care for now.
+ `Mac`: In some terminals, blinking text is disabled. You can enable it by checking `Preferences > Check Profiles > Text > Blinking text allowed`.

# Contributions

Contributions are very welcome!
