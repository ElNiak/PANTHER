import argparse

class ArgumentParserDocker:
    def __init__(self):        
        self.parser = argparse.ArgumentParser(conflict_handler='resolve') 
        self.group = self.parser.add_argument_group('Docker parameters')
        self.group.add_argument(
            '--build', 
            help='build the dockers (default:False)',
            action="store_true"
        )
        self.group.add_argument(
            '--delete', 
            help='delete old docker images/containers (default:False)',
            action="store_true"
        )
        self.group.add_argument(
            '--remove', 
            help='remove old docker images/containers (default:False)',
            action="store_true"
        )
        self.group.add_argument(
            '--docker_output_path', 
            help='Experiment output path (default: docker-output/)',
            type=str, 
            default="docker-output/"
        )
       
        
    def parse_arguments(self, allow_unk=False):
        args = None
        if not allow_unk:
            args = self.parser.parse_args() 
        else:
            args, unknown = self.parser.parse_known_args()
        return args
