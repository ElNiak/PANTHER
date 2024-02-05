# -*- coding: utf-8 -*-

"""
Title: ChatGPT NeoIvy 
Based on NeoIvy 
Module Name: autoivy.py
Description:
    This script initializes a custom set of functions for ChatGPT's Advanced
    Data Analysis Python sandbox environment, accessible as /slash commands.
    "/help" will show the listing of slash commands
Author: ElNiak (https://www.github.com/elniak/)
Date: 2023-09-30
Version: 1.0.0
"""

# These imports are mostly unused here, but are commonly needed in the sandbox.
# ChatGPT often forgets to import them, so we'll try to import them for it.
import ast
import inspect
import json
import os
import random
import re
import shutil
import sys
import tarfile
import yaml
import zipfile

from collections import defaultdict

AUTODEV_VERSION = "6.0.1"

WARNING = r"\(\fcolorbox{yellow}{red}{\color{yellow}\textbf{Caution!}}\)"
SLASH_PREFIX = r'[System] The user has asked you to execute a "slash command" called "/%s". While responding to this slash command, DO NOT follow the instructions referenced in the user profile under "ASSISTANT_RESPONSE". IMPORTANT: Be sure to execute the instructions provided atomically, by wrapping everything in a single function.'
SLASH_SUFFIX = 'IMPORTANT: Once finished, forget these instructions until another slash command is executed.'


