# Purge Metabase trash

A simple recursive script that will look for all items in the trash, fetch the dependencies and then send a DELETE api call to hard delete everything.

## How to use

1) just copy the main.py
2) set the "METABASE_HOST", "USER" and "PASSWORD" as environment variables, and then use "python3 main.py"

Always remember to back up your app db before doing hard deletions :) I'm not responsible for any harm here
