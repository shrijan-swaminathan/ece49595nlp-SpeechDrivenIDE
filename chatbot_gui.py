import azure.cognitiveservices.speech as speechsdk
import openai
import keys
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
import subprocess
import threading

# Define available modes
class Mode:
    EDIT = "edit"
    DEBUG = "debug"

mode=Mode.EDIT
speech_key = keys.azure_key
service_region = keys.azure_region
speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config)
client = openai.AzureOpenAI(azure_endpoint=keys.azure_openai_endpoint, api_key = keys.azure_openai_key, api_version=keys.azure_openai_api_version)
discourse = [{"role": "system", 
              "content":
"""
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
"""}]

def gpt(text):
    discourse.append({"role": "user", "content": text})
    response = client.chat.completions.create(model="gpt-4", messages=discourse)
    reply = response.choices[0].message.content
    return reply

class IDE:
    def __init__(self, root):
        self.root = root
        self.root.title("Spoken Python IDE")

        # Workspace/Text Editor
        self.workspace = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=("Courier", 12))
        self.workspace.pack(fill=tk.BOTH, expand=True)

        # Terminal (Console)
        self.terminal = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=("Courier", 10), bg="black", fg="white")
        self.terminal.pack(fill=tk.BOTH, expand=True)
        self.insert_buffer = "" #Buffer to store the next insert for follow up questions (like whether to append or replace)
        self.waiting_for_text = False #Flag to indicate whether we are waiting for text
        self.waiting_for_append_replace = False # flag to choose whether to append or replace values

        # Status Bar (Mode and Filename Display)
        self.filename = "untitled.py"
        self.status_bar = tk.Label(root, text=f"Mode: {mode} | File: {self.filename}", bd=1, relief=tk.SUNKEN, anchor=tk.W)
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
        global mode
        # mode changes
        if "mode edit" in spoken_text:
            mode = Mode.EDIT
            print("Mode switched to EDIT")
        elif "mode debug" in spoken_text:
            mode = Mode.DEBUG
            print("Mode switched to DEBUG")
        elif "stop" in spoken_text: # stop current execution
            self.write_in_editor("Stopping current execution...\n")
            self.stop_execution()
        elif "exit" in spoken_text:
            self.write_in_editor("Exiting...\n")
            self.root.quit()
        elif "clear" in spoken_text:
            if "terminal" in spoken_text:
                self.clear_terminal()
            elif "editor" in spoken_text:
                self.clear_editor()
            else:
                self.clear_editor()
                self.clear_terminal()
        elif "run" in spoken_text:
            self.run_code()
        elif "chatbot" in spoken_text:
            input_text = "CONTEXT:"+self.current_editor()+"\nNEW:"+spoken_text
            response_text = gpt(input_text)
            self.write_in_editor(response_text, replace=False)
        self.update_status_bar()
    def current_editor(self):
        return self.workspace.get("1.0", tk.END).strip()
    def update_status_bar(self):
        self.status_bar.config(text=f"Mode: {mode} | File: {self.filename}")
    def clear_editor(self):
        self.workspace.delete("1.0", tk.END)
    def clear_terminal(self):
        self.terminal.delete("1.0", tk.END)
    def run_code(self):
        code = self.workspace.get(1.0, tk.END).strip()
        if not code:
            self.terminal.insert(tk.END, "No code to run.\n")
            self.terminal.see(tk.END)
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

        self.terminal.insert(tk.END, "Output:\n" + (output if output else "No output.\n"))
        if error:
            self.terminal.insert(tk.END, "Error:\n" + error)
        self.terminal.insert(tk.END, "-" * 40 + "\n")
        self.terminal.see(tk.END)
    def write_in_editor(self, text, replace=False):
        if replace:
            self.clear_editor()
        self.workspace.insert(tk.END, text + '\n')
        self.workspace.see(tk.END)
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