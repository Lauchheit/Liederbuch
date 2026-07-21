import os
import transform_paragraph as tr
import os
import classes as c
import warnings
from colorama import Fore, Style, init
import traceback  # Import für detaillierte Fehlerinformationen
max_line_border = 55
def transform_file(folder_path, file):

    output = ""

    file_path = os.path.join(folder_path, file)
    outputbackup = output
    filename = "" 
    
    try:
        if os.path.isdir(file_path):
            return ""
        if os.path.isfile(file_path):
            filename = os.path.basename(file_path)
            c.warn_list = [(Fore.YELLOW + "Warning: " + filename + Style.RESET_ALL)]
            output += "\n%NEW SONG: " + file_path + "\n"
            
            with open(file_path, 'r') as file:
                input = file.read()
                
            paragraphs = tr.paragraphs(input)
            output, paragraphs = tr.title_section(output, paragraphs)
            
            for par in paragraphs:  # Paragraphebene
                output += tr.combined_paragraph(par)
                output += "\\\\\n\n"
                
            if c.max_line <= max_line_border:
                output = output[:output.find(file_path) + len(file_path)] + "\n\\twocolumn\n" + output[output.find(file_path) + len(file_path):]
                print(Fore.GREEN + "Success: " + filename + Style.RESET_ALL)
            else:
                c.warn_list.append("Could not convert to two columns. Longest line is " + str(c.max_line) + " characters long. (max is " + str(max_line_border) + ")")
                
            output += "\\onecolumn\n\\newpage"
            
            if len(c.warn_list) > 1:
                for warning in c.warn_list:
                    print(warning)
                    
            c.max_line = 0
        else:
            raise Exception("Could not open one file")
            
    except Exception as e:
        # Detaillierte Fehlermeldung mit Traceback
        print(Fore.RED + "Error in file: " + filename + Style.RESET_ALL)
        print(Fore.RED + "Error type: " + str(type(e)) + Style.RESET_ALL)
        print(Fore.RED + "Error message: " + str(e) + Style.RESET_ALL)
        print(Fore.RED + "Traceback: \n" + traceback.format_exc() + Style.RESET_ALL)
        
        output = outputbackup
        return ""
    return output