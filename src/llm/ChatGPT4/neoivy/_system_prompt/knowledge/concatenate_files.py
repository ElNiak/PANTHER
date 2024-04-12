import os
import glob

def concatenate_files(folder_path, output_file, extensions):
    with open(output_file, 'w') as outfile:
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.endswith(tuple(extensions)):
                    file_path = os.path.join(root, file)
                    # Write filename as a comment
                    outfile.write(f'#### FILENAME = {file_path}\n')
                    # Write content of the file
                    with open(file_path, 'r') as infile:
                        outfile.write(infile.read())
                    # Add separator between files
                    outfile.write('\n\n')

# Example usage:
folder_path = '/home/crochetch/Documents/Projects/VerificationQUIC/PFV/src/llm/neoivy/_system_prompt/knowledge/RFC-all/'
output_file = '/home/crochetch/Documents/Projects/VerificationQUIC/PFV/src/llm/neoivy/_system_prompt/knowledge/rfc-all.txt'
extensions = ('.txt',)  # Add the extensions you want to concatenate here
concatenate_files(folder_path, output_file, extensions)
