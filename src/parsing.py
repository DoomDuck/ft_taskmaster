import yaml

from yaml.loader import SafeLoader


def read_and_write_one_block_of_yaml_data(filename):
    with open(f'{filename}.yaml', 'r') as f: 
        data = yaml.load(f, Loader=SafeLoader)
    programmesList = data['programmes']
    for programme in programmesList:
        print(programme)
read_and_write_one_block_of_yaml_data('test')
