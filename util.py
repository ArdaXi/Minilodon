from datetime import datetime
import os

def open_log_file(channel):
    if not os.path.exists(channel):
        os.mkdir(channel)
    curdate = datetime.now()
    datestr = curdate.strftime('%y-%m-%d')
    filename = '{}/{}-{}.log'.format(channel, datestr, channel)
    fp = open(filename, 'at', 1)
    fp.day = curdate.day
    return fp

def wrap_msg(words):
    if isinstance(words, str):
        for line in wrap_msg(words.split(' ')):
            yield line
        return
    line = ''
    index = 0
    for i in range(len(words)):
        newline = line + ' ' + words[i]
        if len(newline) > 254:
            index = i
            break
        line = newline
    yield line.strip()
    if index > 0:
        remainder = words[index:]
        for line in wrap_msg(remainder):
            yield line
