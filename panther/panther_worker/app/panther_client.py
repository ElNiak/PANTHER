import sys
from flask import Flask, request, jsonify
import requests
import argparse
import configparser
import threading
import os
import socket

from termcolor import colored, cprint
import terminal_banner

from panther_utils.panther_constant import *
from panther_utils.panther_config import update_config, update_protocol_config
from panther import *


class PFVClient:
    app = Flask(__name__)
    app.debug = True
    thread = None

    def __init__(self, dir_path=None):
        pass

    # Parse the parameters received in the request and launch the SCDG
    @app.route("/run-exp", methods=["POST"])
    def run_experiment():
        # Modify config file with the args provided in web app
        user_data = request.json
        os.chdir(SOURCE_DIR)
        PFVClient.app.logger.info("Request to start experiment with parameters:")
        PFVClient.app.logger.info(user_data)

        current_protocol = user_data["protocol"]
        exp_args = user_data["args"]
        net_args = ""

        update_config(exp_args, current_protocol)

        current_tests = user_data["tests_requested"]
        protocol_arguments = user_data["protocol_arguments"]

        update_protocol_config(protocol_arguments, current_protocol, current_tests)

        tool = PANTHER()
        try:
            PFVClient.thread = threading.Thread(
                target=tool.launch_experiments, args=([[user_data["implementation"]]])
            )
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
        r.headers["Cache-Control"] = "public, max-age=0"
        return r

    def run(self):
        PFVClient.app.run(host="0.0.0.0", port=80, use_reloader=True)

os.system("clear")
banner = """
@@@@@@@@@@@@@@@@&&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@&&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@: .~JG#&@@@@@@@@@@@@@@@@@@@@@@@@@@&BJ~. .&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@G   .::: :?5G57~:.........:^!YG5J^.:^:.   5@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@G :.  :~                           ^:  .: Y@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@& .:  ^    .                   .    ^  :. #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@7   .:  .     .^.        ~:     .  ..   ~@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@7      ~~^.  ^7^::~ ~::^7^  .^~~.     !&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@7     :!~??~. :?!: .!?^ .~??~~^     :@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@J       .Y5~7J7..^   ^..7J?^YY.       ^&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@^   .   . !P7!^. .~. .^.  ~7!5~ .   :  ..B@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@:.  :~   !^  .:^^  .^.^.  ^^:.  ^J.  ^^  :.#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@P.^  ?^    ..:: :^.       .^^ .:.:.   .J  :~!@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@Y^^  5!    :??.  7!!?7!7J7!?.  ??^    ^5. :!!@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@#.!  Y5.   :J:^:  ..~P75!..  :^:?^   .YY  ~:G@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@?:. .YY7^. ~^^^^    ...    :^^^!  .!5Y: .: P@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@...  J557 .7:.     .:..    .:7. !5Y~  .^  .@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@5  ^7.~55.... ^B5:!?YY57!^J#! ....5. .77 .. Y@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@P :~ .7Y55.  . !@&:!!^.^!!:#@? .  ~Y7JJ^  :Y. #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@J .YJ   .^7:    .^G?5YJ^?J5?G~.    ~~^.     ^5!.?@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@! :Y!             .~~!YYJYY7~~.         .     J5Y.^@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@7 ^5~  :~         .JG!^~:.:~~~GY.         7!:^?5555 .@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@5  Y5  .P~        .5!!: ^~:~^ .!~Y.         ~J555555^ ~@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@   Y5!:?57         ?^  .::.::.  :J.            .:!55^  B@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@G   .?5555~          :!^.      .~:        J:       :5^  7@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@Y    .555^      ..     .^~~~~^:.          :~~:.     ~7  !@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@#      !P7     .!J^                            :?^    :. .@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@.       ~?    .Y^                         ....  :^        !@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@P     .   ..   ::                      ^~::....::^^.        .&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@~     ~J        !                  .:::^.           ^^.       .&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@&.      ~57.     !7        .....::::::.           .:             ?@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@.         .^~^   :.     .!?#^ .:...                              .@@@@@@@@@@@@@@@@@@@@@@@@@@#J7P@
@@!             :J:        :~G^ .?#~   .:..         :...             @@@@@@@@@@@@@@@@@@@@&G5J~.    P
@&               :5.        .. .7#!  .^^~   .:.    ^^                @@@@@@@@@@@@@@@@#7.           G
@Y              .757            !    .?&#..:.    .~     ..           &@@@@@@@@@@@@@#:            .P@
@J              ....!J?^             ^G:  ~GG  .::      .:^:.        &@@@@@@@@@@@@5         .^75#@@@
@@:..                :~?!::.         .    PJ^..            ...      Y@@@@@@@@@@@@&        :#@@@@@@@@
@@@^ .                :   ~~...          ..                      JG#@@@@@@@@@@@@@#        &@@@@@@@@@
@@@@?.                ..:.5&G.:                                  G@@@@@@@@@@@@@@@@:       &@@@@@@@@@
@@@@@&5~.         ::  .  :.:J?.                                 ^ .~P&@@@@@@@@@@@@&       7@@@@@@@@@
@@@@@@@@@&^       .  .~.                                        ^   .~J#@@@@@@@@@@@B    .  ?@@@@@@@@
@@@@@@@@@@B        : ^G#B! .                    5&.             ^     :^7&@@@@@@@@@@J   :.  P@@@@@@@
@@@@@@@@@@@Y   .^   :.  .7PP&B!                 @@J^.          ^        ::B@@@@@@@@@&   .   :@@@@@@@
@@@@@@@@@@@@&. :^  .    :&@@@@@P.               ^&P.~         ~~GY^.     ..P@@@@@@@@J    !. .@@@@@@@
@@@@@@@@@@@@@7     G&B! J@@@@@@@@?                : .^:.     ~~B@@@5.     . :JGBBBY:    ^P: J@@@@@@@
@@@@@@@@@@@@@P.  ~7: :5G5G@@@@@@@@@Y            .:    ~..    .:5@@@@&~    ..           .Y? ~@@@@@@@@
@@@@@@@@@@@@@@&? .YB?^G@@@@@@@@@@@@@&?           :    7        .@@@@@@G:   .^:.      .~J!.5@@@@@@@@@
@@@@@@@@@@@@@@@@&P7^?G5@@@@@@@@@@@@@@@&Y~:::~: .::    !         P@@@@@@@B~    :^^^^~!!~~5@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@&5!:   .!         .&@@@@@@@@@#57~^^^~~7Y-#@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@#!  ~    .  .   !@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@&7..        :! #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@!!:.  .: :^~ &@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@&?.^?7~7YJ. !@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@&. .^. ::  .7&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@# :.        :#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@P 7.    ..!~ ?@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@J.~         5@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@#!   ..:^~G@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@&BPYYG&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
                                            Made with ❤️ 
                                For the Community, By the Community   

                                ###################################
                    
                                        Made by ElNiak
                linkedin  - https://www.linkedin.com/in/christophe-crochet-5318a8182/ 
                                Github - https://github.com/elniak
                                                                                      
"""

banner_terminal = terminal_banner.Banner(banner)
cprint(banner_terminal, "green", file=sys.stderr)


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