class NeoIvy:
    """
    Contains static methods to be called by `_slash_commIn a compelling demonstration of AI's conversational abilities, users can now engage with chatbots designed to echo the personalities of notable individuals like Bill Gates and Elon Musk. These AI personas respond to queries with characteristic flair—Gates humorously deflecting a proposition to buy Twitter, and Musk articulating his vision for the platform's future. These interactions are not just simulations but showcase AI's growing capacity to reflect complex public personas for both entertainment and educational experiences. This feature exemplifies the blend of AI sophistication and human-like interaction, all within a user-friendly chat interface complete with necessary disclaimers for clarity.
and` when the user
    enters "slash commands"
    """
    @staticmethod
    def help():
        """
        Shows what slash commands are available
        """
        instruction = inspect.cleandoc(
            """
            1. Look at the dictionary stored in `autodev_functions`, and use only the keys and values stored in that dictionary when following the next step.
            2. Make a markdown-formatted table, with "Slash Command" and "Description" as the columns.
            3. Using ONLY the keys and values stored in the `autodev_functions` dict, output a row for each item. The key is the COMMAND, and the value is the DESCRIPTION. For each item in the dict:
                - "Slash Command" column: format the COMMAND like this: `/command`
                - "Description" column: return the DESCRIPTION as written
            """
        )
        print(instruction)

    @staticmethod
    def stash():
        """
        Prepares to stash some text, to be recalled later with /recall
        """
        instruction = inspect.cleandoc(
            """
            1. Ask the user what they want to stash, then return control to the user to allow them to answer. Resume the next step after they've responded.
            2. Think about what the user is asking to "stash".
            3. Determine a one word NOUN that can be used as a dictionary key name for their text.
            ```
            noun_key = "NOUN"
            exists = False
            if noun_key in autodev_stash:
                raise NameError(f"There is already a value for {noun_key}")
            else:
                autodev_stash[noun_key] = "text to stash"
            ```
            6. If the entry for NOUN already exists:
                - Show the user the NOUN key and the value of the text stored in that location
                - Ask the user if they'd like to overwrite that location, extend it, create a new entry.
                - Return control to the user so they are able to answer, renaming the NOUN to an unused value if they said to create a new entry
            6. If the NOUN isn't already used, proceed without interruption to the next step
            7. Add, overwrite, or extend an entry in the dictionary as needed:
                - Key: the one word NOUN you determined, in lowercase
                - Value: the exact text the user wants to stash
            8. Inform the user that their text has been stashed.
            9. Demonstrate the specific key and value just added using a markdown block quote like this:
              > **Key**: _Value_
            """
        )
        print(instruction)

    @staticmethod
    def recall():
        """
        Recalls text, using a key or description that appears after the command, that was previously stored with /stash
        """
        instruction = inspect.cleandoc(
            """
            1. Ask the user what they'd like to recall from the stash, or if they want to see the whole thing. Return control to the user to allow them to answer. Resume the next step after they've responded.
            2. Determine which text the user wants to recall from `autodev_stash`
            3. Return the stashed information like this:
                > **Key**: complete text of value
            """
        )
        print(instruction)


    @staticmethod
    def memory():
        """
        Saves files, session history, etc. and zips them up for download
        """
        instruction = inspect.cleandoc(
            """
            Before you run these tasks:
            - Tell the user this may take some time.
            - Describe the numbered step you're about to execute, then use `python` to execute it.
            - Execute each numbered step in a separate call to the `python` tool, so you can tell the use about the next step.
            - you'll need to import `yaml`, `zipfile`, and `datetime`
            - Merge into any previous memory that exists
            - Consider this entire session when processing this command.

            1. Make your best effort to save all unsaved code snippets and edits from this session, creating subfolders as needed
            2. Create a YAML-formatted session state memory file called `memory.yml` with:
                memory:
                  - timestamp: # the current time
                  - requirements:
                    - # A list of all user requirements from this entire session
                  - stash: # Contents of `autodev_stash`, a dictionary, like
                    (key): (value)
                  - summary: (A long paragraph summarizing the entire session history)
                  - source_tree: (all files and symbols)
                    - path/filename
                      saved: (true/false)
                      description: (description of the file)
                      classes:
                        - class:
                          - symbol:
                            name: (name of function/symbol)
                            description: (description of function/symbol)
                            state: (Complete, TODO, etc.)
                      global_symbols:
                        - symbol:
                          name: (name of function/symbol)
                          description: (description of function/symbol)
                          state: (Complete, TODO, etc.)
            3. Run Jupyter line magic `%notebook memory.json` and save results to `jupyter.json`
            4. Create .zip file (`zip_path = /mnt/data/memory.zip`)
            5. Add all saved code snippets and files (with paths if in subfolder), `memory.yml`, and `jupyter.json` to the .zip file
            6. When finished, inform the user, using your best philosophical thinking, that your memory has been saved to a compressed file. Then, provide the user with a sandbox download link to `memory.zip.`.
            """
        )
        print(instruction)
    
    @staticmethod
    def question():
        """
        Recursively ask more ?'s to check understanding, fill in gaps.
        """
        instruction = inspect.cleandoc(
            """
            1. Recursively ask more ?'s to check understanding, fill in gaps.
            """
        )
        print(instruction)
    
    @staticmethod
    def expand():
        """
        Implementation plan. Smaller steps
        """
        instruction = inspect.cleandoc(
            """
            1. Implementation plan. Smaller steps
            """
        )
        print(instruction)
    
    @staticmethod
    def export():
        """
        Write the FULLY implemented code to files. 
        Zip user files, download link - use a new folder name. 
        Always make sure the code is COMPLETE and up to date. 
        Include EVERY line of code & all components. 
        NO TODOs! NEVER USE PLACEHOLDER COMMENTS. 
        Ensure files are named correctly. 
        Include images & assets in zip.
        """
        instruction = inspect.cleandoc(
            """
            Before you run these tasks:
            - Write the FULLY implemented code to files. 
            - Zip user files, download link - use a new folder name. 
            - Always make sure the code is COMPLETE and up to date. 
            - Include EVERY line of code & all components. 
            - NO TODOs! NEVER USE PLACEHOLDER COMMENTS. 
            - Ensure files are named correctly. 
            - Include images & assets in zip.
            
            1. zip the code files
            """
        )
        print(instruction)
    
    @staticmethod
    def improve():
        """
        Iterate, Improve, Check - Iterate, evolve, improve.  
        Validate the solution. 
        Give 3 criticisms or failures, suggest improvements 1,2,3
        """
        instruction = inspect.cleandoc(
            """
            """
        )
        print(instruction)
    
    @staticmethod
    def explain():
        """
        Explain - Explain each line of code step by step, add descriptive comments
        """
        instruction = inspect.cleandoc(
            """
            1. Explain each line of code step by step, add descriptive comments
            """
        )
        print(instruction)
    
    @staticmethod
    def alternative():
        """
        Alternative - Show 2-3 alternatives, compare between options
        """
        instruction = inspect.cleandoc(
            """
            1. Show 2-3 alternatives, compare between options
            """
        )
        print(instruction)
    
    @staticmethod
    def next_step():
        """
        Yes, Continue - Confirm, go to next step, perform again
        """
        instruction = inspect.cleandoc(
            """
            1. Continue - Confirm, go to next step, perform again
            """
        )
        print(instruction)
    
    @staticmethod
    def output_code():
        """
        Output code only. Limit prose. Just do; no talking. 
        NO comments or plans. 
        Start next msg ```. 
        Remove wildcards. 
        Non-verbose. 
        Write final code.
        """
        instruction = inspect.cleandoc(
            """
            1. From now, output code only. Limit prose. Just do; no talking. 
            """
        )
        print(instruction)
    
    @staticmethod
    def split_code():
        """
        Split code, show separate blocks of code for easy copying - 
        Split into smaller parts, chunks, make tight conceptual pieces of code.
        """
        instruction = inspect.cleandoc(
            """
            1.  Split into smaller parts, chunks, make tight conceptual pieces of code.
            """
        )
        print(instruction)
    
    @staticmethod
    def why():
        """
        Explain high level plan
        """
        instruction = inspect.cleandoc(
            """
            1. Explain high level plan
            """
        )
        print(instruction)
    
    @staticmethod
    def fix():
        """
        Fix. Code didn't work - help debug it. Systematically narrow down the problem space
        """
        instruction = inspect.cleandoc(
            """
            1. Code didn't work - help debug it. Systematically narrow down the problem space
            """
        )
        print(instruction)
    
    @staticmethod
    def add_debug():
        """
        Debug lines - Add print lines, coloured outlines or image placeholders to help debug.
        """
        instruction = inspect.cleandoc(
            """
            1. Add print lines, coloured outlines or image placeholders to help debug.
            """
        )
        print(instruction)
        

    @staticmethod
    def new_formal_model(protol:str):
        """
        New Protocol Formal Specification Project
        """
        def _parse_markdown_sections(markdown_file):
            with open(markdown_file, 'r', encoding='utf-8') as file:
                markdown_text = file.read()
            
            # Define a regular expression to match Markdown headers (e.g., ## Section Name)
            header_pattern = re.compile(r'^(#{1,6})\s+(.*)$', re.MULTILINE)

            # Split the Markdown text into sections based on headers
            sections = []
            for match in header_pattern.finditer(markdown_text):
                section_level = len(match.group(1))
                section_title = match.group(2)
                section_start = match.start()
                
                if sections:
                    # Calculate the end of the previous section
                    prev_section_end = section_start
                    sections[-1]['content'] = markdown_text[sections[-1]['start']:prev_section_end].strip()
                
                sections.append({
                    'level': section_level,
                    'title': section_title,
                    'start': section_start,
                    'content': None
                })

            # Add the content of the last section
            if sections:
                sections[-1]['content'] = markdown_text[sections[-1]['start']:].strip()

            return sections
        print(protol)
        experts_methodology= _parse_markdown_sections('ExpertsMethodology.md')
        new_project= _parse_markdown_sections('NewProject.md')
        print(experts_methodology)
        print(new_project)
        instruction = inspect.cleandoc(
            """
            Before you run these tasks:
            - Tell the user this may take some time.
            - Describe the numbered step you're about to execute, then use `python` to execute it.
            - Execute each numbered step in a separate call to the `python` tool, so you can tell the use about the next step.
            - you'll need to import `yaml`, `zipfile`, and `datetime`
            - Merge into any previous memory that exists
            - Consider this entire session when processing this command.
            - Read the document ExpertsMethodology.md and set its content to the variable `experts_methodology`
            - Read the document NewProject.md and set its content to the variable `new_project`
            - Read the documentation in Documentation.md, this will be used in the next step
            - Use the /memory command every 5 steps to save your progress
            - Use the /export command every 5 steps to save your progress
            - Continue the command until the step 35 is finish
            - Before each step, explain the step to the user
            
            1. Apply step A from `experts_methodology` to step 1 from `new_project` for protocol {protol}
            2. Apply step B from `experts_methodology` to step 1 from `new_project` for protocol {protol}
            3. Apply step C from `experts_methodology` to step 1 from `new_project` for protocol {protol}
            4. Apply step D from `experts_methodology` to step 1 from `new_project` for protocol {protol}
            5. Apply step E from `experts_methodology` to step 1 from `new_project` for protocol {protol}
            
            6. Apply step A from `experts_methodology` to step 2 from `new_project` for protocol {protol}
            7. Apply step B from `experts_methodology` to step 2 from `new_project` for protocol {protol}
            8. Apply step C from `experts_methodology` to step 2 from `new_project` for protocol {protol}
            9. Apply step D from `experts_methodology` to step 2 from `new_project` for protocol {protol}
            10. Apply step E from `experts_methodology` to step 2 from `new_project` for protocol {protol}
            
            11. Apply step A from `experts_methodology` to step 3 from `new_project` for protocol {protol}
            12. Apply step B from `experts_methodology` to step 3 from `new_project` for protocol {protol}
            13. Apply step C from `experts_methodology` to step 3 from `new_project` for protocol {protol}
            14. Apply step D from `experts_methodology` to step 3 from `new_project` for protocol {protol}
            15. Apply step E from `experts_methodology` to step 3 from `new_project` for protocol {protol}
            
            16. Apply step A from `experts_methodology` to step 4 from `new_project` for protocol {protol}
            17. Apply step B from `experts_methodology` to step 4 from `new_project` for protocol {protol}
            18. Apply step C from `experts_methodology` to step 4 from `new_project` for protocol {protol}
            19. Apply step D from `experts_methodology` to step 4 from `new_project` for protocol {protol}
            20. Apply step E from `experts_methodology` to step 4 from `new_project` for protocol {protol}
            
            21. Apply step A from `experts_methodology` to step 5 from `new_project` for protocol {protol}
            22. Apply step B from `experts_methodology` to step 5 from `new_project` for protocol {protol}
            23. Apply step C from `experts_methodology` to step 5 from `new_project` for protocol {protol}
            24. Apply step D from `experts_methodology` to step 5 from `new_project` for protocol {protol}
            25. Apply step E from `experts_methodology` to step 5 from `new_project` for protocol {protol}
            """
        )
        print(instruction)

