# wallpretty
WS2801 project, creating a mountable, interactive, LED... thing

![LED Board](images/LEDBoard.jpg)


## Files
- test.py: Runs WS2801 grid demo
- websocket-quart.py: HTTP-based control for grid
- ws2801_funcs.py: Carries some of the WS2801 functions
- Dockerfile: Attempt to make this Docker-able.  WIP.  GPIO is hard.  (-:

## Parts List
- [Raspberry Pi with breadboard, power supply, MicroSD card, etc](https://smile.amazon.com/gp/product/B07BC567TW/)
- [WS2801 LED strings](https://smile.amazon.com/gp/product/B0192VUDNG); demo build has 4 strings, 200 lights total
- [3 to 5V logic stepper](https://smile.amazon.com/gp/product/B00XW2L39K); strictly speaking, this isn't required, but you may less flicker with this included
- [Wires that plug into LED boards easily](https://smile.amazon.com/gp/product/B01EV70C78)
- [T-connectors](https://smile.amazon.com/gp/product/B07114RK67); they make powering the strings in parallel much easier

## Tools List
- [Knife for cutting Lexan/Plexi/etc](https://smile.amazon.com/gp/product/B000C027ZE)
