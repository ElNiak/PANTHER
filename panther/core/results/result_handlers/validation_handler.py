
from core.results.result_handler import ResultHandler


class ValidationHandler(ResultHandler):
    """
    A handler class for validating experiment results according to the environment 
    and the implementation under test.
    Attributes:
        validator: An instance of a validator that will be used to validate the request.
    Methods:
        handle(request):
            Validates the given request using the validator instance.
    """
    
    def __init__(self, validator) -> None:
        self.validator = validator
        
    def handle(self, request) -> None:
        self.validator.validate(request)