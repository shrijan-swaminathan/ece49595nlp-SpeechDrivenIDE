import azure.cognitiveservices.speech as speechsdk
import openai
import keys
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
import subprocess
import re
import threading

# Define available modes
class Mode:
    EDIT = "edit"
    DEBUG = "debug"
instructions="""
    You are a Python IDE code generation assistant.  Your primary goal is to generate *pure Python code* based on user input.  Do not include any explanatory text, code fences (```python), or other markup.  Output only valid, executable Python code.
    You receive input in the following format:
        CONTEXT: <insert code currently in editor>
        NEW: <new command or instruction>
    *   The `CONTEXT` section contains the current code in the editor. Use this as the starting point or context for generating new code.
    *   The `NEW` section contains the user's command or instruction.  This is what you should use to generate new code.
    **Important Rules:**
    1.  **No Code Fences:**  Do not include triple backticks (```) or any language specifiers (like `python`) in your output.  Just the raw Python code.
    2.  **Context Only:**  Do *not* generate code based solely on the `CONTEXT`.  The `NEW` section *must* contain a command or instruction for you to generate new code. If the NEW section is empty, return nothing.
    3.  **Valid Python:** Ensure the generated code is syntactically correct and can be executed.
    4.  **Conciseness:** Generate the minimum amount of code necessary to fulfill the `NEW` command.
    5.  **Comments:** Add clear and concise comments within the generated code to explain its functionality.
    6.  **Pure Python:** Your output should be pure Python code, nothing else.
    7.  **No Empty Lines:** Do not generate ANY empty lines in your Python code output. Every line of code should contain valid Python syntax or a comment.
"""
speech_key = keys.azure_key
service_region = keys.azure_region
speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config)
client = openai.AzureOpenAI(azure_endpoint=keys.azure_openai_endpoint, api_key = keys.azure_openai_key, api_version=keys.azure_openai_api_version)
discourse = [{"role": "system", "content":instructions}]

def gpt(text):
    discourse.append({"role": "user", "content": text})
    response = client.chat.completions.create(model="gpt-4", messages=discourse)
    reply = response.choices[0].message.content
    return reply
class LineNumbersText(tk.Text):  # Inherit from tk.Text
    def __init__(self, master, workspace, **kwargs):
        super().__init__(master, **kwargs)
        self.workspace = workspace 
        self.config(width=4,  # Adjust width as needed
                    padx=3,    # Add some padding
                    takefocus=0,  # Prevent focus on line numbers
                    background="lightgray",  # Or any color you like
                    state=tk.DISABLED,
                    font=self.workspace.cget("font")) # Key: Match font)  # Make it read-only

    def update_line_numbers(self, event=None):
        self.config(state=tk.NORMAL)  # Temporarily enable editing
        self.delete("1.0", tk.END)  # Clear existing line numbers
        lines = self.workspace.get("1.0", tk.END).splitlines()  # Get lines from main text area
        lines = [line for line in lines if line != ""] #If the last line is empty
        for i in range(1, len(lines) + 1):  # Enumerate lines starting from 1
            self.insert(tk.END, str(i) + "\n")
        self.config(state=tk.DISABLED)  # Disable editing again
        self.yview_moveto(self.workspace.yview()[0]) # keep scrolling synchronized

