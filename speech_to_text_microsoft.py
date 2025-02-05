import azure.cognitiveservices.speech as speechsdk
import openai
import keys
import time
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import subprocess

speech_key, service_region = keys.azure_key, keys.azure_region
speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)

speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config)
client = openai.AzureOpenAI(azure_endpoint=keys.azure_openai_endpoint, api_key = keys.azure_openai_key, api_version=keys.azure_openai_api_version)
discourse = [{"role": "system", "content": "I am a Python code generator that will power a spoken IDE. I will output only code in Python. I will not include sample usage."
"I will only inlcude code and nothing else, I will not include '''python'''. I will either generate one line of code as told, or generate a function."}]

def gpt(text):
    discourse.append({"role": "user", "content": text})
    response = client.chat.completions.create(model="gpt-4", messages=discourse)
    reply = response.choices[0].message.content
    return reply

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Code Editor")
        self.code_buffer = []
        
        # Create Text Area
        self.text_area = ScrolledText(root, wrap=tk.WORD, font=("Courier", 12), height=25, width=80)
        self.text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Add Buttons
        # self.generate_button = tk.Button(root, text="Generate Code", command=self.recognize_and_generate)
        # self.generate_button.pack(side=tk.LEFT, padx=10, pady=10)

        self.console_area = ScrolledText(root, wrap=tk.WORD, font=("Courier", 10), height=10, bg="black", fg="white")
        self.console_area.pack(padx=10, pady=(5, 10), fill=tk.BOTH, expand=True)

        self.setup_continuous_recognition()

    def update_line_numbers(self, event=None):
        """ Update line numbers dynamically """
        self.line_numbers.delete("all")
        line_count = self.text_area.index("end-1c").split(".")[0]  # Get total lines
        for i in range(1, int(line_count) + 1):
            self.line_numbers.create_text(10, i * 20, anchor="nw", text=str(i), font=("Courier", 12))

    def sync_scroll(self, event):
        """ Sync scrolling between text and line numbers """
        self.line_numbers.yview_moveto(self.text_area.yview()[0])
        
    def setup_continuous_recognition(self):
        # Attach event handlers for continuous speech recognition
        speech_recognizer.recognized.connect(self.on_speech_recognized)
        speech_recognizer.canceled.connect(self.on_speech_canceled)

        # Start continuous recognition
        speech_recognizer.start_continuous_recognition()
    
   
    def on_speech_recognized(self, event):
        if event.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            text = event.result.text
            print(f"Recognized: {text}")
            if "exit" in text.lower():
                print("Exiting...")
                self.append_to_editor("Exiting...\n")
                self.root.quit()
                return
            if "run" in text.lower():
                self.run_code()
                return
            if "delete" in text.lower():
                self.delete_last_line()
                return
            if "undo" in text.lower():
                self.undo()
                return
            if "clear" in text.lower():
                self.clear_editor()
                return
            if "stop" in text.lower():
                speech_recognizer.stop_continuous_recognition()
                return
            response_text = gpt(text)
            print(f"Response: {response_text}")
            self.append_to_editor(response_text)
            self.code_buffer.append(response_text)

    def undo(self):
        if self.code_buffer:
            self.code_buffer.pop()
            self.text_area.delete("1.0", tk.END)  # Clear text area
            self.text_area.insert(tk.END, "\n".join(self.code_buffer))  # Reinsert remaining code
            

    def on_speech_canceled(self, event):
        print(f"Speech recognition canceled: {event.reason}")
        if event.reason == speechsdk.CancellationReason.Error:
            print(f"Error details: {event.error_details}")
    def append_to_editor(self, text):
        self.text_area.insert(tk.END, text + "\n")
        self.text_area.see(tk.END)
    
    def delete_last_line(self):
       lines = self.text_area.get("1.0", tk.END).split("\n")
       if len(lines) > 2:  # Ensures at least one line remains
            self.text_area.delete(f"{len(lines)-2}.0", tk.END)
            self.text_area.insert(tk.END, "\n")  # Insert a new line
            self.text_area.mark_set(tk.INSERT, f"{len(lines)-2}.0")
    
    def clear_editor(self):
        self.text_area.delete("1.0", tk.END)


    def run_code(self):
        code = self.text_area.get(1.0, tk.END).strip()
        if not code:
            self.console_area.insert(tk.END, "No code to run.\n")
            self.console_area.see(tk.END)
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

        self.console_area.insert(tk.END, "Output:\n" + (output if output else "No output.\n"))
        if error:
            self.console_area.insert(tk.END, "Error:\n" + error)
        self.console_area.insert(tk.END, "-" * 40 + "\n")
        self.console_area.see(tk.END)

     
    
    def clear_editor(self):
        self.text_area.delete("1.0", tk.END)

    def save_code(self):
        file_path = "generated_code.py"
        with open(file_path, "w") as file:
            file.write(self.text_area.get(1.0, tk.END))
        print(f"Code saved to {file_path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()



# print("Say something...")

# done = False

# while not done:
#     time.sleep(1)
#     result = speech_recognizer.recognize_once()

#     if result.reason == speechsdk.ResultReason.RecognizedSpeech:
#         print("Recognized: {}".format(result.text))
#         if "exit" in result.text.lower():
#             print("Exiting...")
#             done = True
#             break
#         response_text = gpt(result.text)
#         print("Response: {}".format(response_text))


#     # elif result.reason == speechsdk.ResultReason.NoMatch:
#     #     print("No speech could be recognized: {}".format(result.no_match_details))


#     elif result.reason == speechsdk.ResultReason.Canceled:
#         cancellation_details = result.cancellation_details
#         print("Speech Recognition canceled: {}".format(cancellation_details.reason))

#         if cancellation_details.reason == speechsdk.CancellationReason.Error:
#             print("Error details: {}".format(cancellation_details.error_details))
#         done = True

