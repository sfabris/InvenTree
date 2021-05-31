# -*- coding: utf-8 -*-

from shutil import copyfile
import os
import json
import sys

try:
    from invoke import ctask as task
except:
    from invoke import task


def apps():
    """
    Returns a list of installed apps
    """

    return [
        'barcode',
        'build',
        'common',
        'company',
        'label',
        'order',
        'part',
        'report',
        'stock',
        'InvenTree',
        'users',
    ]


def localDir():
    """
    Returns the directory of *THIS* file.
    Used to ensure that the various scripts always run
    in the correct directory.
    """
    return os.path.dirname(os.path.abspath(__file__))


def managePyDir():
    """
    Returns the directory of the manage.py file
    """

    return os.path.join(localDir(), 'InvenTree')


def managePyPath():
    """
    Return the path of the manage.py file
    """

    return os.path.join(managePyDir(), 'manage.py')


def manage(c, cmd, pty=False):
    """
    Runs a given command against django's "manage.py" script.

    Args:
        c - Command line context
        cmd - django command to run
    """

    c.run('cd "{path}" && python3 manage.py {cmd}'.format(
        path=managePyDir(),
        cmd=cmd
    ), pty=pty)


@task
def install(c):
    """
    Installs required python packages
    """

    # Install required Python packages with PIP
    c.run('pip3 install -U -r requirements.txt')

    # If a config.yaml file does not exist, copy from the template!
    CONFIG_FILE = os.path.join(localDir(), 'InvenTree', 'config.yaml')
    CONFIG_TEMPLATE_FILE = os.path.join(localDir(), 'InvenTree', 'config_template.yaml')

    if not os.path.exists(CONFIG_FILE):
        print("Config file 'config.yaml' does not exist - copying from template.")
        copyfile(CONFIG_TEMPLATE_FILE, CONFIG_FILE)


@task
def shell(c):
    """
    Open a python shell with access to the InvenTree database models.
    """

    manage(c, 'shell', pty=True)

@task
def worker(c):
    """
    Run the InvenTree background worker process
    """

    manage(c, 'qcluster', pty=True)

@task
def superuser(c):
    """
    Create a superuser (admin) account for the database.
    """

    manage(c, 'createsuperuser', pty=True)

@task
def check(c):
    """
    Check validity of django codebase
    """

    manage(c, "check")

@task
def wait(c):
    """
    Wait until the database connection is ready
    """

    manage(c, "wait_for_db")

@task
def migrate(c):
    """
    Performs database migrations.
    This is a critical step if the database schema have been altered!
    """

    print("Running InvenTree database migrations...")
    print("========================================")

    manage(c, "makemigrations")
    manage(c, "migrate")
    manage(c, "migrate --run-syncdb")
    manage(c, "check")

    print("========================================")
    print("InvenTree database migrations completed!")


@task
def static(c):
    """
    Copies required static files to the STATIC_ROOT directory,
    as per Django requirements.
    """

    manage(c, "prerender")
    manage(c, "collectstatic --no-input")


@task(pre=[install, migrate, static])
def update(c):
    """
    Update InvenTree installation.

    This command should be invoked after source code has been updated,
    e.g. downloading new code from GitHub.

    The following tasks are performed, in order:

    - install
    - migrate
    - static
    """
    pass

@task(post=[static])
def translate(c):
    """
    Regenerate translation files.

    Run this command after added new translatable strings,
    or after adding translations for existing strings.
    """

    # Translate applicable .py / .html / .js files
    manage(c, "makemessages --all -e py,html,js --no-wrap")
    manage(c, "compilemessages")

    path = os.path.join('InvenTree', 'script', 'translation_stats.py')

    c.run(f'python {path}')

@task
def style(c):
    """
    Run PEP style checks against InvenTree sourcecode
    """

    print("Running PEP style checks...")
    c.run('flake8 InvenTree')

@task
def test(c, database=None):
    """
    Run unit-tests for InvenTree codebase.
    """
    # Run sanity check on the django install
    manage(c, 'check')

    # Run coverage tests
    manage(c, 'test', pty=True)

@task
def coverage(c):
    """
    Run code-coverage of the InvenTree codebase,
    using the 'coverage' code-analysis tools.

    Generates a code coverage report (available in the htmlcov directory)
    """

    # Run sanity check on the django install
    manage(c, 'check')

    # Run coverage tests
    c.run('coverage run {manage} test {apps}'.format(
        manage=managePyPath(),
        apps=' '.join(apps())
    ))

    # Generate coverage report
    c.run('coverage html')


