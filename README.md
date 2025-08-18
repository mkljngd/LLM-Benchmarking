
# Performance Benchmarking of LLM's

1. Download and setup **Ollama**: https://ollama.ai
2. Select **LLM models**: https://ollama.ai/library. Run the download commands for specific model found on the website
3. Create a new virtual environment using: ***python3 -m venv env***
4. Activate the env using: ***source env/bin/activate*** 
5. Install requirements inside env: ***pip install -r requirements.txt***
6. Create a postgres database and update postgres database credentials inside settings.py file
7. Create and run migration files and  ***python manage.py makemigrations; python manage.py migrate***
8. Run the init_database.py file according to downloaded models and questions to be asked
*Optional Step*: Set powermetrics to run with elevated permissions without need for password - https://blog.robe.one/display-cpu-energy-consumption-on-apple-silicon-with-python
9. Run Django server ***python manage.py runserver***
10. To run all the questions and save the responses in DB for plotting:

    a. Run: `python manage.py shell`
    b. Run `from llm.views import simulate, plot; simulate(); plot()`
