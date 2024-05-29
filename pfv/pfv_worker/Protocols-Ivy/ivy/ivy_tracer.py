# https://stackoverflow.com/questions/45238329/it-is-possible-to-generate-sequence-diagram-from-python-code
import os
import sys

ivy_trace = ""

class SequenceOn:
    autonumber = True
    init_done = False
    
    def __init__(self,participant=""):
        global ivy_trace
        if not SequenceOn.init_done :
            #activate if requested only once
            if SequenceOn.autonumber: 
                # content = ""
                # if os.path.exists("/ivy_trace.txt"):
                #     with open("/ivy_trace.txt", "r") as f:
                #         content = f.read()
                # with open("/ivy_trace.txt", "w") as f:
                #     f.write(content + "\nautonumber")
                ivy_trace += "\nautonumber"

            SequenceOn.init_done = True

        #retrieve callee frame
        callee_frame = sys._getframe(1)

        #method/function name
        self.__funcName = callee_frame.f_code.co_name
        
        # look for a class name
        if 'self' in callee_frame.f_locals:
            self.__className = callee_frame.f_locals['self'].__class__.__name__
        else:
            if participant != "":
                self.__className = participant
            else:
                self.__className = callee_frame.f_code.co_filename.split("/")[-1].split(".")[0]

        #retrieve the caller frame and class name of the caller
        caller_frame = sys._getframe(2)

        if 'self' in caller_frame.f_locals:
            self.__caller = caller_frame.f_locals['self'].__class__.__name__
        else:
            self.__caller = callee_frame.f_code.co_filename.split("/")[-1].split(".")[0] # ""

        #print the plantuml message
        activate = "++" if self.__caller != self.__className else ""
        content = ""
        # if os.path.exists("/ivy_trace.txt"):
        #     with open("/ivy_trace.txt", "r") as f:
        #         content = f.read()
        # with open("/ivy_trace.txt", "w") as f:
        inpu = '\n{0} -> {1} {2} : {3}'.format(self.__caller,self.__className, activate, self.__funcName)
        #     f.write(content + inpu)
        ivy_trace += inpu
        print inpu
        #print(ivy_trace)
        


    def __del__(self):
        global ivy_trace
        ''' print the return message upon destruction '''
        # if self.__caller != self.__className:
        #     if os.path.exists("/ivy_trace.txt"):
        #         with open("/ivy_trace.txt", "r") as f:
        #             content = f.read()
        #     with open("/ivy_trace.txt", "w") as f:
        #         f.write(content +'\n{0} <-- {1} -- '.format(self.__caller, self.__className))
        inpu = '\n{0} <-- {1} -- '.format(self.__caller, self.__className)
        ivy_trace += inpu
        print inpu

    def note(self,msg):
        if os.path.exists("/ivy_trace.txt"):
            with open("/ivy_trace.txt", "r") as f:
                content = f.read()
        with open("/ivy_trace.txt", "w") as f:
            f.write('note over {0}:{1}'(self.__className, msg))

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
