import vosk
import sys
import os
import wave
import pyaudio
import json
import requests
import nltk
from nltk.tokenize import word_tokenize 
import fitz 
import openai
# LangChain components to use
# from langchain.vectorstores.cassandra import Cassandra
# from langchain.indexes.vectorstore import VectorStoreIndexWrapper
# from langchain_community.llms import OpenAI
# from langchain_community.embeddings import OpenAIEmbeddings
# from PyPDF2 import PdfReader
# # Support for dataset retrieval with Hugging Face
# from datasets import load_dataset
# from typing_extensions import Concatenate
# # With CassIO, the engine powering the Astra DB integration in LangChain,
# # you will also initialize the DB connection:
# from langchain.text_splitter import CharacterTextSplitter
import cassio
##################################################################################################
import pyttsx3
import serial
import time
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel
from PyQt5.QtCore import Qt, QThread
import os
import threading

engine = pyttsx3.init()
voices = engine.getProperty('voices')
    
    # Select a female voice (assuming the first available female voice)
for voice in voices:
    if "female" in voice.name.lower():
        engine.setProperty('voice', voice.id)
        break

##################################################################################################
# Download NLTK data (run this once)
nltk.download('punkt')
class VoiceAssistant:
    def __init__(self, model_path):
        self.openai_api_key = "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"  # Replace with your OpenAI API key
        openai.api_key = self.openai_api_key
        self.model = vosk.Model("C:/Users/Parasu/Desktop/Maruth/vosk-model-small-en-us-0.15")
        self.recognizer = vosk.KaldiRecognizer(self.model, 16000) 
        self.pdf_folder_path = pdf_folder_path
        self.word_to_index = {}
        
        self.arduino_event = threading.Event()  # Event to control pausing and resuming Arduino triggering
        self.arduino_paused = False  # Flag to track whether Arduino triggering is paused
        self.arduino_lock = threading.Lock()  # Lock for synchronized access to arduino_paused flag

        # Arduino communication setup
        self.serial_port = 'COM13'
        self.baud_rate = 9600
        self.arduino_connection = None
        self.setup_arduino_connection()

    def setup_arduino_connection(self):
        try:
            self.arduino_connection = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
            time.sleep(2)
            print("Arduino connection established")
        except serial.SerialException as e:
            print(f"Failed to establish Arduino connection: {e}")

    def pause_arduino(self):
        with self.arduino_lock:
            self.arduino_paused = True

    def resume_arduino(self):
        with self.arduino_lock:
            self.arduino_paused = False
            self.arduino_event.set()  # Set the event to allow the triggering to continue

    def read_file_and_return_list(self):
        linectr = 1
        path = r"C:\Users\jimve\Documents\PEC-HACKS\i.txt"
        lst = []
        with open(path, 'r') as file:
            for line in file:
                lst.append(line)
        return lst, linectr

    def trigger_arduino(self, book_name, lst_func, linectr_func, rec_flag_func):
        lst, linectr = lst_func()
        rec_flag = rec_flag_func()

        done = False
        while not done:
            with self.arduino_lock:
                if self.arduino_paused:
                    self.arduino_event.clear()  # Clear the event to pause the triggering
            self.arduino_event.wait()  # Wait until the event is set
            if self.arduino_connection and self.arduino_connection.is_open:
                try:
                    if rec_flag == 1 and linectr < len(lst):
                        message = lst[linectr]
                        linectr += 1
                        print(message)
                        self.arduino_connection.write(message.encode('utf-8'))
                        rec_flag = 0
                        time.sleep(1)
                    else:
                        line = self.arduino_connection.readline().decode('utf-8').strip()
                        if line == "574848481310":
                            rec_flag = 1
                except serial.SerialException as e:
                    print(f"Error: {e}")
                    self.arduino_connection.close()
                    break
            else:
                print("Arduino connection is not available.")
            with self.arduino_lock:
                done = self.arduino_paused

    def recognize_audio(self, audio_data):
        if self.recognizer.AcceptWaveform(audio_data):
            result = json.loads(self.recognizer.Result())
            return result.get("text", "")
        else:
            return ""

    def listen(self):
        p = pyaudio.PyAudio()

        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=16000,
                        input=True,
                        frames_per_buffer=8000)

        print("Listening...")

        while True:
            try:
                data = stream.read(8000)
                text = self.recognize_audio(data)
                if text:
                    print("You said:", text)
                    self.process_command(text)
            except KeyboardInterrupt:
                print("Stopping...")
                break

        stream.stop_stream()
        stream.close()
        p.terminate()

    def process_command(self, command):
        
        print("Processing command:", command)

        # Tokenize the command
        tokens = word_tokenize(command.lower())

        # Check if the command involves opening a PDF
        if 'open' in tokens and 'book' in tokens:
            pdf_name = self.extract_pdf_name(tokens)
            if pdf_name:
                self.open_pdf(pdf_name)
                arduino_thread = threading.Thread(target=self.trigger_arduino)
                arduino_thread.start()
            else:
                print("PDF name not specified.")
        # Check if the command involves downloading a PDF
        elif 'download' in tokens and 'book' in tokens:
            self.download_pdf() 
        elif 'extract' in tokens and 'words' in tokens:
            chapter_number = self.extract_chapter_number(tokens)
            if chapter_number:
                self.extract_words_from_pdf(chapter_number)
            else:
                print("Chapter number not specified.") 
        elif 'one' in tokens:
            # Check if 'custom_command' is present in the tokens
            prompt_index = tokens.index('one') + 1
            if prompt_index < len(tokens):
                custom_prompt = " ".join(tokens[prompt_index:])
                if custom_prompt:
                    response = self.ask_chatgpt(custom_prompt)
                    print("GPT-3.5 Response:", response)
                else:
                    print("Custom prompt not specified.")
            else:
                print("Custom prompt not specified.")

        else:
            print("Command not recognized.")
    def extract_chapter_number(self, tokens):
        # Extract the chapter number from the tokens
        extract_index = tokens.index('extract') if 'extract' in tokens else -1
        chapter_index = tokens.index('chapter') if 'chapter' in tokens else -1

        if extract_index != -1:
            if chapter_index != -1 and extract_index < chapter_index:
                chapter_number = " ".join(tokens[chapter_index + 1:])
                return chapter_number
            elif chapter_index == -1:
                # If "extract" is present but "chapter" is not, assume the next word is the chapter number
                next_word_index = extract_index + 1
                if next_word_index < len(tokens):
                    chapter_number = tokens[next_word_index]
                    return chapter_number

        return None

    def ask_chatgpt(self, question_prompt):
        messages = [{"role": "system", "content": "You are an intelligent assistant."}]
        full_prompt = f"one \"{question_prompt}\""

        try:
            messages.append({"role": "user", "content": full_prompt})
            response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
            reply = response.choices[0].message.content
            print("GPT-3.5 Response:", reply)  # Add this line for debugging
            return reply
        except Exception as e:
            print(f"Error asking GPT-3.5: {e}")
            return "I encountered an error while processing your request."
            
    def extract_pdf_name(self, tokens):
        # Extract the PDF name from the tokens
        open_index = tokens.index('open') if 'open' in tokens else -1
        pdf_index = tokens.index('book') if 'book' in tokens else -1

        if open_index != -1 and pdf_index != -1 and open_index < pdf_index:
            pdf_name = " ".join(tokens[pdf_index + 1:])
            return pdf_name
        else:
            return None

    def open_pdf(self, pdf_name):
        # Search for the specified PDF in the folder
        pdf_file_path = os.path.join(self.pdf_folder_path, f'{pdf_name}.pdf')

        try:
            os.system(f'start {pdf_file_path}')  # Windows
            # Alternatively, you can use platform-independent solutions like PyMuPDF or pdf2image.
            # For example:
            # import webbrowser
            # webbrowser.open(pdf_file_path)
        except Exception as e:
            print(f"Error opening PDF: {e}") 
    def extract_words_from_pdf(self, chapter_number):
        # Search for the specified PDF in the folder
        pdf_file_path = os.path.join(self.pdf_folder_path, 'books')  # Replace with your PDF file

        try:
            # Open the PDF file
            with fitz.open(pdf_file_path) as pdf_document:
                # Get the text of the specified chapter
                chapter_text = ''
                for page_number in range(pdf_document.page_count):
                    page = pdf_document[page_number]
                    chapter_text += page.get_text()

                # Display words from the specified chapter
                print(f"Words from Chapter {chapter_number} (integer indices):")
                words = word_tokenize(chapter_text)
                for word in words:
                    if word not in self.word_to_index:
                        self.word_to_index[word] = len(self.word_to_index)  # Assign a new index
                    print(f"{word}: {self.word_to_index[word]}")
        except Exception as e:
            print(f"Error extracting words from PDF: {e}") 



