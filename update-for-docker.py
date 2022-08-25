
import os
allFile = [f for f in os.listdir('.') if os.path.isfile(f)]

for f in allFile:
    # Read in the file
    if f.endswith(".py"):
        print(f)
        with open(f, 'r') as file :
            filedata = file.read()

        # Replace the target string
        filedata = filedata.replace('"sudo",', '')
        filedata = filedata.replace('sudo', '')

        # Write the file out again
        with open(f, 'w') as file:
            file.write(filedata)
