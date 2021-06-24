import yaml


class Config:
    def load(self, config_file):
        with open(config_file, "r") as stream:
            self.config = yaml.load(stream)

    def get(self, field):
        return self.config[field]

    def get_profile(self, profile_name):
        for p in self.config["profiles"]:
            if p["name"] == profile_name:
                return p
