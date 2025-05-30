# People-Search-Desktop-App

Package Structure for Distribution:
# CEO Finder Pro

This is the file structure for **CEO Finder Pro**, an application designed to help you find CEOs of various companies. Let's explore what each file does:

---

## Project Components

* `ceo_finder_gui.py`: This is the heart of the desktop application, providing the **graphical user interface (GUI)** you'll interact with.
* `people.py`: This file contains the **core engine** of the application. It's where the heavy lifting for searching and processing people's (and likely CEOs') information happens.
* `requirements.txt`: Essential for setting up the project, this lists all the **Python dependencies** that need to be installed for the application to run smoothly.
* `setup.bat`: If you're on a Windows machine, this is your go-to. It's a **Windows setup script** designed to automate the installation process.
* `setup.sh`: For Mac and Linux users, this is the equivalent of `setup.bat`. It's a **Mac/Linux setup script** that helps you get the application up and running.
* `.env.template`: This serves as a **template for API keys**. It indicates that the application likely relies on external services for data, and you'll need to provide your own API keys in a `.env` file (copied from this template).
* `README.md`: This is your **instruction manual**. It provides all the necessary information, from how to set up the project to how to use it.
* `sample_companies.csv`: An **example file** containing company names. This suggests the application can take a list of companies as input to find their CEOs, or it might be used for demonstration purposes.
