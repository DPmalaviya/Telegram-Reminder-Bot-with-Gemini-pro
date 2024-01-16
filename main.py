import telebot
from telebot import TeleBot, types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import json
from pytz import timezone
from datetime import datetime, timedelta
from time import sleep
import threading
import google.generativeai as genai
from keep_alive import keep_alive, updated_info
keep_alive()

BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
GOOGLE_API_KEY= 'YOUR_GEMINI_PRO_API_TOKEN'

bot = telebot.TeleBot(BOT_TOKEN)
reminders_filename = 'reminders_with_jobs.json'
reminders = []
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')
context = """
Ms Manager is a Telegram bot designed by Dhruvik Malaviya to assist users in setting reminders and managing their schedules efficiently. Users can interact with the bot using commands like /set_reminder, /view_reminder, and /cancel_reminder to schedule, check, and cancel reminders. The bot supports both predefined time intervals and custom future dates for reminders.

**Key Features:**
- Reminder Setting: Users can set reminders for specific time intervals or choose custom future dates and times.
- View and Cancel Reminders: The bot allows users to view their upcoming reminders and cancel them as needed.
- Custom Time Input: Users can provide custom time expressions for setting reminders.
- AI-based Auto-Reply: The bot incorporates an auto-reply feature using a generative AI model for certain user messages.
- Customizable Reminders: Users can customize the reminder messages and timings.

**Limitations:**
Ms Manager is focused on providing responses related to reminders and scheduling. It does not perform tasks beyond its designated scope.

**Author:**
This Telegram bot was created by Dhruvik Malaviya.

**Note:**
These functionalities are limited to reminder-related queries, and the bot does not perform additional actions beyond managing reminders.

"""


def remind():
  global reminders
  while True:
    for reminder in reminders:
        now = datetime.now(timezone("Asia/Kolkata"))
        current_time = now.strftime('%d %b %I:%M %p')
        # print(current_time)
        due_time = reminder['set_time']
        title = reminder['title']
        if current_time == due_time:
            if title is None:
              bot.send_message(reminder['chat_id'], "Hey\nThis is your reminder")
            else:  
              bot.send_message(reminder['chat_id'], title)
            reminders.remove(reminder)
            save_reminders_to_json(reminders_filename, reminders)
    sleep(30)

def load_reminders_from_json(filename):
  try:
      with open(filename, 'r') as file:
          reminders = json.load(file)
      return reminders
  except FileNotFoundError:
      # If the file doesn't exist, return an empty list
      return []

def save_reminders_to_json(filename, reminders):
  print(reminders)
  with open(filename, 'w') as file:
      json.dump(reminders, file, indent=4)


def get_reminders_without_jobs(reminders):
  reminders_without_jobs = []
  for reminder in reminders:
      reminder_without_job = reminder.copy()  # Create a copy of the reminder
      if 'job' in reminder_without_job:
          del reminder_without_job['job']  # Remove the 'job' field from the copy if it exists
      reminders_without_jobs.append(reminder_without_job)
  return reminders_without_jobs


# Start command handler
@bot.message_handler(commands=['start'])
def handle_start(message):
  # Send a welcome message when the /start command is received
  bot.send_message(message.chat.id, f"""
                  Hey there, {message.from_user.first_name}! 🌟

This is the Reminder Bot! 🤖✨ I'm here to help you remember important tasks and events. You can set reminders for specific times or use predefined intervals. Let's make sure you stay on top of your schedule! 🗓️💡

Type /help to see all available commands and learn how to set reminders.""")


