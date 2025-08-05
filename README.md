# LiveHoldTimeTool
A tool that shows how long a key is held for in ms.

Usage:
This tool is really just to be used when recording gameplay. The goal was to show holdtimes live, rather than rendering it after gameplay, so used simliarly to a keyoverlay.
This tool includes a clickper/second counter too.

Limitations:
Its not perfect, for some reason when you double tap exactly, they are slightly off. I believe this is a limiation with python, which, I've lowered updating times since matching a keyboards 500 or 1000hz, would make any system cry in update times. The program uses opengl to note.
Due to this, it should not be a exact representation or alternative to holdtimeanalyzer, since there is no end graph.
It uses global hotkeys, so it does not work on replays.

How to use:
Simply chose the keys you want, and click ok.
Resize how you want.

