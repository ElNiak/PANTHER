import argparse

from utils.ArgumentParserDocker import ArgumentParserDocker
from utils.ArgumentParserRunner import ArgumentParserRunner

class ArgumentParser:

    def __init__(self):        
        self.args_parser_docker = ArgumentParserDocker()
        self.args_parser_runner = ArgumentParserRunner()
        self.parser = argparse.ArgumentParser(conflict_handler='resolve',
                                parents=[self.args_parser_docker.parser,self.args_parser_runner.parser])
    
    # TODO conflict with --exp_dir and binaries arguments 
    def parse_arguments(self, allow_unk=False):
        args = None
        if not allow_unk:
            args = self.parser.parse_args() 
        else:
            args, unknown = self.parser.parse_known_args()
        return args