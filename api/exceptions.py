try:
    from requests.exceptions import JSONDecodeError
except:
    from json import JSONDecodeError


class LoginError(Exception):
    def __init__(self, *args: object):
        super().__init__(*args)


class FormatError(Exception):
    def __init__(self, *args: object):
        super().__init__(*args)


class MaxRollBackError(Exception):
    def __init__(self, *args: object):
        super().__init__(*args)
