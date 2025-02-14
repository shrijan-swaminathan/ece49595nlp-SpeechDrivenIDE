# ece49595nlp-SpeechDrivenIDE
1. An IDE meant to be used purely with voice.

All commands that can be currently handled:
 - Use the command `python3 chatbot_gui.py` to start the program.
 - To change modes, use the `mode one line` or `mode default` commands to switch to One Line (writes code one line at a time) or Default mode (multi-line code generation) respectively.
 - To generate python code, use the `maestro` command and say what you want coded in natural language. The code will be generated in the text editor. Say `replace` for the code to replace the code in the text editor with newer generated code.
 - the `stop` command will stop a running program.
 - the `exit` command will close the application.
 - the `save file`/`save code` command will save the code in the text editor to a file named `untitled.py` by default. say `save file/code as` followed by the name of the file to save it in (working directory only).
 - You can clear terminal and text editor using the `clear` command. if you say `clear terminal`, only the terminal will be cleared. If you say `clear editor`, only the text editor will be cleared.
 - the `run` command will run the code in the text editor. NOTE: Prints will not be flushed to the terminal until the program is finished running.
 - the `undo` and `redo` commands will undo/redo the last action in the text editor, respectively.
 - the `scroll to` command will scroll to the line number specified.
 - the `delete line` command will delete the line number specified (requiring confirmation).