# Help command handler
@bot.message_handler(commands=['help'])
def handle_help(message):
  # Send a help message when the /help command is received
  help_text = f"""
Hey there, memory maestro {message.from_user.first_name}! 🎩✨


The Reminder Bot helps you stay organized by setting reminders for your tasks and events. You can quickly set reminders within the next 24 hours using simple commands. For custom reminders, just say 'Custom' and specify the time in hours. Stay productive and never forget a thing with this handy bot! 🚀


Here are the available commands:

- /start: Start the bot and get to know more about it.
- /custom: To set custom reminder to Future.
- /set_reminder: Set a reminder using predefined time intervals.
- /view_reminder: View your upcoming reminders.
- cancel_reminder: Cancel a previously set reminder.


For fastly reminders, simply specify the time in hours (e.g., '5').
"""
  bot.send_message(message.chat.id, help_text)

# set_reminder command handler
@bot.message_handler(commands=['set_reminder'])
def set_reminder(message):
  """Allows users to set a reminder using a time picker interface."""
  chat_id = message.chat.id

  # Create the keyboard with time options
  markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
  markup.row('5 minutes', '15 minutes')
  markup.row('30 minutes', '1 hour')
  markup.row('Cancel')

  # Send the message with the keyboard
  bot.send_message(chat_id, 'Please choose a time interval for the reminder:', reply_markup=markup)

# Handle the user's time choice
@bot.message_handler(func=lambda message: message.text in ['5 minutes', '15 minutes', '30 minutes', '1 hour', 'Cancel'])
def handle_time_choice(message):
  user_choice = message.text
  chat_id = message.chat.id

  if user_choice == 'Cancel':
      bot.send_message(chat_id, 'Reminder Settings Destroyed.', reply_markup=types.ReplyKeyboardRemove())
      return

  try:
      time_intervals = {
          '5 minutes': 300,
          '15 minutes': 900,
          '30 minutes': 1800,
          '1 hour': 3600,
      }

      if user_choice in time_intervals:
          due = time_intervals.get(user_choice)
          now = datetime.now(timezone("Asia/Kolkata"))
          due_datetime = now + timedelta(seconds=due)
          set_time = due_datetime.strftime('%d %b %I:%M %p')

          # Add the new reminder to the list of reminders
          reminders.append({
              'chat_id': chat_id,
              'set_time': set_time,
              'title': None,
          })
          save_reminders_to_json(reminders_filename, reminders)
          bot.send_message(chat_id, f'Reminder successfully set for {user_choice}!', reply_markup=types.ReplyKeyboardRemove())
      else:
          bot.send_message(chat_id, 'Invalid choice. Please choose a valid time interval.')

  except ValueError:
      bot.send_message(chat_id, 'Invalid input. Please enter a number.')

# view_reminder command handler
@bot.message_handler(commands=['view_reminder'])
def view_reminder(message):
  # Get the chat ID from the incoming message
  chat_id = message.chat.id

  # Create a list of user reminders, including their position (index + 1), due time, and set time
  user_reminders = []
  i = 1
  for index, reminder in enumerate(reminders, start=1):
      if reminder['chat_id'] == chat_id:
          user_reminders.append(f"{i}. Set for {reminder['set_time']}")
          i += 1

  # Check if there are any user reminders
  if user_reminders:
      txt = f'You have {len(user_reminders)} reminders..\n\n'
      txt += '\n'.join(user_reminders)
      bot.send_message(chat_id, txt)
  else:
      bot.send_message(chat_id, 'You have no reminders left...')

# cancel_reminder command handler
@bot.message_handler(commands=['cancel_reminder'])
def cancel_reminder(message):
  chat_id = message.chat.id
  user_reminders = []
  for reminder in reminders:
      if reminder['chat_id'] == chat_id:
          user_reminders.append((chat_id, reminder['set_time'])) 

  if user_reminders:
      # Create an inline keyboard with reminder options for the user to choose from
      keyboard = []
      i = 1
      for chat_id , set_time in user_reminders:
          time = set_time.replace(' ', '_')
          button_text = f"Cancel Reminder for {set_time}"
          callback_data = f'cancel_{chat_id}_{time}'
          keyboard.append([types.InlineKeyboardButton(button_text, callback_data=callback_data)])
          i += 1

      keyboard.append([types.InlineKeyboardButton("Cancel All Reminders", callback_data="cancel_all")])
      reply_markup = types.InlineKeyboardMarkup(keyboard)
      global sent_msg
      sent_msg = bot.send_message(chat_id, 'Select a reminder to cancel:', reply_markup=reply_markup)
  else:
      bot.send_message(chat_id, "You have no upcoming reminders.")


