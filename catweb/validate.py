import cerberus
import yaml

class Loader(yaml.SafeLoader):
    def __init(self, stream):
        super(Loader, self).__init__(stream)
    def include(self, node):
        return "ok"

Loader.add_constructor('!include', Loader.include)

def validate_yaml(schema_file, yaml_file):
    schema = eval(open(schema_file, 'r').read())
    v = cerberus.Validator(schema)
    doc = yaml.load(open(yaml_file, 'r').read(), Loader)
    r = v.validate(doc, schema)
    return r, v.errors

def main():
    validate_yaml('config.yaml.schema', 'config.yaml')
#    validate_yaml('config.yaml.schema', 'config.yaml-example')

if __name__ == '__main__':
    main()
