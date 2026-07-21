import classes as c
from typing import List

def paragraphs(text)->List[str]:
    while text.find("\n\n\n") != -1:
        text = text.replace('\n\n\n','\n\n')
    while text[-1]=="\n":
        text = text[:-1]
    text = text.replace('&','\\&')
    text = text.replace('#','\\#')
    text = text.replace('} ','}{}')
    return text.split('\n\n')

def get_comment(line)->c.Comment:
    index1 = line.find("[")
    index2 = line.find("]")
    
    if index1 == -1 or index2 == -1:
        return c.Comment(False, "")
    else:
        return c.Comment(True, line[index1+1:index2])

def remove_comment(line)->str:
    index2 = line.find("]")

    if index2 == -1:
        return line
    else: return line[index2+1:]


def split_line(line:str, comment:c.Comment)->str:
    pos_left = []
    index_left = 0

    pos_right = []
    index_right =0
    while True:
        index_left = line.find("{", index_left)
        if index_left == -1:
            break
        pos_left.append(index_left)
        index_left += 1
    
    while True:
        index_right = line.find("}", index_right)
        if index_right == -1:
            break
        pos_right.append(index_right)
        index_right += 1

    chords= [] #: List(c.Chord) 
    #chord_spaceflag_blacklist = [" ", "{","}","\\n"]
    #Add Chords to Chord List
    for k in range(len(pos_left)):
        pos1 = pos_left[k]+1
        pos2 = pos_right[k]
        
        chords.append(c.Chord(k+1,line[pos1:pos2]))

    #print("empty chords:" + format(empty_chord_list))
    lyrics = [] #: List(c.Lyrics)

    if(len(chords)==0):
        lyrics.append(c.Lyrics(0,line))
        return c.Table(comment,chords,lyrics).out
    
    #Add Lyrics to Lyrics List
    if(pos_left[0] != 0 ): 
        lyrics.append(c.Lyrics(0, line[0:pos_left[0]])) #Before first Chord

    offset = 1
    for i in range(len(chords)-1):    #Mid
        pos1 = pos_right[i]+1
        pos2 = pos_left[i+1]
        
        current_lyrics = line[pos1:pos2]
        lyrics.append(c.Lyrics(i+1, current_lyrics))

    pos1 = pos_right[-1]+1
    pos2 = len(line)
    last_lyrics = line[pos1:pos2]
    #print("|" + last_lyrics + "|\n")
    lyrics.append(c.Lyrics(k+offset, last_lyrics))

    table = c.Table(comment, chords, lyrics)
    return table.out

def combined_paragraph(paragraph:str)->str:
    if(paragraph.count("[")>1 or paragraph.count("]")>1): c.warn_list.append("Detected more than one comment in paragraph:\n"+paragraph)
    comment = get_comment(paragraph)
    paragraph = remove_comment(paragraph)
    if(len(paragraph)==0 and comment.flag == True):
        return "\\begin{tabular}{l}\n\\begin{tabular}{l}\n\com{\\textmusicalnote ~" + comment.text + "}\n\\end{tabular}\n\\end{tabular}"
    lines = paragraph.splitlines()
    output ="%paragraph\n\\begin{tabular}{l}\n\n"
    first:bool= True
    for line in lines:
        if(len(line)==0):continue
        if(first==False): 
            output += "\n\n"
            output += split_line(line,c.Comment(False,""))
        else: 
            output += split_line(line,comment)
        first=False
    
    output += "\n\n\\end{tabular}\\\\"
    return output

def title_section(output,paragraphs):
    titlelist = [None,None]
    removelist = []
    for par in paragraphs:
        pos1=par.find('[')
        pos2=par.find(']')+1
        if(pos1 == -1 or pos2 == -1): continue
        if(par[pos1:pos2] == '[Title]'): 
            if(titlelist[0]!=None): raise Exception("You cannot have two Titles:\n1: "+titlelist[0]+"\n2: "+par[pos2:])
            titlelist[0] = par[pos2:]
            removelist.append(par)
        elif(par[pos1:pos2] == '[Composer]'): 
            if(titlelist[1]!=None): raise Exception("You cannot have two Composers:\n1: "+titlelist[1]+"\n2: "+par[pos2:])
            titlelist[1] = par[pos2:]
            removelist.append(par)
        else: break
        if(len(par.splitlines())>1): raise Exception("Meta Text cannot be longer than one line: \n"+par)
        if(par.find('{')!=-1 or par.find('}')!=-1 or par.count('[')>1 or par.count(']')>1 or par.find('\n')!=-1): raise Exception("Invalid position for a Meta Command:\n" +par)
    for par in removelist:
        paragraphs.remove(par)
    return output+c.TitleSection(titlelist).out, paragraphs