def content_excludes():
    """
    Returns a list of content types to exclude from import/export
    """

    excludes = [
        "contenttypes",
        "sessions.session",
        "auth.permission",
        "error_report.error",
        "admin.logentry",
        "django_q.schedule",
        "django_q.task",
        "django_q.ormq",
        "users.owner",
    ]

    output = ""

    for e in excludes:
        output += f"--exclude {e} "

    return output


@task(help={'filename': "Output filename (default = 'data.json')"})
def export_records(c, filename='data.json'):
    """
    Export all database records to a file
    """

    # Get an absolute path to the file
    if not os.path.isabs(filename):
        filename = os.path.join(localDir(), filename)
        filename = os.path.abspath(filename) 

    print(f"Exporting database records to file '{filename}'")

    if os.path.exists(filename):
        response = input("Warning: file already exists. Do you want to overwrite? [y/N]: ")
        response = str(response).strip().lower()

        if response not in ['y', 'yes']:
            print("Cancelled export operation")
            sys.exit(1)

    tmpfile = f"{filename}.tmp"

    cmd = f"dumpdata --indent 2 --output {tmpfile} {content_excludes()}"

    # Dump data to temporary file
    manage(c, cmd, pty=True)

    print("Running data post-processing step...")

    # Post-process the file, to remove any "permissions" specified for a user or group
    with open(tmpfile, "r") as f_in:
        data = json.loads(f_in.read())

    for entry in data:
        if "model" in entry:

            # Clear out any permissions specified for a group
            if entry["model"] == "auth.group":
                entry["fields"]["permissions"] = []

            # Clear out any permissions specified for a user
            if entry["model"] == "auth.user":
                entry["fields"]["user_permissions"] = []

    # Write the processed data to file
    with open(filename, "w") as f_out:
        f_out.write(json.dumps(data, indent=2))

    print("Data export completed")


@task(help={'filename': 'Input filename'})
def import_records(c, filename='data.json'):
    """
    Import database records from a file
    """

    # Get an absolute path to the supplied filename
    if not os.path.isabs(filename):
        filename = os.path.join(localDir(), filename)

    if not os.path.exists(filename):
        print(f"Error: File '{filename}' does not exist")
        sys.exit(1)

    print(f"Importing database records from '{filename}'")

    # Pre-process the data, to remove any "permissions" specified for a user or group
    tmpfile = f"{filename}.tmp.json"

    with open(filename, "r") as f_in:
        data = json.loads(f_in.read())

    for entry in data:
        if "model" in entry:

            # Clear out any permissions specified for a group
            if entry["model"] == "auth.group":
                entry["fields"]["permissions"] = []

            # Clear out any permissions specified for a user
            if entry["model"] == "auth.user":
                entry["fields"]["user_permissions"] = []

    # Write the processed data to the tmp file
    with open(tmpfile, "w") as f_out:
        f_out.write(json.dumps(data, indent=2))

    cmd = f"loaddata {tmpfile} -i {content_excludes()}"

    manage(c, cmd, pty=True)

    print("Data import completed")

@task
def import_fixtures(c):
    """
    Import fixture data into the database.

    This command imports all existing test fixture data into the database.

    Warning:
        - Intended for testing / development only!
        - Running this command may overwrite existing database data!!
        - Don't say you were not warned...
    """

    fixtures = [
        # Build model
        'build',

        # Common models
        'settings',

        # Company model
        'company',
        'price_breaks',
        'supplier_part',

        # Order model
        'order',

        # Part model
        'bom',
        'category',
        'params',
        'part',
        'test_templates',

        # Stock model
        'location',
        'stock_tests',
        'stock',

        # Users
        'users'
    ]

    command = 'loaddata ' + ' '.join(fixtures)

    manage(c, command, pty=True)


@task(help={'address': 'Server address:port (default=127.0.0.1:8000)'})
def server(c, address="127.0.0.1:8000"):
    """
    Launch a (deveopment) server using Django's in-built webserver.

    Note: This is *not* sufficient for a production installation.
    """

    manage(c, "runserver {address}".format(address=address), pty=True)