# Callback function to handle user's choice for cancelling a reminder
@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_'))
def handle_cancel_callback(call):
  chat_id = call.message.chat.id
  callback_data_parts = call.data.split('_')
  if len(callback_data_parts) == 6:
      # Extract chat ID and set time from the callback data
      extracted_chat_id = (callback_data_parts[1])
      extracted_set_time = ' '.join(callback_data_parts[2:])  
      response_text = cancel_specific_reminder(extracted_chat_id, extracted_set_time)
      bot.edit_message_text(chat_id=sent_msg.chat.id,
      message_id=sent_msg.message_id,
      text=response_text)
  elif len(callback_data_parts) == 2:
      extracted_info = (callback_data_parts[1])
      response_text = cancel_specific_reminder(chat_id, extracted_info)
      bot.edit_message_text(chat_id=sent_msg.chat.id,
      message_id=sent_msg.message_id,
      text=response_text)
  else:
      bot.send_message(chat_id, "Invalid callback data format.")

# Function to cancel a specific reminder
def cancel_specific_reminder(chat_id, set_time):
  global reminders
  try:
      if set_time == 'all':
          # Keep only the reminders that don't match the specified chat_id
          reminders = [reminder for reminder in reminders if reminder['chat_id'] != int(chat_id)]
          save_reminders_to_json(reminders_filename, reminders)
          return "All reminders have been cancelled."  
      else:
          for reminder in reminders:
              if reminder['chat_id'] == int(chat_id) and reminder['set_time'] == set_time:
                  reminders.remove(reminder)
                  save_reminders_to_json(reminders_filename, reminders)
          return f"Reminder for {set_time} canceled successfully!"

  except (IndexError, ValueError):
      return "Invalid reminder index. Please select a valid reminder to cancel."

@bot.message_handler(func=lambda message: message.text and not message.text.startswith('/') and any(op in message.text for op in ['+', '-', '*', '/']))
def for_expression(message):
  user_input = message.text
  chat_id = message.chat.id
  user_input = user_input.replace('*', ' * ').replace('/', ' / ').replace('-', ' - ').replace('+', ' + ')
  operators = ['+', '-', '*', '/']
  components = [c.strip() for c in user_input.split()]
  result = 0
  current_operator = '+'
  for comp in components:
      if comp in operators:
          current_operator = comp
      else:
          operand = float(comp)
          if current_operator == '+':
              result += operand
          elif current_operator == '-':
              result -= operand
          elif current_operator == '*':
              result *= operand
          elif current_operator == '/':
              result /= operand
  result_seconds = result * 3600
  hours = result_seconds / 3600
  now = datetime.now(timezone("Asia/Kolkata"))
  due_datetime = now + timedelta(seconds=result_seconds)
  set_time = due_datetime.strftime('%d %b %I:%M %p')

  # Add the new reminder to the list of reminders
  if result_seconds > 0:
    bot.reply_to(message, f"🚀 Reminder successfully set for {hours} hours!\nHaha! I am a genius too, bro! 😄\n\nBecause, I am made by an extremely intelligent guy! 🧠💡")
    new_reminder = {
        'chat_id': chat_id,
        'set_time': set_time,
        'title': None,
    }
    reminders.append(new_reminder)
    save_reminders_to_json(reminders_filename, reminders)
  else:
    bot.reply_to(message, "Invalid input. Please enter a positive expression.")

