import sys
from flask import Flask, request, jsonify
import requests
import argparse
import configparser
import threading
import os
import socket

from pfv_utils.pfv_constant import *
from pfv_utils.pfv_config import get_experiment_config, restore_config, update_config, update_protocol_config
from pfv import *

class PFVClient:
    app = Flask(__name__)
    app.debug = True
    thread = None
    
    def __init__(self,dir_path=None):                
        pass

    #Parse the parameters received in the request and launch the SCDG
    @app.route('/run-exp', methods=['POST'])
    def run_experiment():
        #Modify config file with the args provided in web app
        user_data = request.json
        os.chdir(SOURCE_DIR)
        PFVClient.app.logger.info("Request to start experiment with parameters:")
        PFVClient.app.logger.info(user_data)
        
        current_protocol = user_data['protocol']
        exp_args         = user_data['args']
        net_args         = ""

        update_config(exp_args, current_protocol)
            
        current_tests = user_data['tests']
        prot_args     = user_data['prot_args']
        
        update_protocol_config(prot_args, current_protocol, current_tests)

        tool = PFV()
        try:
            PFVClient.thread = threading.Thread(target=tool.launch_experiments, args=([[user_data['implementation']]])) 
            PFVClient.thread.daemon = True
            PFVClient.thread.start()
            return "Request successful"
        except:
            return "Something went wrong"
        
    @app.after_request
    def add_header(r):
        """
        It sets the cache control headers to prevent caching
        
        :param r: The response object
        :return: the response object with the headers added.
        """
        r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        r.headers["Pragma"] = "no-cache"
        r.headers["Expires"] = "0"
        r.headers['Cache-Control'] = 'public, max-age=0'
        return r        

    def run(self):
        PFVClient.app.run(host='0.0.0.0', port=80, use_reloader=True)


from termcolor import colored, cprint
import terminal_banner
import sys
import os
os.system('clear')
banner = ("""
                
                ░▒▓███████▓▒░░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░ 
                ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░ 
                ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░       ░▒▓█▓▒▒▓█▓▒░  
                ░▒▓███████▓▒░░▒▓██████▓▒░  ░▒▓█▓▒▒▓█▓▒░  
                ░▒▓█▓▒░      ░▒▓█▓▒░        ░▒▓█▓▓█▓▒░   
                ░▒▓█▓▒░      ░▒▓█▓▒░        ░▒▓█▓▓█▓▒░   
                ░▒▓█▓▒░      ░▒▓█▓▒░         ░▒▓██▓▒░    
                                                    
                                                    
                            Made with ❤️ 
                For the Community, By the Community   

                ###################################
       
                        Made by ElNiak
        linkedin  - https://www.linkedin.com/in/christophe-crochet-5318a8182/ 
                Github - https://github.com/elniak
                                                                                      
""")
banner_terminal = terminal_banner.Banner(banner)
cprint(banner_terminal , 'green', file=sys.stderr)
     
def main():
    app = PFVClient(SOURCE_DIR)
    app.run()
    sys.exit(app.exec_())

if __name__ == "__main__":    
    try:
        main()
    except Exception as e:
        print(e)
    finally:
        sys.stdout.close()
        sys.stderr.close() 
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__       