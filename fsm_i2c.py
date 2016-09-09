"""
   fsm_i2c.py

   written by  Yunho Kim, Charlotte

   Create a Finite State Machine as Verilog from the vcd format timing diagram

"""

"""
    @ FSM Class
        Set the data of Finite State Machine from the vcd file.
        Print the FSM to the Verilog format.

    - Variable -
        s_moduleName : Name of FSM
        dic_inputVal : A pair of vcd variable name and original variable name
                        It defines from vcd header section
        li_states : A List of state classes

    - Function -
        setFSM() : Setting class local variables and state information from the each line of vcd file
        printHeader() : Print the header part of verilog file
        printInitialize() : Print the initialize part of verilog file
        printTransitions() : Print the state changing conditions & transition part of verilog file
        makeConditionString() : Create the condition statement for state changing
"""
class FSM:
    s_moduleName = ""
    dic_inputVal = {}
    li_states = []

    # set FSM class
    def setFSM(self, lines):
        stat = 0
        idx = 1
        dontCareVar = '0'
        dontCare = 0
        tempdic = {}
        sda = ''

        for line in lines:
            # print(line)
            if line[0] == '$':
                line = line[1:]
                words = line.split()

                # read module name and original value names at .vcd and write on the FSM class
                if words[0] == 'scope':
                    fsm.setModuleName(words[2])
                elif words[0] == 'var' and words[1] == 'reg':
                    print(words[4], "is assigned to", words[3])
                    fsm.setInputValue(words[3], words[4])
                continue

            if line[0] == '#':
                if line[1] == '0':
                    continue
                if idx > 1 and not (tempdic.get('scl') == '1' and len(tempdic) == 1):
                    stat.setTransition(tempdic, "s" + str(idx + 1))
                    fsm.setState(stat)
                #reset transitions, create new State
                tempdic = {}
                stat = State("s" + str(idx))
                idx += 1
                continue
            if line == "...\n":
                stat.setIsLoop()
                continue

            #write the transitions to dictionary
            val = line[0]
            var = fsm.getInputVal(line[1])
            tempdic[var] = val
            if var == 'sda':
                sda = val
            if tempdic.get('scl') == '0' and len(tempdic) == 1:
                tempdic['sda'] = sda

        return fsm


    # print the header part of verilog file
    def printHeader(self, output):
        output.write("module " + self.s_moduleName + "(reset, " + self.makeInputVarString() + ", out);\n")
        output.write("\tinput reset, " + self.makeInputVarString() + ";\n")
        output.write("\toutput reg[64:0] out;\n")
        output.write("\tparameter " + self.makeStateString() + ";\n")
        output.write("\treg[64:0] state, nextState;\n")  # change 1 bit into 16 bits
        output.write("\treg[128:0] label;\n\n")  # to label repeated states

    # print the initialize part of verilog file
    def printInitialize(self, output):
        string = '\t' + 'always @(*) begin\n'
        string += '\t\t' + 'if(reset) begin\n'
        string += '\t\t\t' + 'state <= ' + self.li_states[0].s_name + ';\n'
        string += '\t\t' + 'end\n\t\t' + 'else begin\n'
        string += '\t\t\t' + 'state <= nextState;\n\t\t' + 'end\n\t'
        string += 'end\n\n'
        output.write(string)

    # print the state changes & transition part of verilog file
    def printTransition(self, output):
        output.write('\t' + 'always @(' + self.makeInputVarString() + ') begin\n\t\t' + 'case(state)\n')
        for i in range(0, len(self.li_states)):
            curState = self.li_states[i]
            if i == len(self.li_states) - 1:
                string = '\t\t' + curState.s_name + ' : begin\n\t\tend\n'
                output.write(string)

            else:
                string = '\t\t' + curState.s_name + ' : begin\n'
                string += "\t\t\tout <= " + curState.s_name + ';\n'
                if self.li_states[i].s_labeled == -1:
                    # default state
                    if self.li_states[i].s_name == 's1':
                        string += "\t\t\tlabel <= 1'bx;\n"

                elif self.li_states[i].s_labeled == 0:  # stop condition
                    string += "\t\t\tlabel <= 1'bx;\n"

                elif self.li_states[i].s_labeled == 1:
                    string += '\t\t\tlabel <= "repeat";\n'

                string += '\t\t\tif('
                # if phrase
                string += self.makeConditionString(i)
                string += ') nextState <= ' + self.li_states[i + 1].s_name + ';\n'
                if i > 0:
                    string += '\t\t\telse if('
                    # else-if phrase
                    string += self.makeElifConditionString(i - 1)
                    string += ') nextState <= ' + self.li_states[i].s_name + ';\n'

                if self.li_states[i].b_isLoop == 0:
                    string += "\t\t\telse nextState <= s1;\n"
                else:
                    string += "\t\t\telse nextState <=" + curState.s_name + ";\n"
                string += '\t\t' + 'end\n'
                output.write(string)
            #curState.printState()

        output.write('\t\t' + 'endcase\n\t' + 'end\n' + 'endmodule')

    def makeConditionString(self, idx):
        string = ""
        for trans in self.li_states[idx].li_transitions:
            for key in trans.dic_tranValue.keys():
                if trans.dic_tranValue[key] != 'x':
                    string += key + ' == ' + trans.dic_tranValue[key] + ' && '
        return string[:-4]

    def makeElifConditionString(self, idx):
        string = ""
        for trans in self.li_states[idx].li_transitions:
            for key in trans.dic_tranValue.keys():
                if trans.dic_tranValue[key] != 'x' and key != 'scl':
                    string += key + ' == ' + trans.dic_tranValue[key] + ' && '
        return string[:-4]


    # make the input value string (e.g. i1, i2, i3)
    def makeInputVarString(self):
        s = ""
        for v in self.dic_inputVal.values():
            s += (v + ", ")
        s = s[:-2]
        return s

    # make the state string (e.g. s1 = 0, s2 = 10, s3 = 30)
    def makeStateString(self):
        s = ""
        idx = 1
        for state in self.li_states:
            s += (state.s_name + " = \"" + state.s_name + "\", ")
            idx += 1
        s = s[:-2]
        return s

    # getters and setters
    def setModuleName(self, n):
        self.s_moduleName = n

    def setInputValue(self, k, v):
        self.dic_inputVal[k] = v

    def setState(self, s):
        self.li_states.append(s)

    def getInputVal(self, k):
        return self.dic_inputVal[k]