@bot.message_handler(func=lambda message: message.text and not message.text.startswith('/') and message.text.isdigit())
def handle_custom_time_input(message):
  chat_id = message.chat.id
  user_input = message.text

  if int(user_input) <= 24:
      try:
          # Convert the user's input to an integer (time in hours)
          hours = int(user_input)
          # Convert hours to seconds for the reminder
          due = hours * 3600

          # Calculate the due datetime and set time only once
          now = datetime.now(timezone("Asia/Kolkata"))
          due_datetime = now + timedelta(seconds=due)
          set_time = due_datetime.strftime('%d %b %I:%M %p')  # Format the set time

          # Schedule a reminder by sending a message with a delay
          bot.reply_to(message, f"🚀 Reminder successfully set for {hours} hours!\n\n⏰ Scheduled Time: {set_time}")

          # Create a new reminder
          new_reminder = {
              'chat_id': chat_id,
              'set_time': set_time,
              'title': None
          }
          # Add the new reminder to the list of reminders
          reminders.append(new_reminder)
          save_reminders_to_json(reminders_filename, reminders)
      except ValueError:
          bot.reply_to(message, 'Invalid input. Please enter a valid number of hours (only numbers).')
  else:
      bot.send_message(chat_id, f"""
Hello there, time wizard {message.from_user.first_name}! ⏳✨

So, you're ready to set a reminder? But remember, I'm a short-term memory wizard!
I can only handle reminders within a day. If you need to go beyond that,
why not fire up your time-turner or set an alarm on your phone?
If you really want to set a future reminder, you just need to use /custom command.

Magically reminding you,
Your Friendly Reminder Bot 🧙‍♂️🌟""")


SELECT_DAY, SELECT_HOUR, SELECT_MINUTE, SELECT_AM_PM, SELECT_TITLE = range(5)
# Command handler for /custom
temp_user_data = {}
days = []
hours = []
minutes = []
@bot.message_handler(commands=['custom'])
def start_custom_reminder(message):
  chat_id = message.chat.id
  today = datetime.now(timezone("Asia/Kolkata")).date()
  date_list = [today + timedelta(days=i) for i in range(29)]
  day_options = [date.strftime("%d %B") for date in date_list]
  markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
  for day in day_options:
    days.append(day)
    markup.row(day)
  bot.send_message(
      chat_id,
      "Please choose a day for the reminder:\n\nYou can also cancel this process by pressing /cancel",
      reply_markup=markup
  )

  # Set user's state to SELECT_DAY
  bot.register_next_step_handler(message, select_hour)

# Handler for selecting the hour
def select_hour(message):
  chat_id = message.chat.id
  markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
  for hour in range(1, 13):
    hours.append(hour)
    markup.row(str(hour))
  bot.send_message(
      chat_id,
      "Great! Now, please choose the hour for the reminder:\n\nYou can also cancel this process by pressing /cancel",
      reply_markup=markup
  )

  if message.text in days:
    # Store the selected day in user_data
    temp_user_data['selected_day'] = message.text
    bot.register_next_step_handler(message, select_minute)
  else:
    bot.reply_to(message, "Invalid input. Please enter a valid number for the day.\nTry again", reply_markup=types.ReplyKeyboardRemove(selective=False)) 
    # return ConversationHandler.END

# Handler for selecting the minute
def select_minute(message):
  chat_id = message.chat.id
  markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
  for minute in range(0, 60):
    minutes.append(minute)
    markup.row(str(minute))
  sleep(1)
  bot.send_message(
      chat_id,
      "Awesome! Now, please choose the minute for the reminder:\n\nYou can also cancel this process by pressing /cancel",
      reply_markup=markup
  )

  try:
    if int(message.text) in hours:
      # Store the selected hour in user_data
      temp_user_data['selected_hour'] = message.text
      bot.register_next_step_handler(message, select_am_pm)
    else:
      bot.reply_to(message, "Invalid input. Please enter a valid number for the hour in the list.\nTry again", reply_markup=types.ReplyKeyboardRemove(selective=False))
  except:
    bot.reply_to(message, "Invalid  string input. Please enter a valid number for the hour.\nTry again", reply_markup=types.ReplyKeyboardRemove(selective=False))

