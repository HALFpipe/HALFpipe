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
    def __init__(self):
        self.clear()
        
        self.defaults = dict()

    def clear(self):
        sys.stdout.write(CLEAR_SCREEN)
        sys.stdout.write(ESC + u"0;0H")
        sys.stdout.flush()

    def info(self, q):
        sys.stdout.write(CURSOR_MOVE_LEFT)
        sys.stdout.write(COLOR_NORMAL)
        sys.stdout.write("%s" % q)
        sys.stdout.write(RESET)
        sys.stdout.write("\n")
        sys.stdout.flush()

    def error(self, q):
        sys.stdout.write(CURSOR_MOVE_LEFT)
        sys.stdout.write(RESET)
        sys.stdout.write("\n")
        sys.stdout.flush()
        
        raise RuntimeError(COLOR_ERROR + "%s" % q + RESET)

    def read(self, q, o = "", tag = None):
        settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin)
        
        selected = 0
        
        if tag is not None and tag in self.defaults:
            o = self.defaults[tag]
        
        sys.stdout.write(CURSOR_MOVE_LEFT)
        sys.stdout.write(COLOR_NORMAL)
        sys.stdout.write("%s" % q)
        sys.stdout.write(RESET)
        sys.stdout.write("\n")
        
        def refresh():
            sys.stdout.write(CURSOR_MOVE_LEFT)
            sys.stdout.write(COLOR_EMPHASIS)
            sys.stdout.write("[%s] " % o)
            sys.stdout.write(CURSOR_MOVE_LEFT)
            sys.stdout.write(u"\u001b[%iC" % (1 + selected))
            sys.stdout.flush()
        
        refresh()
        while True:
            character = ord(sys.stdin.read(1))
            
            if character == 3:
                sys.stdout.write(RESET)
                sys.stdout.write("\n")
                
                sys.stdout.write(CURSOR_SHOW)
                sys.stdout.flush()
                
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
                
                return None
                
            if character in {10, 13}:
                sys.stdout.write(RESET)
                sys.stdout.write("\n")
                sys.stdout.flush()
                
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
                
                if tag is not None:
                    self.defaults[tag] = o
                
                return o
                
            if character == 27:
                next1, next2 = ord(sys.stdin.read(1)), ord(sys.stdin.read(1))
                if next1 == 91:
                    if next2 == 68: 
                        selected = max(0, selected-1)
                    elif next2 == 67: 
                        selected = min(len(o), selected+1)
                        
                    refresh()
                
            if 32 <= character <= 126:
                o = o[:selected] + chr(character) + o[selected:]
                selected += 1
                refresh()
                
            if character == 127:
                if selected > 0:
                    o = o[:selected-1] + o[selected:]
                    selected -= 1
                    refresh()
                

    def select(self, q, o, tag = None):
        settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin)
        
        sys.stdout.write(CURSOR_HIDE)
        
        selected = 0
        
        if tag is not None and tag in self.defaults:
            selected = self.defaults[tag]
        
        def refresh():
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
            
            if character == 3: 
                sys.stdout.write(RESET)
                sys.stdout.write("\n")
                
                sys.stdout.write(CURSOR_SHOW)
                sys.stdout.flush()
                
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
                
                return None
                
            if character in {10, 13}:
                sys.stdout.write(RESET)
                sys.stdout.write("\n")
                
                sys.stdout.write(CURSOR_SHOW)
                sys.stdout.flush()
                
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
                
                if tag is not None:
                    self.defaults[tag] = selected
                
                return o[selected]
                
            if character == 27:
                next1, next2 = ord(sys.stdin.read(1)), ord(sys.stdin.read(1))
                if next1 == 91:
                    if next2 == 68: 
                        selected = max(0, selected-1)
                    elif next2 == 67: 
                        selected = min(len(o)-1, selected+1)
                        
                    refresh()
        
    