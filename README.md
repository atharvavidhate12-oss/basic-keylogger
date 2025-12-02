Basic Keylogger (Educational Purpose Only)

A simple Python-based keylogger built strictly for learning and local system experimentation.
This project helps beginners understand how keyboard event listeners work in Python.

🚀 Features

Records all keystrokes

Detects and logs special keys (Enter, Backspace, Space, etc.)

Runs silently in the background

Saves logs to a text file

Uses the lightweight pynput library

📁 Project Structure
basic-keylogger/
│── keylogger.py
│── requirements.txt
└── README.md

🛠️ Installation
1. Install dependencies
pip install pynput

2. Run the keylogger
python keylogger.py

📌 How It Works

The script listens for keyboard events

Every key pressed is written to key_log.txt

Special keys (like Enter, Shift) are handled separately

Runs until you manually stop it (Ctrl + C)

🧪 Example Output
h e l l o   w o r l d Enter
T h i s   i s   a   t e s t Backspace

⚠️ Disclaimer

This project is strictly for educational use only.

You MUST NOT:

use it on devices without permission

use it for spying or malicious intent

The author is not responsible for any misuse.

📜 License

This project is open-source and available under the MIT License.
