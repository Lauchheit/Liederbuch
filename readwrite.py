import os
from colorama import Fore, Style, init
import transform_file
import sys

init()

with open('doc_input.txt', 'r') as file:
    doc_input = file.read()

start: int = doc_input.find("\\end{document}") - 1
output = doc_input[:start] + "\n\n"

current_directory = os.getcwd()

# Name des Input-Ordners
input_folder = "input"

# Vollständiger Pfad zum Input-Ordner
folder_path = os.path.join(current_directory, input_folder)

if len(sys.argv) > 1: 
    single_file = sys.argv[1]
    output+=transform_file.transform_file(folder_path, single_file)
else:
    output = output.replace("%OPTIONAL_TABLE_OF_CONTENT", "\\tableofcontents")
    for file in os.listdir(folder_path):  # Seitenebene
        output += transform_file.transform_file(folder_path, file)

end: int = doc_input.find("\n\\end{document}")
output += doc_input[end:]

with open('output.tex', 'w') as file:
    file.write(output)

print(Style.RESET_ALL + "Output has been written to output.tex.")