# Handler for selecting AM or PM
def select_am_pm(message):
  chat_id = message.chat.id
  markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
  markup.row('AM', 'PM')

  bot.send_message(
      chat_id,
      "Almost there! Please choose AM or PM:\n\nYou can also cancel this process by pressing /cancel",
      reply_markup=markup
  )

  try:
    if int(message.text) in minutes:
      # Store the selected minute in user_data
      temp_user_data['selected_minute'] = message.text
      bot.register_next_step_handler(message, prompt_for_title)
    else:
      bot.reply_to(message, "Invalid input. Please enter in minutes.\nTry again", reply_markup=types.ReplyKeyboardRemove(selective=False))
  except:
    bot.reply_to(message, "Invalid  string input. Please enter a valid number for the minutes in the list.\nTry again", reply_markup=types.ReplyKeyboardRemove(selective=False))

# Handler for prompting for title
def prompt_for_title(message):
  chat_id = message.chat.id
  bot.send_message(chat_id, "Please enter a title for your reminder:\n\nYou can also cancel this process by pressing /cancel", reply_markup=types.ReplyKeyboardRemove(selective=False))

  if message.text in ('AM' , 'PM'):
    # Store the selected AM/PM in user_data
    temp_user_data['selected_am_pm'] = message.text
    # Set user's state to SELECT_TITLE
    bot.register_next_step_handler(message, set_custom_reminder)
  else:
    bot.reply_to(message, "Invalid input. Please enter AM or PM.\nTry again" , reply_markup=types.ReplyKeyboardRemove(selective=False))
    # return ConversationHandler.END

# Handler for setting custom reminder
def set_custom_reminder(message):
  chat_id = message.chat.id
  selected_title = message.text
  # Parse selected_day and convert it to a datetime object
  selected_day = datetime.strptime(temp_user_data['selected_day'], '%d %B')

  # Extract other time components
  selected_hour = int(temp_user_data['selected_hour'])
  selected_minute = int(temp_user_data['selected_minute'])
  selected_am_pm = temp_user_data['selected_am_pm']

  # Adjust hour for PM
  if selected_am_pm == 'PM' and selected_hour < 12:
      selected_hour += 12

  due_datetime = selected_day.replace(hour=selected_hour, minute=selected_minute)
  formatted_time = due_datetime.strftime('%d %b %I:%M %p')

  # Add the custom reminder to the list
  new_reminder = {
      'chat_id': chat_id,
      'set_time': formatted_time,
      'title': selected_title
  }
  reminders.append(new_reminder)
  save_reminders_to_json(reminders_filename, reminders)
  bot.send_message(chat_id, f"Reminder successfully set for {formatted_time}!")

@bot.message_handler(commands=['cancel'])
def cancel_reminder(message):
  bot.reply_to(message, "Reminder canceled.", reply_markup=types.ReplyKeyboardRemove(selective=False))

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    # 1. Extract user's message text
    user_text = message.text
    # chat_id = message.chat.id
    prompt_template = f'''
    You are a Telegram bot named Ms Manager. You are designed to assist users in setting reminders and managing their schedules efficiently. Your task is to provide accurate and helpful responses to user queries related to reminders and scheduling. Give short answer only ranging between 200 to 300 charaters.

    Your job is to give answer to user based on the context provided below.
    Context: {context}
    User issue: {user_text}
    '''
    response = model.generate_content(prompt_template)
    outcome = response.text.replace("*", "")

    # Send a response back to the user
    bot.reply_to(message, outcome)
    # bot.send_message(chat_id, outcome)
    updated_info(f"{message.from_user.first_name}: {user_text}\nAI: {outcome}")
    # print(f"{message.from_user.first_name}: {prompt_template}\nAI: {outcome}")


threading.Thread(target=remind).start()
reminders = load_reminders_from_json('reminders_with_jobs.json')
bot.polling()
