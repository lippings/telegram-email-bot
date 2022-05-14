import imaplib
import re
import logging
import datetime
from typing import List, Optional, Callable, Union

from file_io import read_yaml

MSG_FIELDS = ['From', 'Message-ID', 'Subject', 'To', 'Date', 'Content-Type']
MSG_REGEX = {
    f: re.compile(f'{f}\:\s(?P<value>[^\n\r]+)\r?\n') for f in MSG_FIELDS
}

DOMAIN_MAP = {
    'hotmail': 'outlook',
    'gmail': 'gmail'
}


def get_connection_by_file(path: str):
    cont = read_yaml(path)

    email = cont['email']
    pwd = cont['password']

    return EmailConnection(email, pwd)


def _refresh_if_needed(func):
    def wrapper(self, *args, **kwargs):
        try:
            ret = func(self, *args, **kwargs)
        except self.con.error:
            logging.debug('Refreshing connection.')
            self.refresh_connection()

            ret = func(self, *args, **kwargs)

        return ret

    return wrapper


class Message:
    def __init__(self, msg_text: str, msg_flags: str):
        self.flags = msg_flags
        self.data = {}

        for field, regex in MSG_REGEX.items():
            m = regex.search(msg_text)

            if m is None:
                logging.debug(f'Could not find value {field} in message. Using None')
                val = None
            else:
                val = m.group('value')

            self.data[field] = val

        self.id = self.data['Message-ID']
        try:
            self.date = parse_date(self.data['Date'])
        except ValueError as e:
            logging.error(f'Got ValueError when parsing date {self.data["Date"]}:')
            raise e

    def get(self, field: str, default=None) -> Optional[str]:
        return self.data.get(field, default)


def parse_date(date_str: str) -> datetime.datetime:
    date_str = date_str.replace('(UTC)', '').strip()
    return datetime.datetime.strptime(date_str, '%a, %d %b %Y %X %z')


class EmailConnection:
    def __init__(self, email: str, password: str):
        if not self._validate_email(email):
            raise ValueError(f'Email {email} is not valid!')

        domain = email.split('@')[1].split('.')[0]

        if domain not in DOMAIN_MAP:
            raise ValueError(f'Domain {domain} not recognized! '
                             f'Must be one of: {", ".join(DOMAIN_MAP.keys())}')

        logging.debug(f'Mapping domain "{domain}" to "{DOMAIN_MAP[domain]}"')
        self.domain = DOMAIN_MAP[domain]

        self.con: Optional[imaplib.IMAP4_SSL] = None
        self.email = email
        self.password = password

        self._connect()

    @staticmethod
    def _validate_email(email: str):
        m = re.match('^[\.0-9a-zA-Z]+@[a-zA-Z0-9]+\.[a-z]+$', email)
        if m is not None:
            return True
        else:
            return False

    def _connect(self):
        if self.con is None:
            self.con = imaplib.IMAP4_SSL(f'imap.{self.domain}.com')
        try:
            self.con.login(self.email, self.password)
        except self.con.error:
            raise ValueError('Could not login to email account, invalid credentials!')

    def _disconnect(self):
        if self.con.state == 'SELECTED':
            self.con.close()
        self.con.logout()
        self.con = None

    def _fetch_until(self,
                     start_ind: int,
                     cond: Callable[[Message], bool],
                     max_fetched: int = 50) \
            -> List[Message]:
        result = []
        for i in range(start_ind, start_ind-max_fetched, -1):
            res, msg_data = self.con.fetch(str(i), '(RFC822)')
            (_, msg_text), msg_flags = msg_data
            msg = Message(msg_text.decode(), msg_flags.decode())

            if cond(msg):
                result.append(msg)
            else:
                break

        return result

    def _fetch_in_range(self, min_id: int, max_id: int) -> List[Message]:
        result = []
        for i in range(max_id, min_id, -1):
            res, msg_data = self.con.fetch(str(i), '(RFC822)')
            (_, msg_text), msg_flags = msg_data
            msg = Message(msg_text.decode(), msg_flags.decode())

            result.append(msg)

        return result

    def refresh_connection(self):
        self._disconnect()
        self._connect()

    @_refresh_if_needed
    def fetch_last_k(self, nb_to_fetch: int, folder: str = 'Inbox') -> List[Message]:
        status, msgs = self.con.select(folder, readonly=True)
        nb_msgs = int(msgs[0])

        return self._fetch_in_range(nb_msgs-nb_to_fetch, nb_msgs)

    @_refresh_if_needed
    def fetch_since(self, last_fetched: Union[int, datetime.datetime], folder: str = 'Inbox') \
            -> List[Message]:
        status, msgs = self.con.select(folder, readonly=True)
        nb_msgs = int(msgs[0])

        if isinstance(last_fetched, int):
            return self._fetch_in_range(last_fetched, nb_msgs)
        elif isinstance(last_fetched, datetime.datetime):
            return self._fetch_until(
                nb_msgs, lambda msg: msg.date <= last_fetched
            )

# EOF