"""
    @ State Class
        Store the information of each state

    - Variable -
        s_name : State name
        li_transition : A list of transition
        b_isLoop : boolean variable for check loop back to the first state
        s_labled : Lable nane. if doesn't have anything, value is -1

    - Function -
        setTransition() : Add transition data to the list
"""

class State:
    s_name = ""
    li_transitions = []
    b_isLoop = 0
    s_labeled = -1  # default value to detect whether current state is start or stop

    def __init__(self, n):
        self.s_name = n
        self.li_transitions = []
        self.b_isLoop = 0

    def setTransition(self, valDic, d):
        self.li_transitions.append(Transition(valDic, d))

    def setIsLoop(self):
        self.b_isLoop = 1

    def setStartLabeled(self):
        self.s_labeled = 1

    def setStopLabeled(self):
        self.s_labeled = 0


"""
    @ Transition Class
        Store the information of each transition

    - Variable -
        dic_tranValue : A pair of FSM input variable and value

    - Function -
        PrintTransitionInfo() : Print the transition data on the console
"""

class Transition:
    # s_variable = ""
    # s_value = '0'
    dic_tranValue = {}
    s_dest = ""

    def __init__(self, dic, d):
        self.dic_tranValue = dic
        self.s_dest = d

    def printTransitionInfo(self):
        string = "\tif "
        for k in self.dic_tranValue.keys():
            string += k + " changes to " + self.dic_tranValue[k] + " and "
        string = string[:-4]
        print(string + "\n\t\t--> Next State is " + self.s_dest)


if __name__ == "__main__":
    rf = open("i2c_vcd.vcd", "r")
    wf = open("output.v", "w")
    fsm = FSM()

    lines = rf.readlines()
    lines = lines[10:]
    fsm.setFSM(lines)
    print("FSM created\n")

    fsm.printHeader(wf)
    fsm.printInitialize(wf)
    fsm.printTransition(wf)

    rf.close()
    wf.close()