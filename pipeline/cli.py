# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

#
# interface code
#

import sys, tty
import termios

ESC = u"\u001b["

CURSOR_HIDE      = ESC + u"?25l";
CURSOR_SHOW      = ESC + u"?25h";

CURSOR_MOVE_LEFT = ESC + u"1000D"

COLOR_NORMAL     = ESC + u"48;5;20m" +  ESC + u"37;1m"
COLOR_EMPHASIS   = ESC + u"48;5;21m" +  ESC + u"37;1m"
COLOR_ERROR      = ESC + u"48;5;198m" + ESC + u"37;1m"

CLEAR_SCREEN     = ESC + u"2J"
RESET            = ESC + u"0m"

class cli:
    """ Command line interface """
    def __init__(self):
        self.clear()
        
        self.settings = termios.tcgetattr(sys.stdin)
            
        try:
            tty.setraw(sys.stdin)
        except termios.error:
            c.error("Did you forget the docker arguments \"--interactive --tty\"?")
            raise
        
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
        
        self.defaults = dict()

    def clear(self):
        """ Clear the screen """
        sys.stdout.write(CLEAR_SCREEN)
        sys.stdout.write(ESC + u"0;0H")
        sys.stdout.flush()

    def info(self, q):
        """
        Render text in regular color

        :param q: Text

        """
        sys.stdout.write(CURSOR_MOVE_LEFT)
        sys.stdout.write(COLOR_NORMAL)
        sys.stdout.write("%s" % q)
        sys.stdout.write(RESET)
        sys.stdout.write("\n")
        sys.stdout.flush()

    def error(self, q):
        """
        Render text in error color
        
        :param q: Text

        """
        sys.stdout.write(CURSOR_MOVE_LEFT)
        sys.stdout.write(RESET)
        sys.stdout.write("\n")
        sys.stdout.flush()
        
        raise RuntimeError(COLOR_ERROR + "%s" % q + RESET)

    def read(self, q, o = ""):
        """
        Text prompt

        :param q: Prompt text
        :param o: Initial value (Default value = "")

        """
        tty.setraw(sys.stdin)
        
        selected = 0
        
        sys.stdout.write(CURSOR_MOVE_LEFT)
        sys.stdout.write(COLOR_NORMAL)
        sys.stdout.write("%s" % q)
        sys.stdout.write(RESET)
        sys.stdout.write("\n")
        
        def refresh():
            """ render prompt """
            sys.stdout.write(CURSOR_MOVE_LEFT)
            sys.stdout.write(COLOR_EMPHASIS)
            sys.stdout.write("[%s] " % o)
            sys.stdout.write(CURSOR_MOVE_LEFT)
            sys.stdout.write(u"\u001b[%iC" % (1 + selected))
            sys.stdout.flush()
        
        refresh()
        while True:
            character = ord(sys.stdin.read(1))
            
            if character == 3: # ctrl-c
                sys.stdout.write(RESET)
                sys.stdout.write("\n")
                
                sys.stdout.write(CURSOR_SHOW)
                sys.stdout.flush()
                
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
                
                return None
                
            if character in {10, 13}: # enter
                sys.stdout.write(RESET)
                sys.stdout.write("\n")
                sys.stdout.flush()
                
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
                
                return o
                
            if character == 27: # arrow kets
                next1, next2 = ord(sys.stdin.read(1)), ord(sys.stdin.read(1))
                if next1 == 91:
                    if next2 == 68: # left
                        selected = max(0, selected-1)
                    elif next2 == 67:  # right
                        selected = min(len(o), selected+1)
                        
                    refresh()
                
            if 32 <= character <= 126: # text
                o = o[:selected] + chr(character) + o[selected:]
                selected += 1
                refresh()
                
            if character == 127: # backspace
                if selected > 0:
                    o = o[:selected-1] + o[selected:]
                    selected -= 1
                    refresh()
                

    def select(self, q, o):
        """
        Single choice prompt with multiple possible answers

        :param q: Prompt text
        :param o: List of possible answers

        """
        tty.setraw(sys.stdin)
        
        sys.stdout.write(CURSOR_HIDE)
        
        selected = 0
        
        def refresh():
            """ renders the prompt """
            sys.stdout.write(CURSOR_MOVE_LEFT)
            sys.stdout.write(COLOR_NORMAL)
            sys.stdout.write("%s " % q)
            for i, oo in enumerate(o):
                if i == selected:
                    sys.stdout.write(COLOR_EMPHASIS)
                    sys.stdout.write(" [%s] " % oo)
                else:
                    sys.stdout.write(COLOR_NORMAL)
                    sys.stdout.write(" %s " % oo)
            sys.stdout.write(CURSOR_MOVE_LEFT)
            sys.stdout.flush()
        
        refresh()
        while True:
            character = ord(sys.stdin.read(1))
            
            if character == 3: # ctrl-c
                sys.stdout.write(RESET)
                sys.stdout.write("\n")
                
                sys.stdout.write(CURSOR_SHOW)
                sys.stdout.flush()
                
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
                
                return None
                
            if character in {10, 13}: # enter
                sys.stdout.write(RESET)
                sys.stdout.write("\n")
                
                sys.stdout.write(CURSOR_SHOW)
                sys.stdout.flush()
                
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
                
                return o[selected]
                
            if character == 27: # arrow keys
                next1, next2 = ord(sys.stdin.read(1)), ord(sys.stdin.read(1))
                if next1 == 91:
                    if next2 == 68: # left
                        selected = max(0, selected-1)
                    elif next2 == 67: # right
                        selected = min(len(o)-1, selected+1)
                        
                    refresh()
        
    #  from pipeline.cli import cli; c = cli(); c.fields("How are you?", ["Today", "Yesterday"])
    def fields(self, q, o, max_length = 6):
        """
        Text prompt with multiple fixed-width fields, used for example to
        input contrast vector for first level fMRI analysis.
        
        :param q: Prompt text
        :param o: Initial value
        :param max_length: Maximum length of each text input (Default value = 6)

        """
        tty.setraw(sys.stdin)
        
        selected0 = 0
        selected1 = 0
        
        sys.stdout.write(CURSOR_MOVE_LEFT)
        sys.stdout.write(COLOR_NORMAL)
        sys.stdout.write(q)
        sys.stdout.write(RESET)
        sys.stdout.write("\n")
        
        max_length = max(max_length, max([len(f) for f in o]))
        
        o = [(f + " ").ljust(max_length) for f in o] 
        
        sys.stdout.write(CURSOR_MOVE_LEFT)
        for oo in o:
            sys.stdout.write(COLOR_NORMAL)
            sys.stdout.write(oo)
            sys.stdout.write(RESET)
            sys.stdout.write(" ")
        sys.stdout.write("\n")
        
        v = ["" for f in o]
        
        def refresh():
            """ renders the prompt """
            sys.stdout.write(CURSOR_MOVE_LEFT)
            sys.stdout.write(COLOR_NORMAL)
            
            n = 0
            m = 0
            for i, vv in enumerate(v):
                if i == selected0:
                    sys.stdout.write(COLOR_EMPHASIS)
                    sys.stdout.write(("[%s]" % vv).ljust(len(o[i])))
                    m = n + selected1 + 1
                else:
                    sys.stdout.write(COLOR_NORMAL)
                    if len(vv) == 0:
                        vv = "[]"
                    s = vv.ljust(len(o[i]))
                    sys.stdout.write(s)
                    n += len(s)
                if i < len(v)-1:
                    sys.stdout.write(RESET)
                    sys.stdout.write(" ")
                    n += 1
                    
            sys.stdout.write(CURSOR_MOVE_LEFT)
            sys.stdout.write(u"\u001b[%iC" % m)
            sys.stdout.flush()
        
        refresh()
        while True:
            character = ord(sys.stdin.read(1))
            
            if character == 3: # ctrl-c
                sys.stdout.write(RESET)
                sys.stdout.write("\n")
                
                sys.stdout.write(CURSOR_SHOW)
                sys.stdout.flush()
                
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
                
                return None
                
            if character in {10, 13}: # enter
                sys.stdout.write(RESET)
                sys.stdout.write("\n")
                
                sys.stdout.write(CURSOR_SHOW)
                sys.stdout.flush()
                
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
                
                return v
                
            if character == 27: # arrow keys
                next1, next2 = ord(sys.stdin.read(1)), ord(sys.stdin.read(1))
                if next1 == 91:
                    if next2 == 68: # left
                        if selected1 == 0:
                            s = selected0
                            selected0 = max(0, selected0-1)
                            if s != selected0:
                                selected1 = len(v[selected0])
                        else:
                            selected1 = max(0, selected1-1)
                    elif next2 == 67: # right
                        if selected1 == len(v[selected0]):
                            s = selected0
                            selected0 = min(len(o)-1, selected0+1)
                            if s != selected0:
                                selected1 = 0
                        else:
                            selected1 = min(len(v[selected0]), selected1+1)
                        
                    refresh()
            
            if 32 <= character <= 126: # text input
                if len(v[selected0]) < len(o[selected0])-2:
                    v[selected0] = v[selected0][:selected1] + chr(character) + v[selected0][selected1:]
                    selected1 += 1
                    refresh()
            
            if character == 127: # backspace
                if selected1 > 0:
                    v[selected0] = v[selected0][:selected1-1] + v[selected0][selected1:]
                    selected1 -= 1
                    refresh()
    