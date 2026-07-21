from typing import List
max_line:int =0
warn_list = []

class TitleSection:
    def __init__(self, titlelist) -> None:
        if(titlelist[0] == None): raise Exception("Piece has no Title")
        self.title = titlelist[0]

        if(titlelist[1] == None): self.composer = None
        else: self.composer = titlelist[1]

        self.out = self.output_string()
    
    def output_string(self)->str:
        if(self.composer == None): self.composer=""
        output = "\\mysection{"+self.title+"}{"+self.composer+"}\n\n\\composer{"+self.composer+"}\\\\\n\n"
        return output

class Comment:
    def __init__(self,flag : bool, text : str) -> None:
        self.flag = flag
        self.text = text

    def __str__(self) -> str:
        return self.text

class Chord:
    def __init__(self, pos:int, name:str,) -> None:
        self.pos = pos
        self.repflag=False
        #self.before_chord_spaceflag = before_chord_spaceflag or pos == 1 #in case the chord is in the middle of a word  (e.g. 'ne{F}eds') the space must be removed
        if(name.find('x')!=-1): 
            self.repflag : bool= True
        self.name = name
    
    def __str__(self) -> str:
        return "{"+self.name+"}" + ": " + str(self.pos)

class Lyrics:
    def __init__(self, pos:int, text:str, spaceflag:bool = True) -> None:
        self.text=text
        self.pos = pos
        self.spaceflag:bool = spaceflag

    
    def __str__(self) -> str:
        return self.text + ": " + str(self.pos) #+ "   " + str(self.spaceflag)
            


def create_empty_table(rows, columns):
    table = []
    for _ in range(rows):
        row = [None] * columns
        table.append(row)
    return table

class Table:
    def __init__(self, comment: Comment, chords: List[Chord], lyric_array: List[Lyrics]) -> None:
        self.comment = comment
        self.max_index = (lyric_array[-1].pos)+1
        table = create_empty_table(2,self.max_index)


        for chord in chords:
            table[0][chord.pos] = chord

        sum=0
        global max_line
        global warning_line
        for lyric in lyric_array:
            table[1][lyric.pos] = lyric
            sum+=len(lyric.text)
        
        for lyric in table[1]:
            if lyric is None: continue
            if len(lyric.text) >0 and lyric.text[-1] != ' ':
                lyric.spaceflag = False
            #print(str(lyric.pos) + "|"+lyric.text+"| " + str(lyric.spaceflag))

        if(sum>max_line): 
            max_line=sum
        self.table=table
        #print(self.table)
        self.tabledef = self.get_table_def()
        self.out: str = self.output_string()

    def get_table_def(self)->str:
        output = "l"
        for i in range(self.max_index):
            if self.table[1][i] is None:
                output += "@{}"
            elif (self.table[1][i] is not None and self.table[1][i].spaceflag):
                output += "@{ }"
            else:
                output += "@{}"
            output += "l"
        return output
    

    def output_string(self) -> str:
        output = "\\begin{tabular}{" + self.tabledef +"}\n"
        if(self.comment.flag==True): 
            output += "\\multicolumn{"+str(self.max_index)+"}{l}{\\com{" + self.comment.text + "}}\\\\\n"

        empty:bool = True
        for i in self.table[0]:
            if(i != None and len(i.name) != 0): 
                empty = False
                break
        if(empty == False):
            first: bool = True
            output+="\\\\[-0.5em]"
            for i in self.table[0]:
                if(first == False): output += "&"
                if(i == None): 
                    text = ""
                    
                else: 
                    text = i.name
                    if(i.repflag == False):output += "\\ch"
                    if(i.repflag == True):output+="\\rep"
                output+= "{"+text+"}"
                first = False
            output+="\\\\\n"

        empty:bool = True
        for i in self.table[1]:
            if(i != None and len(i.text) != 0): 
                empty = False
                break

        if(empty == False):
            first: bool = True
            for i in self.table[1]:
                if(i == None): text = ""
                else: text = i.text

                if(first == False): output += "&"
                output += "\\tx{"+ text +"}"
                first = False

        output += "\n\\end{tabular}\\\\"
        return output