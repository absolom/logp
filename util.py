
def load_yaml(filename):
    import yaml
    with open(filename, 'r') as f:
        data = f.read()

    return yaml.safe_load(data)

