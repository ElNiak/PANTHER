
import os


def getListOfFiles(dirName):
    '''
    For the given path, get the List of all files in the directory tree 
    ''' 
    # create a list of file and sub directories 
    # names in the given directory 
    listOfFile = os.listdir(dirName)
    allFiles = list()
    # Iterate over all the entries
    for entry in listOfFile:
        # Create full path
        fullPath = os.path.join(dirName, entry)
        # If entry is a directory then get the list of files in this directory 
        if os.path.isdir(fullPath):
            allFiles = allFiles + getListOfFiles(fullPath)
        else:
            allFiles.append(fullPath)
                
    return allFiles


allFile = getListOfFiles(".")

for f in allFile:
    # Read in the file
    with open(f, 'r') as file :
        filedata = file.read()

    # Replace the target string
    filedata = filedata.replace('sudo', '')

    # Write the file out again
    with open(f, 'w') as file:
        file.write(filedata)