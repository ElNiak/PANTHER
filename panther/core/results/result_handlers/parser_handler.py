
from core.results.result_handler import ResultHandler

class ParserHandler(ResultHandler):
    """
    A handler class for parsing experiment results according to the environment 
    and the implementation under test.
    Attributes:
        parser: An instance of a parser that will be used to parse the request.
    Methods:
        handle(request):
            Parses the given request using the parser instance.
    """
    
    def __init__(self, parser) -> None:
        self.parser = parser
        
    def handle(self, request) -> None:
        self.parser.parse(request)