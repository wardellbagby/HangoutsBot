import collections, functools, json


class ConfigDict(collections.MutableMapping):
    """Configuration JSON storage class"""

    def __init__(self, filename, default=None):
        self.filename = filename
        self.default = None
        self.config = {}
        self.load()

    def load(self):
        """Load config from file"""
        try:
            self.config = json.loads(open(self.filename, encoding='utf-8').read(), encoding='utf-8')
        except IOError:
            self.config = {}

    def loads(self, json_str):
        """Load config from JSON string"""
        self.config = json.loads(json_str)

    def save(self):
        """Save config to file (only if config has changed)"""
        with open(self.filename, 'w') as f:
            json.dump(self.config, f, indent=2, sort_keys=True)

    def get_by_path(self, keys_list):
        """Get item from config by path (list of keys)"""
        return functools.reduce(lambda d, k: d[k], keys_list, self)

    def set_by_path(self, keys_list, value):
        """Set item in config by path (list of keys)"""
        self.get_by_path(keys_list[:-1])[keys_list[-1]] = value

    def __getitem__(self, key):
        try:
            return self.config[key]
        except KeyError:
            return self.default

    def __setitem__(self, key, value):
        self.config[key] = value

    def __delitem__(self, key):
        del self.config[key]

    def __iter__(self):
        return iter(self.config)

    def __len__(self):
        return len(self.config)
