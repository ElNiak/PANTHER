# https://stackoverflow.com/questions/45238329/it-is-possible-to-generate-sequence-diagram-from-python-code

class SequenceOn:
   autonumber = True
   init_done = False

def __init__(self,participant=""):

    if not SequenceOn.init_done :
        #activate if requested only once
        if SequenceOn.autonumber: 
            print "autonumber"

        SequenceOn.init_done = True

    #retrieve callee frame 
    callee_frame = sys._getframe(1)

    #method/function name
    self.__funcName = callee_frame.f_code.co_name

    # look for a class name
    if 'self' in callee_frame.f_locals:
        self.__className = callee_frame.f_locals['self'].__class__.__name__
    else:
        self.__className = participant

    #retrieve the caller frame and class name of the caller
    caller_frame = sys._getframe(2)

    if 'self' in caller_frame.f_locals:
        self.__caller = caller_frame.f_locals['self'].__class__.__name__
    else:
        self.__caller = ""

    #print the plantuml message
    activate = "++" if self.__caller != self.__className else ""
    print f'{self.__caller} -> {self.__className} {activate} :{self.__funcName}'


def __del__(self):
    ''' print the return message upon destruction '''
    if self.__caller != self.__className:
        print f'{self.__caller} <-- {self.__className} -- '

def note(self,msg):
    print f'note over {self.__className}:{msg}'

class SequenceOff:
    ''' empty class allowing to disable the trace by eg doing in the begining of a file:

    Seq = SequenceOn # enable sequence generation
    Seq = SequenceOff # disable sequence generation

    and using seq for tracing instead of SequenceOn
    '''
    def __init__(self,participant=""):
        pass
    def __call__(self,msg):
        pass
    def note(self,msg):
        pass
