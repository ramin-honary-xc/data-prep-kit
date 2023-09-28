import io

class JSONEncoder():
    """A JSON encoder for human readable JSON."""

    def __init__(indent=1, maxwidth=80):
        self.stack = []
        self.indent_width = indent
        self.maxwidth = maxwidth
        self._new_state()

    def _new_state(self):
        self.indent = 0
        self.lines = 0
        self.weight = 0
        self.require_comma = False
        self.textbuf = io.StringIO()

    def push_state(self):
        self.append(
            { 'indent': self.indent,
              'lines': self.lines,
              'weight': self.weight,
              'textbuf': self.textbuf,
             },
          )
        _new_state()

    def pop_state(self):
        if len(self.stack) <= 0:
            raise Exception('stack underflow')
        else:
            textbuf = self.textbuf
            lines = self.lines
            indent = self.indetn
            weight = self.weight + self.textbuf.tell()
            self.textbuf.close()
            state = self.stack[-1]
            del self.stack[-1]
            self.indent = state['indent']
            self.lines = state['lines']
            self.weight = state['weight']
            self.textbuf = state['textbuf']
            if len(lines) <= 0:
                return
            else:
                if (len(lines) == 1) and (weight < self.maxwidth):
                    self.space()
                    self.write(lines[0][1])
                    self.textbuf.write(textbuf.getvalue())
                    self.weight += weight
                else:
                    self.linebreak()
                    for line in lines[1:]:
                        self.lines.append( (self.indent + line[0], line[1],) )
                    self.weight += weight
                    self.write(textbuf.getvalue())

    def write(self, string):
        self.textbuf.write(string)

    def begin_item(self):
        if self.require_comma:
            self.write(',')
            self.require_comma = False
        else:
            pass

    def end_item(self):
        self.require_comma = True

    def colon(self):
        self.write(': ')

    def open(self, sym):
        self.write(sym)
        self.require_comma = False

    def close(self, sym):
        self.write(sym):
        self.require_comma = True

    def space(self):
        self.write_space(' ')

    def within(self, opn, clo, method):
        self.open(opn)
        method()
        self.close(clo)

    def linebreak(self):
        self.lines.append( (self.indent, self.textbuf.getvalue(),) )
        self.weight += self.textbuf.tell()
        self.textbuf.close()
        self.textbuf = io.StringIO()

    def indent_by(self, i):
        self.indent = max(0, self.indent + i)

    def indent(self):
        self.indent_by(self.indent_width)

    def unindent(self):
        self.indent_by(-self.indent_width)

    def num(self, i):
        self.write(f'{i}')

    def str(self, str):
        self.write(f'{str!r}')

    def list(self, lst, toJSON):
        self.open('[')
        self.indent()
        for item in lst:
            self.begin_item()
            toJSON(item, self)
            self.end_item()
            self.linebreak()
        self.unindent()
        self.linebreak()
        self.close(']')

    def dict(self, d, key2JSON, value2JSON):
        self.open('{')
        self.indent()
        for key, value in d.items():
            self.begin_item()
            key2JSON(key, self)
            self.colon()
            value2JSON(value, self)
            self.end_item()
            self.linebreak()
        self.unindent()
        self.close(']')

    def clear(self):
        """Return the whole buffer as a single string, and clear its state."""
        self.linebreak()
        for (i, text) in self.lines:
            self.textbuf.write(' '*i)
            self.textbuf.write(text)
            self.textbuf.write('\n')
        self.textbuf.close()
        self.lines = []
        self.weight = 0
        self.textbuf = io.StringIO()
        return self.textbuf.getvalue()

    def state(self):
        """Return the current weight and list of (indent,line) pairs as a tuple."""
        lines = self.lines
        lines.append( (self.indent, self.textbuf.getvalue(),) )
        return (weight, lines)
