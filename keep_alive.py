from flask import Flask, render_template
from threading import Thread
app = Flask(__name__)
messages = []
@app.route('/')

def index():
  temp = f'Last message from server: {messages}'
  return temp
  
def run():
  app.run(host='0.0.0.0',port=80)
  
def keep_alive():  
  t = Thread(target=run)
  t.start()
  
def updated_info(string):
  messages.append(string + "\n")
  return string
