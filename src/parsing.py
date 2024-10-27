import yaml
import config


def read_and_write_one_block_of_yaml_data(filename):
    try:
        with open(f'{filename}.yaml', 'r') as f: 
            data = yaml.load(f, Loader=SafeLoader)
    except Exception as e :
        print ("le fichier yaml est invalide", e)
  
read_and_write_one_block_of_yaml_data('test')