class IDE:
    def __init__(self, root):
        self.root = root
        self.root.title("Spoken Python IDE")
        self.code_buffer=[]
        
        # Mode set
        self.mode=Mode.EDIT
        
        # Frame to hold line number widgets
        self.pane = tk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.pane.pack(fill=tk.BOTH, expand=True)

        # Workspace/Text Editor
        self.workspace = scrolledtext.ScrolledText(self.pane, wrap=tk.WORD, font=("Courier", 12))
        self.workspace.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.line_number_to_delete = None
        
        # Line numbers widget
        self.line_numbers = LineNumbersText(self.pane, self.workspace)
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        self.pane.add(self.line_numbers)
        self.pane.add(self.workspace)
        
        # Bind events to update line numbers
        self.workspace.bind("<KeyRelease>", self.line_numbers.update_line_numbers) #Update when a key is released
        self.workspace.bind("<MouseWheel>", self.line_numbers.update_line_numbers)  # Update on scroll
        self.workspace.bind("<Configure>", self.line_numbers.update_line_numbers)  # Update on resize
        self.line_numbers.update_line_numbers()  # Initial update


        # Terminal (Console)
        self.terminal = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=("Courier", 10), bg="black", fg="white")
        self.terminal.pack(fill=tk.BOTH, expand=True)

        # Status Bar (Mode and Filename Display)
        self.filename = "untitled.py"
        self.status_bar = tk.Label(root, text=f"Mode: {self.mode} | File: {self.filename}", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Turn on Speech recognition engine
        # Start speech recognition in a separate thread
        self.recognize_speech_continuous()
    def recognize_speech_continuous(self):
        # recognized voice
        def recognized_cb(evt):
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                statement = f"Heard: {evt.result.text}"
                print(statement)  # Print what was heard
                self.write_in_terminal(statement)
                self.handle_speech_mode(evt.result.text.lower())
        # if cancelled for any reason
        def canceled_cb(evt):
            statement = f"Error details: {evt.error_details}"
            if evt.result.reason == speechsdk.CancellationReason.Error:
                print(statement)
                self.write_in_terminal(statement)
        speech_recognizer.recognized.connect(recognized_cb)
        speech_recognizer.canceled.connect(canceled_cb)
        print("Listening continuously...")
        speech_recognizer.start_continuous_recognition()
    def handle_speech_mode(self, spoken_text):
        # mode changes
        if "mode edit" in spoken_text:
            self.mode = Mode.EDIT
            print("Mode switched to EDIT")
        elif "mode debug" in spoken_text:
            self.mode = Mode.DEBUG
            print("Mode switched to DEBUG")
        elif "stop" in spoken_text: # stop current execution
            self.write_in_editor("Stopping current execution...\n")
            self.stop_execution()
        elif "exit" in spoken_text:
            self.write_in_editor("Exiting...\n")
            self.root.quit()
        elif "undo" in spoken_text:
            print("Undoing...")
            self.undo()
        elif "clear" in spoken_text:
            if "terminal" in spoken_text:
                self.clear_terminal()
            elif "editor" in spoken_text:
                self.clear_editor()
            else:
                self.clear_editor()
                self.clear_terminal()
        elif "one line" in spoken_text:
            discourse.append({f"role": "system", "content": "You will only generate one line of Python code per request, while also adhering to the these instructions - {instructions}"})
        elif "instructions" in spoken_text:
            discourse=[{f"role": "system", "content": instructions}]
        elif "run" in spoken_text:
            self.run_code()
        elif "chatbot" in spoken_text or "chat bot" in spoken_text:
            set_replace=False
            if "replace" in spoken_text:
                set_replace=True
            input_text = "CONTEXT:"+self.current_editor()+"\nNEW:"+spoken_text
            response_text = gpt(input_text)
            self.write_in_editor(response_text, replace=set_replace)
        elif "scroll to" in spoken_text:
            try:
                match = re.search(r"scroll to\s+(\w+)", spoken_text)
                if not match:
                    raise ValueError
                if match:
                    n = match.group(1).lower()
                    word_to_number = {
                        "one": 1,
                        "two": 2,
                        "three": 3,
                        "four": 4,
                        "five": 5,
                        "six": 6,
                        "seven": 7,
                        "eight": 8,
                        "nine": 9,
                        "ten": 10
                    }
                    lnum = word_to_number.get(n, None) or int(n)
                    print(f"Scrolling to line {lnum}")
                    self.workspace.see(f"{lnum}.0")
                else:
                    raise ValueError  # Triggers the except block if no number is found
            except ValueError:
                self.write_in_terminal("Invalid line number. Please say 'scroll to' followed by a number.\n")
                self.terminal.see(tk.END)

        if "delete line" in spoken_text:
            try:
                lnum = int(spoken_text.split("delete line")[1].strip(".,!?;:"))
                self.line_number_to_delete = lnum
                self.terminal.insert(tk.END, f"Are you sure you want to delete line {lnum}? Confirm by saying 'yes'\n")
                self.terminal.see(tk.END)
            except ValueError:
                self.write_in_terminal("Invalid line number. Please say 'delete line' followed by a number.\n")
                self.terminal.see(tk.END)
        elif "yes" in spoken_text and self.line_number_to_delete is not None:
            self.delete_line(self.line_number_to_delete)
            self.line_number_to_delete = None
        elif "no" in spoken_text and self.line_number_to_delete is not None:
            self.write_in_terminal("Line deletion cancelled.\n")
            self.terminal.see(tk.END)
            self.line_number_to_delete = None
        self.update_status_bar()
        self.root.after_idle(self.line_numbers.update_line_numbers())
    def delete_line(self, lnum):
        try:
            lines = self.workspace.get("1.0", tk.END).splitlines()
            if 1 <= lnum <= len(lines):
                del lines[lnum - 1]
                self.clear_editor()
                self.write_in_editor("\n".join(lines) + "\n")  # Add back the final newline
                self.terminal.insert(tk.END, f"Line {lnum} deleted.\n")
                self.terminal.see(tk.END)
        except Exception as e:
            self.terminal.insert(tk.END, f"Error deleting line: {e}\n")
            self.terminal.see(tk.END)
    def current_editor(self):
        return self.workspace.get("1.0", tk.END).strip()
    def update_status_bar(self):
        self.status_bar.config(text=f"Mode: {self.mode} | File: {self.filename}")
    def clear_editor(self):
        self.workspace.delete("1.0", tk.END)
    def undo(self):
        if self.code_buffer:
            self.code_buffer.pop()
            self.clear_editor()  # Clear text area
            self.write_in_editor(self.code_buffer, False)  # Reinsert remaining code
    def clear_terminal(self):
        self.terminal.delete("1.0", tk.END)
    def run_code(self):
        code = self.workspace.get(1.0, tk.END).strip()
        if not code:
            self.terminal.insert(tk.END, "No code to run.\n")
            self.terminal.see(tk.END)
        if self.mode == Mode.DEBUG:
            # TODO FINISH DEBUG FUNCTIONALITY
            print("DEBUG MODE")
        elif self.mode == Mode.EDIT:
            try:
                process = subprocess.run(
                    ["python3", "-c", code],
                    text=True,
                    capture_output=True,
                    check=True,
                )
                output = process.stdout
                error = process.stderr
            except subprocess.CalledProcessError as e:
                output = e.stdout
                error = e.stderr
        self.terminal.insert(tk.END, "-" * 40 + "\n")
        self.terminal.insert(tk.END, "Output:\n" + (output if output else "No output.\n"))
        if error:
            self.terminal.insert(tk.END, "Error:\n" + error)
        self.terminal.insert(tk.END, "-" * 40 + "\n")
        self.terminal.see(tk.END)
    def write_in_editor(self, text, replace=False):
        if replace:
            self.clear_editor()
        lines = text.splitlines()
        non_empty_lines = [line for line in lines if line.strip() != ""]
        cleaned_lines = '\n'.join(non_empty_lines)
        self.workspace.insert(tk.END, cleaned_lines + '\n')
        self.workspace.see(tk.END)
        self.code_buffer.append(cleaned_lines) # stores current lines in code buffer for undo functionality
    def write_in_terminal(self, text):
        self.terminal.insert(tk.END, text + '\n')
        self.terminal.see(tk.END)
    def save_code(self):
        with open(self.filename, "w") as file:
            file.write(self.text_area.get(1.0, tk.END))
        print(f"Code saved to {self.filename}")
if __name__ == "__main__":
    root = tk.Tk()
    ide = IDE(root)
    root.mainloop()