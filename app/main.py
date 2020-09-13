import os
import email
import imaplib
import logging
import traceback
from time import sleep
from typing import Tuple
from pathlib import Path
from functools import wraps

# Global variables
SERVER = os.environ.get('FASTMAIL_IMAP_HOST', 'imap.fastmail.com')
PORT = os.environ.get('FASTMAIL_IMAP_PORT', 993)
USER = os.environ.get('FASTMAIL_USER')
PASSWORD = Path('/run/secrets/fastmail_passwd').read_text()
REFRESH_RATE = int(os.environ.get('REFRESH_RATE', 10))
UID_SET = set()
MAILBOX_PATH = os.environ.get('MAILBOX_PATH', '/mailbox')
MAILBOX_HOME = os.environ.get('MAILBOX_HOME', 'home')
# Logging config
logging.basicConfig(format='[*] %(levelname)s: %(message)s', level=os.environ.get("LOGLEVEL", "INFO"))


def log(msg):
    """
    Decoratorm for printing a message before running function
    :param msg: Message to be printed before running function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logging.info(msg)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def set_uid_track_file(file: str = '.uid_track') -> None:
    """
    Creates or loads a .uid_track file to prevent emails to be written twice.
    If the app restarts (or simply fetches again emails), it will assume that the emails
    written on the volume are new ones, hence, assigning [number] sufix to them.
    By tracking their uid we prevent them to be doubly written.
    """
    global UID_SET
    file = os.path.join(MAILBOX_PATH, file)
    try:
        with open(file, 'r') as fd:
            UID_SET = set(line.strip() for line in fd.readlines())
    except FileNotFoundError:
        pass


@log('Connecting to IMAP server')
def get_imap_connection() -> imaplib.IMAP4_SSL:
    """
    Get IMAP4 connection object with 'INBOX' mailbox selected

    :return: maplib.IMAP4_SSL object
    """
    connection = imaplib.IMAP4_SSL(SERVER, PORT)
    connection.login(USER, PASSWORD)
    connection.select()  # selects INBOX by default

    return connection


@log('Parsing header fields')
def parse_header_fields(connection: imaplib.IMAP4_SSL, email_index: str) -> Tuple[str, str, tuple, str]:
    """
    Parses HEADER fields sender, subject, date and Message-Id (as uid) from RFC822 standard

    :param connection: Connection to IMAP server
    :param email_index: Number from index list of emails
    :return: (sender, subject, date, uid)
    """
    typ, data = connection.fetch(email_index, '(RFC822)')
    if typ != 'OK':
        raise imaplib.IMAP4.error(f'Server replied with {typ} on email {email_index} while parsing the headers')

    msg = email.message_from_bytes(data[0][1])
    sender = email.utils.parseaddr(msg['From'])[1]
    subject = msg["Subject"]
    date = email.utils.parsedate(msg['date'])
    uid = msg['Message-ID']

    return sender, subject, date, uid


@log('Parsing email body')
def parse_body(connection: imaplib.IMAP4_SSL, email_index: str) -> str:
    """
    Parses email body without attachments

    :param connection: Connection to IMAP server
    :param email_index: Number from index list of emails
    :return: body str
    """
    typ, data = connection.fetch(email_index, '(UID BODY[TEXT])')
    if typ != 'OK':
        raise imaplib.IMAP4.error(f'Server replied with {typ} on email {email_index} while parsing the body')

    body = email.message_from_bytes(data[0][1]).as_string()
    body = remove_html_from_body(body)
    return body


@log('Erasing HTML from raw email body')
def remove_html_from_body(body: str) -> str:
    """
    Email body is duplicated with HTML part, this function removes the HTML part if exists and it's duplicated.

    :param body: email body
    :return: body str
    """
    body_split = body.split('\n')
    uid = body_split[1]
    index = len(body_split)
    for i, line in enumerate(body_split):
        if uid == line:
            index = i
    parsed_body = '\n'.join(body_split[:index])
    if parsed_body:
        return parsed_body

    return body


@log('Writing to file')
def write_to_file(file: str, body: str, uid: str, index: int = 0) -> str:
    """
    Write body content to file and name it after it's subject
    If the file doesn't exist the algorithm will create a new file with a number between square brackets
    based on their uid.

    :param file: email file name
    :param body: email body
    :param uid: email unique identifier
    :param index: index to be added to file name if it already exists
    :return: final email file name str
    """

    _file = os.path.join(MAILBOX_PATH, file)
    if not os.path.isfile(_file):
        logging.info(f'New email: {_file}')
        with open(_file, 'w+') as fd:
            fd.write(body)
            update_uid_track_file(uid)
    else:
        file_split = file.rsplit('[', 1)[0]
        new_index = index + 1
        new_file = f'{file_split}[{new_index}]'  # format "subject[1]"
        file = write_to_file(file=new_file, body=body, uid=uid, index=new_index)  # recursion

    return file


@log('Adding new uid to uid_track file')
def update_uid_track_file(uid: str, file: str = '.uid_track') -> None:
    """
    Updates uid_track file with newly fetched uid's

    :param uid: email unique identifier
    :param file: uid_track file path
    """
    file = os.path.join(MAILBOX_PATH, file)
    with open(file, 'a+') as fd:
        fd.write(f'{uid}\n')
        logging.info(f'New {uid} added')
        UID_SET.add(uid)


@log('Creating fs hardlink tree')
def create_fs_hardlink_tree(email_path: str, dest: str) -> None:
    """
    Create directories and hardlinks at their end's according to their destination.

    :param email_path: path to where email is saved
    :param dest: path to where the hardlink will be created
    """
    if not os.path.isdir(dest):
        logging.info(f'Directory at {dest} already exists. Nothing to do')
        os.makedirs(dest)

    dest_path = os.path.join(dest, email_path)
    src_path = os.path.join(MAILBOX_PATH, email_path)
    print(f'[*****] Path is {dest_path}')
    if not os.path.isfile(dest_path):
        logging.info(f'Creating path at {dest_path}')
        Path(src_path).link_to(dest_path)


def main():
    try:
        connection = get_imap_connection()
        typ, _data = connection.search(None, 'ALL')
        if typ != 'OK':
            raise imaplib.IMAP4.error(f'Server replied with {typ}')

        # Loop on every email fetched
        for email_index in _data[0].split():
            # Parse data
            sender, subject, date, uid = parse_header_fields(connection, email_index)

            if uid in UID_SET:
                logging.info('No new emails')
                continue
            # Parse body
            body = parse_body(connection, email_index)

            # create file at base level MAILBOX_PATH
            file = f'{sender}-{subject}'
            email_path = write_to_file(file=file, body=body, uid=uid)

            # create dir and symlink to email for /timeline/{year}/{month}/{day}/
            dest_date = os.path.join(MAILBOX_PATH, MAILBOX_HOME, 'timeline/{}/{}/{}/'.format(*date))
            create_fs_hardlink_tree(email_path=email_path, dest=dest_date)

            # create dir and symlink to email for /sender/{email}/
            dest_sender = os.path.join(MAILBOX_PATH, MAILBOX_HOME, 'sender/{}/'.format(sender))
            create_fs_hardlink_tree(email_path=email_path, dest=dest_sender)

            # TODO '/topics/{IMAP folder path}/'

        _ = connection.close()  # ('OK', [b'Completed'])
        _ = connection.logout()  # ('BYE', [b'LOGOUT received'])
    except imaplib.IMAP4.error:
        traceback.print_exc(limit=1)


if __name__ == '__main__':
    set_uid_track_file()
    while True:
        main()
        sleep(REFRESH_RATE)