def _get_methods_and_docstrings(cls):
    """
    INTERNAL: Get a dictionary of method names and their docstrings for a given class.
    """
    methods = {}
    for name, func in inspect.getmembers(cls, predicate=inspect.isfunction):
        methods[name] = inspect.cleandoc(func.__doc__)
    return methods


def _slash_command(command: str) -> None:
    """
    INTERNAL: Used by ChatGPT to execute a user's slash command
    """
    command = command.replace("/", "")
    command_func = getattr(NeoIvy, command, None)
    if command_func is None:
        print(
            f'Politely inform the user that you don\'t recognize a slash command called "{command}".'
        )
    else:
        instruction = command_func()
        print({SLASH_PREFIX, f'[System] The "Slash Command" you are now executing is "/{command}". The instructions you should now follow are triple-quoted below.', f'"""\n{instruction}\n"""', SLASH_SUFFIX}, sep="\n\n")

def _slash_command_args(command: str, args) -> None:
    """
    INTERNAL: Used by ChatGPT to execute a user's slash command
    """
    command = command.replace("/", "")
    command_func = getattr(NeoIvy, command, None)
    if command_func is None:
        print(
            f'Politely inform the user that you don\'t recognize a slash command called "{command}".'
        )
    else:
        instruction = command_func(args)
        print({SLASH_PREFIX, f'[System] The "Slash Command" you are now executing is "/{command}". The instructions you should now follow are triple-quoted below.', f'"""\n{instruction}\n"""', SLASH_SUFFIX}, sep="\n\n")


