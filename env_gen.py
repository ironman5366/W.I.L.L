"""
Generate the necessary env.list file
"""
import sys
import getpass
import os

if os.path.isfile(".env"):
    print(".env already exists, doing nothing")
    sys.exit(0)

if len(sys.argv) >= 2:
    db_username = sys.argv[1]
    db_password = sys.argv[2]
    db_url = sys.argv[3]
    secret_key = sys.argv[4]
else:
    db_username = input("DB username:")
    db_password = getpass.getpass("DB password:")
    db_url = input("DB URL:")
    secret_key = getpass.getpass("Secret key:")

os.environ.putenv("DB_USERNAME", db_username)
os.environ.putenv("DB_PASSWORD", db_password)
os.environ.putenv("DB_URL", db_url)
os.environ.putenv("SECRET_KEY", secret_key)

# Write everything to "env.list"
template = """
DB_USERNAME={0}
DB_PASSWORD={1}
DB_URL={2}
SECRET_KEY={3}
""".format(db_username, db_password, db_url, secret_key)
with open(".env", 'w') as f:
    f.write(template)
print("Finished")