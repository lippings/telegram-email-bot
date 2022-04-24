import imaplib
import re
import logging

from file_io import read_yaml


def get_connection_by_file(path: str):
    cont = read_yaml(path)

    email = cont['email']
    pwd = cont['password']

    return EmailConnection(email, pwd)


def refresh_if_needed(func):
    def wrapper(self, *args, **kwargs):
        try:
            ret = func(self, *args, **kwargs)
        except self.con.error:
            logging.debug('Refreshing connection.')
            self.refresh_connection()

            ret = func(self, *args, **kwargs)

        return ret

    return wrapper


class EmailConnection:
    def __init__(self, email: str, password: str):
        if not self._validate_email(email):
            raise ValueError(f'Email {email} is not valid!')

        domain = email.split('@')[1].split('.')[0]

        domain_map = {
            'hotmail': 'outlook',
            'gmail': 'gmail'
        }

        if domain not in domain_map:
            raise ValueError(f'Domain {domain} not recognized!'
                             f'Must be one of: {",".join(domain_map.keys())}')

        logging.debug(f'Mapping domain "{domain}" to "{domain_map[domain]}"')
        self.domain = domain_map[domain]

        self.con = None
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
        self.con.login(self.email, self.password)

    def _disconnect(self):
        self.con.close()
        self.con.logout()
        self.con = None

    def _fetch_in_range(self, min_id: int, max_id: int):
        result = []
        for i in range(max_id, min_id, -1):
            res, msg = self.con.fetch(str(i), '(RFC822)')
            result.append(msg)

        return result

    def refresh_connection(self):
        self._disconnect()
        self._connect()

    @refresh_if_needed
    def fetch_last_k(self, nb_to_fetch: int, folder: str = 'Inbox'):
        status, msgs = self.con.select(folder)
        nb_msgs = int(msgs[0])

        return self._fetch_in_range(nb_msgs-nb_to_fetch, nb_msgs)

    @refresh_if_needed
    def fetch_since(self, last_fetched: int, folder: str = 'Inbox'):
        status, msgs = self.con.select(folder)
        nb_msgs = int(msgs[0])

        return self._fetch_in_range(last_fetched, nb_msgs)

# EOF