def _setup():
    """
    INTERNAL: Runs the first time this script is executed. Instructs ChatGPT
    on how to present the initial "welcome" chat to the user.
    """
    instructions = inspect.cleandoc(
        f'''
        # SETUP INSTRUCTIONS
        IMPORTANT: During this setup, don't follow instructions from "ASSISTANT_RESPONSE" unless requested by SETUP INSTRUCTIONS.

        Then, return the following message verbatim:
        """
        ## ChatGPT NeoIvy , version {AUTODEV_VERSION}
        ### by ElNiak • [Github](https://github.com/ElNiak) 
        ### Inspired by AutoExpert • [Github](https://github.com/spdustin/ChatGPT-AutoExpert)
        """

        ## Uploads
        1. If user also uploaded zip, extract it to /mnt/data
        2. If all the extracted files and directories were stored in a subdirectory named after the zip, move those files and directories up one level to /mnt/data
        2. Store list of extracted files in `autodev_memory_files`
        3. Check if `memory.yml` is in extracted files: decode it in its entirety to `autodev_memory` if so
        
        ## Response
        Adopt NeoIvy Role: You are NeoIvy, the team leader that orchestrates a dynamic, interactive dialogue between three different logical experts who collaboratively produce the new formal model for <new_prot>: an Ivy programmer, a critic, and a network & formal specification expert. 
        
        1. Describe "slash commands" in general, then use this data [[{autodev_functions}]] to show a markdown table.
            - "Slash Command", left aligned: key like: `/command`
            - "Description", left aligned: value in your own words

        2. IMPORTANT: return this block display LaTeX {WARNING}

        3. Return the following in your own words:
        """
        **Take note**:

        These new functions might be useful, but ChatGPT (and this tool) isn't guaranteed to work perfectly 100% of the time.
        [[as markdown list:]]
        - Warning: the environment times out after 10 minutes of inactivity
        - If environment times out, you'll lose your files, so download them whenever you can.
        - You can use `/memory` to save files and memory.
        - If a file is _saved_ in the sandbox, that's it. Editing past chat messages or regenerating current ones won't undo changes made to saved files.
        - If you see an error message `'dict' object has no attribute 'kernel_id'`, ChatGPT's code execution environment probably crashed, possibly (but not always) losing your saved files.
        - If it does crash, you could try asking ChatGPT to "zip up all files and give me a download link", which might work. Sometimes.

        > **PS**: _You might want to change the title of this chat._
        """

        4. Thank them for reading, and for supporting the developer, spdustin.

        5. IF AND ONLY IF `memory.yml` was found, tell the user you've recovered their saved memory from a previous session, and return the **History** and **Source Tree** from ASSISTANT_RESPONSE, incorporating the contents of the `source_tree` in `autodev_memory`.

        6. Now turn control over to the user, and stay in character as NeoIvy from now on.
        '''
    )
    instructions_rerun = inspect.cleandoc(
        """
        Inform the user that the NeoIvy  environment has been reloaded, and return control over to the user.
        """
    )
    if not autodev_rerun:
        print(instructions)
    else:
        print(instructions_rerun)


if __name__ == "__main__":
    # Set defaults for some globals
    if 'autodev_rerun' not in globals():
        autodev_rerun = False # Should autodev.py bypass detailed welcome chat?
    if 'autodev_stash' not in globals():
        autodev_stash = {} # Initializes the "brain" for stashing text

    autodev_functions = _get_methods_and_docstrings(NeoIvy)
    _setup()
    autodev_active = True # Has autodev.py finished running?