# Usage example
if __name__ == "__main__":
    pdf_folder_path = 'C:/Users/Parasu/Desktop/Maruth/books/'

    if not os.path.exists(pdf_folder_path):
        sys.exit(f"PDF folder path '{pdf_folder_path}' does not exist. Please provide the correct path.")
    
    messages = [ {"role": "system", "content": "You are a intelligent assistant."} ]
    # ASTRA_DB_APPLICATION_TOKEN = "AstraCS:ZrQuFeSAgOckaOQZBiDpnEzr:3e931e9adf46d937f52e553f7535a1b29cb1757f05065f08d52e01072925677d" # enter the "AstraCS:..." string found in in your Token JSON file
    # ASTRA_DB_ID = "2ef34ab2-038d-4d1a-aff6-d8dbd8f1711f" # enter your Database ID

    # OPENAI_API_KEY = "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" # enter your OpenAI key
    # pdfreader = PdfReader('books/name.pdf')
    
    # # read text from pdf
    # raw_text = ''
    # for i, page in enumerate(pdfreader.pages):
    #     content = page.extract_text()
    #     if content:
    #         raw_text += content
    # cassio.init(token=ASTRA_DB_APPLICATION_TOKEN, database_id=ASTRA_DB_ID)
    # llm = OpenAI(openai_api_key=OPENAI_API_KEY)
    # embedding = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
   
    # astra_vector_store = Cassandra(
    # embedding=embedding,
    # table_name="team_maruth",
    # session=None,
    # keyspace=None,
    # ) 
    
    # # We need to split the text using Character Text Split such that it sshould not increse token size
    # text_splitter = CharacterTextSplitter(
    #     separator = "\n",
    #     chunk_size = 800,
    #     chunk_overlap  = 200,
    #     length_function = len,
    # )
    # texts = text_splitter.split_text(raw_text) 
    
    # astra_vector_store.add_texts(texts[:50])

    # print("Inserted %i headlines." % len(texts[:50]))

    # astra_vector_index = VectorStoreIndexWrapper(vectorstore=astra_vector_store)

    assistant = VoiceAssistant(pdf_folder_path)
    # Example commands
    # assistant.listen()
    assistant.process_command("open book name")