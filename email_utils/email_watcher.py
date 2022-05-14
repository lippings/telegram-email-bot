import datetime
import logging
import re
from typing import Optional, Dict, Sequence, Tuple

from .email_connection import EmailConnection, Message

NB_TO_FETCH_FIRST = 10  # How many emails to fetch when initializing


class EmailWatcher:
    def __init__(self, email: str, password: str, fetch_period: int):
        self.last_fetched: Optional[datetime.datetime] = None
        self.period = fetch_period
        self.con = EmailConnection(email, password)

        self.patterns: Dict[str, Dict[str, re.Pattern]] = {}  # <pattern name>: {<field name>: <regex pattern>}

    def _send_matches(self, matches: Sequence[Tuple[Message, str]]):
        pass

    def _fetch_emails(self):
        if self.last_fetched is None:
            msgs = self.con.fetch_last_k(NB_TO_FETCH_FIRST)
        else:
            msgs = self.con.fetch_since(self.last_fetched)

        # Pattern matching
        all_matched = []
        for p_name, p_dict in self.patterns.items():
            matched = []
            for msg in msgs:
                if all(pat.search(msg.get(pat_field, '')) is not None for pat_field, pat in p_dict.items()):
                    matched.append((msg, p_name))
            all_matched.extend(matched)
            logging.info(f'Matched {len(matched)} messages for {p_name}. Sending.')

        self._send_matches(all_matched)

        self.last_fetched = max([m.date for m in msgs])

    def set_fetch_period(self, fetch_period: int):
        self.period = fetch_period

    def register_pattern(self, pattern_name: str, pattern_dict: Dict[str, re.Pattern]):
        pass

# EOF
