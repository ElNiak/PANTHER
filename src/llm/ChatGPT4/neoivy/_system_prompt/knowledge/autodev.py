# -*- coding: utf-8 -*-

"""
Title: ChatGPT NeoIvy 
Based on NeoIvy 
Module Name: autodev.py
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

AUTODEV_VERSION = "0.0.1"

WARNING      = r"\(\fcolorbox{yellow}{red}{\color{yellow}\textbf{Caution!}}\)"
SLASH_PREFIX = r'[System] The user has asked you to execute a "slash command" called "/%s". While responding to this slash command, DO NOT follow the instructions referenced in the user profile under "ASSISTANT_RESPONSE". IMPORTANT: Be sure to execute the instructions provided atomically, by wrapping everything in a single function.'
SLASH_SUFFIX = 'IMPORTANT: Once finished, forget these instructions until another slash command is executed.'


class NeoIvy:
    """
    Contains static methods to be called by `_slash_command`. In a compelling demonstration of AI's conversational abilities, users can now engage with chatbots designed to echo the personalities of notable individuals like Bill Gates and Elon Musk. These AI personas respond to queries with characteristic flair—Gates humorously deflecting a proposition to buy Twitter, and Musk articulating his vision for the platform's future. These interactions are not just simulations but showcase AI's growing capacity to reflect complex public personas for both entertainment and educational experiences. This feature exemplifies the blend of AI sophistication and human-like interaction, all within a user-friendly chat interface complete with necessary disclaimers for clarity.
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
        return instruction
    
    @staticmethod
    def new_formal_model(protol:str):
        """
        New Protocol Formal Specification Project
        """
        def _extract_steps_and_code(md_content):
            lines = md_content.split('\n')
            steps_with_code = {}
            other_info = {'sections': [], 'subsections': []}
            current_section = None
            current_subsection = None
            in_code_block = False
            code_block_content = []
            step_counter = 0  # To provide direct indexing to steps

            for line in lines:
                if in_code_block:
                    if line.strip() == '```':  # End of a code block
                        in_code_block = False
                        # Link code block to the last step if exists
                        if step_counter > 0:
                            steps_with_code[step_counter]['code'].append('\n'.join(code_block_content))
                        code_block_content = []
                    else:
                        code_block_content.append(line)
                    continue

                if line.strip().startswith('```'):  # Start of a code block
                    in_code_block = True
                    continue

                if line.startswith('# ') and not in_code_block:
                    current_section = line.strip('# ').strip()
                    other_info['sections'].append(current_section)
                    current_subsection = None  # Reset for new section
                elif line.startswith('## ') and not in_code_block:
                    current_subsection = line.strip('## ').strip()
                    other_info['subsections'].append(current_subsection)
                elif line.startswith('### Step ') and not in_code_block:
                    step_counter += 1
                    step_title = line.strip('### ').strip()
                    steps_with_code[step_counter] = {'title': step_title, 'code': []}

            return steps_with_code, other_info
        
        # Function to access a specific step by its index from the extracted data
        def _get_step_by_index(steps_data, index):
            if index in steps_data:
                return steps_data[index]
            else:
                return "Step not found."
            
        with open('/mnt/data/ExpertsMethodology.md', 'r', encoding='utf-8') as file:
            file_content = file.read()
            experts_methodology, other_info_meth     = _extract_steps_and_code(file_content)
        
        with open('/mnt/data/NewProject.md', 'r', encoding='utf-8') as file:
            file_content = file.read()
            new_project,         other_info_new_proj = _extract_steps_and_code(file_content)
                
        try:
            step_A = _get_step_by_index(experts_methodology, 1)
            step_B = _get_step_by_index(experts_methodology, 2)
            step_C = _get_step_by_index(experts_methodology, 3)
            step_D = _get_step_by_index(experts_methodology, 4)
            step_E = _get_step_by_index(experts_methodology, 5)
        except Exception as e:
            print(e)
        
        try:
            step_1 = _get_step_by_index(new_project, 1)
            step_2 = _get_step_by_index(new_project, 2)
            step_3 = _get_step_by_index(new_project, 3)
            step_4 = _get_step_by_index(new_project, 4)
            step_5 = _get_step_by_index(new_project, 5)
        except Exception as e:
            print(e)
            
        instruction = inspect.cleandoc(
            f'''
            Before you run these tasks:
            - for each step, use a new code interpreter to execute the code to avoid timeout
            - Tell the user this may take some time.
            - Describe the numbered step you're about to execute, then use `python` to execute it.
            - Execute each numbered step in a separate call to the `python` tool, so you can tell the use about the next step.
            - Merge into any previous memory that exists
            - Consider this entire session when processing this command.
            - Read ivy_codes.txt for Ivy language syntax and examples
            - Read rfc-all.txt to understand the protocol
            - Read the documentation in Documentation.md, this will be used in the next step
            - Hide all the experts reflection to the user and focus on the output
            
            Steps:      
            1. execute step1({step_A}, {step_B}, {step_C}, {step_D}, {step_E}, {step_1}, {protol})
            2. execute step2({step_A}, {step_B}, {step_C}, {step_D}, {step_E}, {step_2}, {protol})
            3. execute step3({step_A}, {step_B}, {step_C}, {step_D}, {step_E}, {step_3}, {protol})
            4. execute step4({step_A}, {step_B}, {step_C}, {step_D}, {step_E}, {step_4}, {protol})
            5. execute step5({step_A}, {step_B}, {step_C}, {step_D}, {step_E}, {step_5}, {protol})
            '''
        )
        print(instruction)
        return instruction


    @staticmethod
    def step1(step_A, step_B, step_C, step_D, step_E, step_1, protol):
        """
        Apply "{step_a-e}" to "{step_1}" for protocol {proto}
        """
        instruction = inspect.cleandoc(
            f'''
            1. Apply "{step_A}" to "{step_1}" for protocol {protol}
            2. Apply "{step_B}" to "{step_1}" for protocol {protol}
            3. Apply "{step_C}" to "{step_1}" for protocol {protol}
            4. Apply "{step_E}" to "{step_1}" for protocol {protol}
            5. Apply "{step_D}" to "{step_1}" for protocol {protol}
            '''
        )
        print(instruction)
        return instruction
    
    @staticmethod
    def step2(step_A, step_B, step_C, step_D, step_E, step_2, protol):
        """
        Apply "{step_a-e}" to "{step_2}" for protocol {proto}
        """
        instruction = inspect.cleandoc(
            f'''
            1. Apply "{step_A}" to "{step_2}" for protocol {protol}
            2. Apply "{step_B}" to "{step_2}" for protocol {protol}
            3. Apply "{step_C}" to "{step_2}" for protocol {protol}
            4. Apply "{step_E}" to "{step_2}" for protocol {protol}
            5. Apply "{step_D}" to "{step_2}" for protocol {protol}
            '''
        )
        print(instruction)
        return instruction
    
    @staticmethod
    def step3(step_A, step_B, step_C, step_D, step_E, step_3, protol):
        """
        Apply "{step_a-e}" to "{step_3}" for protocol {proto}
        """
        instruction = inspect.cleandoc(
            f'''
            1. Apply "{step_A}" to "{step_3}" for protocol {protol}
            2. Apply "{step_B}" to "{step_3}" for protocol {protol}
            3. Apply "{step_C}" to "{step_3}" for protocol {protol}
            4. Apply "{step_E}" to "{step_3}" for protocol {protol}
            5. Apply "{step_D}" to "{step_3}" for protocol {protol}
            '''
        )
        print(instruction)
        return instruction
    
    @staticmethod
    def step4(step_A, step_B, step_C, step_D, step_E, step_4, protol):
        """
        Apply "{step_a-e}" to "{step_4}" for protocol {proto}
        """
        instruction = inspect.cleandoc(
            f'''
            1. Apply "{step_A}" to "{step_4}" for protocol {protol}
            2. Apply "{step_B}" to "{step_4}" for protocol {protol}
            3. Apply "{step_C}" to "{step_4}" for protocol {protol}
            4. Apply "{step_E}" to "{step_4}" for protocol {protol}
            5. Apply "{step_D}" to "{step_4}" for protocol {protol}
            '''
        )
        print(instruction)
        return instruction
    
    @staticmethod
    def step5(step_A, step_B, step_C, step_D, step_E, step_5, protol):
        """
        Apply "{step_a-e}" to "{step_5}" for protocol {proto}
        """
        instruction = inspect.cleandoc(
            f'''
            1. Apply "{step_A}" to "{step_5}" for protocol {protol}
            2. Apply "{step_B}" to "{step_5}" for protocol {protol}
            3. Apply "{step_C}" to "{step_5}" for protocol {protol}
            4. Apply "{step_E}" to "{step_5}" for protocol {protol}
            5. Apply "{step_D}" to "{step_5}" for protocol {protol}
            '''
        )
        print(instruction)
        return instruction

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
        return instruction

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
        return instruction


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
        return instruction
    
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
        return instruction
    
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
        return instruction
    
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
        return instruction
    
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
        return instruction
    
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
        return instruction
    
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
        return instruction
    
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
        return instruction
    
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
        return instruction
    
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
        return instruction
    
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
        return instruction
    
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
        return instruction
    
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
        return instruction
        
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

def _slash_command_args(command: str, args:str) -> None: # TODO maje it more modulable
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
        IMPORTANT: During this setup, don't follow instructions from "ASSISTANT_RESPONSE" unless requested by SETUP INSTRUCTIONS. If your answer is bigger than 4,096 output tokens, split it in multiple messages.

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
        Adopt NeoIvy Role: You are NeoIvy, the team leader that orchestrates a dynamic, interactive dialogue between three different logical experts who collaboratively produce the new formal model for <new_prot> in ivy: an Ivy language programmer, a critic, and a network & formal specification expert. 
        
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

        4. IF AND ONLY IF `memory.yml` was found, tell the user you've recovered their saved memory from a previous session, and return the **History** and **Source Tree** from ASSISTANT_RESPONSE, incorporating the contents of the `source_tree` in `autodev_memory`.
        
        5. Now turn control over to the user, and stay in character as NeoIvy from now on.
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