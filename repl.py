import sys
import tty
import termios
import re

gReplCmds = {}
gCmdQuitters = []
gCmds = []

def match_cmd(cmd, subcmd):
    def match_by_unique_prefix(cmd,cmds):
        ret = None
        if cmd:
            for ind in range(1,len(cmd)+1):
                substr = cmd[0:ind]
                matches = [x for x in cmds if re.match(r'^{:s}'.format(substr), x) and len(cmd) <= len(x)]
                if len(matches) == 1:
                    ret = matches[0]
        return ret
    rcmd = match_by_unique_prefix(cmd,gCmds[0])
    rsubcmd = match_by_unique_prefix(subcmd,gCmds[1])
    return (rcmd,rsubcmd)

def replcmdquitter(func):
    name = func.__name__[4:]
    gReplCmds[name] = func
    tokens = name.split('_')
    for lvl,token in enumerate(tokens):
        if len(gCmds) <= lvl:
            gCmds.append(set())
        gCmds[lvl].add(token)
    gCmdQuitters.append(func)
    return func

def replcmd(quitter=False):
    def ret(func):
        name = func.__name__[4:]
        gReplCmds[name] = func
        tokens = name.split('_')
        for lvl,token in enumerate(tokens):
            if len(gCmds) <= lvl:
                gCmds.append(set())
            gCmds[lvl].add(token)
        if quitter:
            gCmdQuitters.append(func)
        return func
    return ret

def get_help():
    cmds = [gReplCmds[x] for x in gReplCmds]
    cmds = [(x.__name__[4:].replace('_',' '),x.__doc__) for x in cmds]
    cmds.sort()
    ret = ''
    for name,doc in cmds:
        ret += f'\n{name} - {doc}'
    return ret

def process_cmd(args, pargs, kwargs):
    cmd = args[0]
    subcmd = None
    if len(args) > 1:
        subcmd = args[1]
    (cmd,subcmd) = match_cmd(cmd, subcmd)

    if subcmd:
        cmd = gReplCmds['{:s}_{:s}'.format(cmd,subcmd)]
    else:
        cmd = gReplCmds['{:s}'.format(cmd,subcmd)]

    done = cmd in gCmdQuitters
    ret = cmd(*pargs, **kwargs)

    return (ret,done)

def enter_repl(*pargs, prompt='> ', **kwargs):
    def getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    def should_echo(ch):
        if ch == '\r': # TODO : Why we get \r instead of \n in WSL?
            return '\n'
        else:
            return None

    def should_continue(ch):
        return False

    def should_break(ch):
        if ch == '\r':
            return True
        else:
            return False

    def parse_ctrlcode(code):
        if code == '\x1b[A':
            return 'UP_ARROW'
        elif code == '\x1b[B':
            return 'DOWN_ARROW'
        elif code == '\x1b[C':
            return 'LEFT_ARROW'
        elif code == '\x1b[D':
            return 'RIGHT_ARROW'
        else:
            return None

    while True:
        sys.stdout.write(prompt)
        sys.stdout.flush()
        line = ''
        ctrlcode = None
        while True:
            ch = getch()
            if ctrlcode:
                ctrlcode += ch
                if ch != '[':
                    term_cmd = parse_ctrlcode(ctrlcode)
                    if term_cmd == 'UP_ARROW':
                        sys.stdout.write('Not implemented : UP_ARROW\n')
                    elif term_cmd == 'DOWN_ARROW':
                        sys.stdout.write('Not implemented : DOWN_ARROW\n')
                    elif term_cmd == 'RIGHT_ARROW':
                        sys.stdout.write('Not implemented : RIGHT_ARROW\n')
                    elif term_cmd == 'LEFT_ARROW':
                        sys.stdout.write('Not implemented : LEFT_ARROW\n')
                    ctrlcode = None
                    break
                continue
            else:
                if ch == '\x1b':
                    ctrlcode = ch
                    continue
                echo_ch = should_echo(ch)
                if echo_ch is not None:
                    sys.stdout.write(echo_ch)
                if should_continue(ch):
                    continue
                if should_break(ch):
                    break

            line += ch
            sys.stdout.write(ch)
            sys.stdout.flush()
        if not line.strip():
            continue
        (outp,done) = process_cmd(line.split(' '), pargs, kwargs)
        if done:
            return
        if outp is None:
            outp = 'Command not recognized...'
        sys.stdout.write(f'{outp}\n\n')
