def _split_pipes(text: str) -> str:
    """Split on | outside strings; start each pipe stage on its own line,
    but leave comment lines (// or #) untouched."""
    out, buf, i, in_s, qch = [], '', 0, False, ''
    lines = text.splitlines()
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('//') or stripped.startswith('#'):
            # comment line: keep as-is
            out.append(line)
            continue
        i = 0
        buf = ''
        while i < len(line):
            ch = line[i]
            if in_s:
                buf += ch
                if ch == qch:
                    in_s = False
                elif ch == '\\' and i + 1 < len(line):
                    buf += line[i + 1]; i += 1
            else:
                if ch in ('"', "'"):
                    in_s, qch = True, ch
                    buf += ch
                elif ch == '|':
                    out.append(buf.strip())
                    buf = '| '
                else:
                    buf += ch
            i += 1
        out.append(buf.strip())
    return '\n'.join(part if part.startswith('| ') or part.startswith('//') or part.startswith('#')
                     else part for part in out if part.strip())
